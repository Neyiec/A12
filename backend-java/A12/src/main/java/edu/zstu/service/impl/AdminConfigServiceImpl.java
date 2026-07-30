package edu.zstu.service.impl;

import cn.hutool.core.bean.BeanUtil;
import edu.zstu.dto.ConfigDTO;
import edu.zstu.dto.LogQueryDTO;
import edu.zstu.dto.RollbackDTO;
import edu.zstu.dto.SecurityPolicyDTO;
import edu.zstu.entity.AiConfigVersion;
import edu.zstu.entity.Sys_Config;
import edu.zstu.entity.Sys_Log;
import edu.zstu.mapper.AiConfigVersionMapper;
import edu.zstu.mapper.SysConfigMapper;
import edu.zstu.mapper.SysLogMapper;
import edu.zstu.service.AdminConfigService;
import edu.zstu.service.BusinessLogService;
import edu.zstu.utils.CurrentHolder;
import edu.zstu.utils.PageResult;
import edu.zstu.utils.RedisCacheUtil;
import edu.zstu.vo.ConfigVO;
import edu.zstu.vo.LogVO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Slf4j
@Service
public class AdminConfigServiceImpl implements AdminConfigService {

    private final SysConfigMapper configMapper;
    private final AiConfigVersionMapper versionMapper;
    private final SysLogMapper logMapper;
    private final BusinessLogService businessLogService;
    private final RedisCacheUtil redisCacheUtil;

    public AdminConfigServiceImpl(SysConfigMapper configMapper, AiConfigVersionMapper versionMapper,
                                  SysLogMapper logMapper, BusinessLogService businessLogService,
                                  RedisCacheUtil redisCacheUtil) {
        this.configMapper = configMapper;
        this.versionMapper = versionMapper;
        this.logMapper = logMapper;
        this.businessLogService = businessLogService;
        this.redisCacheUtil = redisCacheUtil;
    }

    // ==================== API-98 查询AI配置列表 ====================

    @Override
    public List<ConfigVO> listAiConfigs(String configGroup) {
        log.info("listAiConfigs configGroup={}", configGroup);
        String key = configGroup != null && !configGroup.isBlank()
                ? "config:group:" + configGroup
                : "config:all";
        return redisCacheUtil.getOrLoad(key, new com.fasterxml.jackson.core.type.TypeReference<List<ConfigVO>>() {},
                Duration.ofMinutes(10), () -> {
                    List<Sys_Config> list;
                    if (configGroup != null && !configGroup.isBlank()) {
                        list = configMapper.findByGroup(configGroup);
                    } else {
                        list = configMapper.findAll();
                    }
                    return list.stream().map(this::toConfigVO).collect(Collectors.toList());
                });
    }

    // ==================== API-99 创建/更新AI配置 ====================

    @Override
    @Transactional
    public ConfigVO createAiConfig(ConfigDTO dto) {
        log.info("createAiConfig group={}, key={}", dto.getConfig_group(), dto.getConfig_key());
        // 参数校验
        if (dto.getConfig_group() == null || dto.getConfig_group().isBlank()) {
            throw new RuntimeException("config_group 不能为空");
        }
        if (dto.getConfig_key() == null || dto.getConfig_key().isBlank()) {
            throw new RuntimeException("config_key 不能为空");
        }
        if (dto.getConfig_value() == null || dto.getConfig_value().isBlank()) {
            throw new RuntimeException("config_value 不能为空");
        }

        Integer currentUser = CurrentHolder.getCurrentId();

        // 查配置键是否已存在
        Sys_Config existing = configMapper.findByConfigKey(dto.getConfig_key());

        if (existing != null) {
            // 保存当前版本到历史表
            AiConfigVersion history = new AiConfigVersion();
            history.setConfigId(existing.getId());
            history.setVersion(existing.getVersion());
            history.setConfigValue(existing.getConfig_value());
            history.setCreatedBy(currentUser);
            history.setCreatedAt(LocalDateTime.now());
            versionMapper.insert(history);

            // 更新现有配置：新值、新描述、版本+1
            existing.setConfig_value(dto.getConfig_value());
            existing.setDescription(dto.getDescription());
            existing.setVersion(existing.getVersion() + 1);
            existing.setUpdated_by(currentUser);
            existing.setStatus("draft");
            configMapper.update(existing);
            evictConfigCache(existing);
            businessLogService.record("operation", "admin_config", "update_ai_config", "config", existing.getId(),
                    Map.of("config_key", existing.getConfig_key(), "version", existing.getVersion()));
            return toConfigVO(existing);
        } else {
            // 新建配置
            Sys_Config config = new Sys_Config();
            config.setConfig_group(dto.getConfig_group());
            config.setConfig_key(dto.getConfig_key());
            config.setConfig_value(dto.getConfig_value());
            config.setDescription(dto.getDescription());
            config.setUpdated_by(currentUser);
            config.setUpdated_at(LocalDateTime.now());
            config.setVersion(1);
            config.setStatus("draft");
            configMapper.insert(config);
            evictConfigCache(config);

            // 同时写入历史表（version 1）
            AiConfigVersion history = new AiConfigVersion();
            history.setConfigId(config.getId());
            history.setVersion(1);
            history.setConfigValue(dto.getConfig_value());
            history.setCreatedBy(currentUser);
            history.setCreatedAt(LocalDateTime.now());
            versionMapper.insert(history);
            businessLogService.record("operation", "admin_config", "create_ai_config", "config", config.getId(),
                    Map.of("config_key", config.getConfig_key(), "version", config.getVersion()));

            return toConfigVO(config);
        }
    }

    // ==================== API-100 发布AI配置 ====================

    @Override
    @Transactional
    public Map<String, Object> publishAiConfig(Integer id) {
        log.info("publishAiConfig configId={}", id);
        Sys_Config config = configMapper.findById(id);
        if (config == null) {
            throw new RuntimeException("配置不存在");
        }

        configMapper.updateStatus(id, "published");
        evictConfigCache(config);
        businessLogService.record("operation", "admin_config", "publish_ai_config", "config", id);

        // 模拟多节点发布状态
        List<Map<String, String>> nodeStatuses = List.of(
                Map.of("node", "node-01", "status", "loaded"),
                Map.of("node", "node-02", "status", "loaded"),
                Map.of("node", "node-03", "status", "loaded")
        );
        return Map.of("node_status", nodeStatuses);
    }

    // ==================== API-101 回滚AI配置 ====================

    @Override
    @Transactional
    public ConfigVO rollbackAiConfig(Integer id, RollbackDTO dto) {
        log.info("rollbackAiConfig configId={}, targetVersion={}", id, dto.getTarget_version());
        Sys_Config config = configMapper.findById(id);
        if (config == null) {
            throw new RuntimeException("配置不存在");
        }

        // 查找目标版本历史
        AiConfigVersion targetVersion = versionMapper.findByConfigIdAndVersion(id, dto.getTarget_version());
        if (targetVersion == null) {
            throw new RuntimeException("目标版本不存在: " + dto.getTarget_version());
        }

        Integer currentUser = CurrentHolder.getCurrentId();

        // 保存当前版本到历史表（记录回滚原因）
        AiConfigVersion rollbackHistory = new AiConfigVersion();
        rollbackHistory.setConfigId(config.getId());
        rollbackHistory.setVersion(config.getVersion());
        rollbackHistory.setConfigValue(config.getConfig_value());
        rollbackHistory.setReason(dto.getReason());
        rollbackHistory.setCreatedBy(currentUser);
        rollbackHistory.setCreatedAt(LocalDateTime.now());
        versionMapper.insert(rollbackHistory);

        // 将当前配置更新为目标版本的配置值
        config.setConfig_value(targetVersion.getConfigValue());
        config.setVersion(config.getVersion() + 1);
        config.setUpdated_by(currentUser);
        config.setStatus("draft");
        configMapper.update(config);
        evictConfigCache(config);
        businessLogService.record("operation", "admin_config", "rollback_ai_config", "config", id,
                Map.of("target_version", dto.getTarget_version(), "new_version", config.getVersion()));

        return toConfigVO(config);
    }

    @Override
    public List<ConfigVO> listSecurityPolicies() {
        log.info("listSecurityPolicies");
        return redisCacheUtil.getOrLoad("config:group:security",
                new com.fasterxml.jackson.core.type.TypeReference<List<ConfigVO>>() {},
                Duration.ofMinutes(10),
                () -> configMapper.findByGroup("security").stream().map(this::toConfigVO).collect(Collectors.toList()));
    }

    @Override
    @Transactional
    public ConfigVO updateSecurityPolicy(String id, SecurityPolicyDTO dto) {
        log.info("updateSecurityPolicy configId={}, requestVersion={}", id, dto.getVersion());
        Sys_Config config = configMapper.findById(Integer.parseInt(id));
        if (config == null || !"security".equals(config.getConfig_group())) throw new RuntimeException("安全策略不存在");
        if (dto.getVersion() != config.getVersion()) throw new RuntimeException("版本冲突，请刷新后重试");
        if (dto.getConfig_value() == null || dto.getConfig_value().isBlank()) throw new RuntimeException("config_value 不能为空");
        config.setConfig_value(dto.getConfig_value());
        config.setVersion(config.getVersion() + 1);
        config.setStatus("draft");
        config.setUpdated_by(CurrentHolder.getCurrentId());
        configMapper.update(config);
        evictConfigCache(config);
        businessLogService.record("operation", "admin_config", "update_security_policy", "config", config.getId(),
                Map.of("version", config.getVersion()));
        return toConfigVO(config);
    }

    @Override
    @Transactional
    public Map<String, Object> publishSecurityPolicy(String id) {
        log.info("publishSecurityPolicy configId={}", id);
        Sys_Config config = configMapper.findById(Integer.parseInt(id));
        if (config == null || !"security".equals(config.getConfig_group())) throw new RuntimeException("安全策略不存在");
        configMapper.updateStatus(config.getId(), "published");
        evictConfigCache(config);
        businessLogService.record("operation", "admin_config", "publish_security_policy", "config", config.getId());
        return Map.of("published", true);
    }

    @Override
    public PageResult<LogVO> listAuditLogs(LogQueryDTO dto) {
        log.info("listAuditLogs type={}, module={}, userId={}, page={}, size={}", dto.getLog_type(), dto.getModule(), dto.getUser_id(), dto.getPage(), dto.getSize());
        return redisCacheUtil.getOrLoad(logCacheKey("audit", dto),
                new com.fasterxml.jackson.core.type.TypeReference<PageResult<LogVO>>() {},
                Duration.ofSeconds(20),
                () -> pageLogs(filterLogs(dto, "audit"), dto));
    }

    @Override
    public PageResult<LogVO> listSystemLogs(LogQueryDTO dto) {
        log.info("listSystemLogs type={}, module={}, userId={}, page={}, size={}", dto.getLog_type(), dto.getModule(), dto.getUser_id(), dto.getPage(), dto.getSize());
        return redisCacheUtil.getOrLoad(logCacheKey("system", dto),
                new com.fasterxml.jackson.core.type.TypeReference<PageResult<LogVO>>() {},
                Duration.ofSeconds(20),
                () -> pageLogs(filterLogs(dto, null), dto));
    }

    @Override
    public Map<String, Object> getDashboard() {
        log.info("getDashboard");
        return redisCacheUtil.getOrLoad("admin:dashboard",
                new com.fasterxml.jackson.core.type.TypeReference<Map<String, Object>>() {},
                Duration.ofSeconds(60),
                () -> {
                    long aiConfigCount = configMapper.findByGroup("ai_model").size();
                    long logCount = logMapper.findAll().size();
                    return Map.of("user_count", 0, "resource_count", 0, "ai_task_count", aiConfigCount,
                            "export_task_count", 0, "moderation_pending_count", 0, "log_count", logCount);
                });
    }

    @Override
    public PageResult<Map<String, Object>> listAlerts(String level, String source, String status, int page, int size) {
        log.info("listAlerts level={}, source={}, status={}, page={}, size={}", level, source, status, page, size);
        int p = page <= 0 ? 1 : page;
        int s = size <= 0 ? 10 : size;
        return new PageResult<>(0, p, s, List.of());
    }

    @Override
    public Map<String, Object> getAlert(String id) {
        log.info("getAlert alertId={}", id);
        return Map.of("id", id, "level", "info", "source", "system", "title", "告警不存在",
                "detail", "当前系统未接入告警存储", "status", "resolved");
    }

    @Override
    public void acknowledgeAlert(String id) {
        log.info("acknowledgeAlert alertId={}", id);
        businessLogService.record("operation", "admin_alert", "acknowledge", "alert", Integer.parseInt(id));
    }

    @Override
    public void resolveAlert(String id, String resolution) {
        log.info("resolveAlert alertId={}, hasResolution={}", id, resolution != null && !resolution.isBlank());
        if (resolution == null || resolution.isBlank()) throw new RuntimeException("resolution 不能为空");
        businessLogService.record("operation", "admin_alert", "resolve", "alert", Integer.parseInt(id),
                Map.of("resolution", resolution));
    }

    // ==================== 内部辅助 ====================

    private ConfigVO toConfigVO(Sys_Config config) {
        ConfigVO vo = new ConfigVO();
        BeanUtil.copyProperties(config, vo);
        return vo;
    }

    private void evictConfigCache(Sys_Config config) {
        redisCacheUtil.delete("config:all");
        redisCacheUtil.delete("config:group:" + config.getConfig_group());
        redisCacheUtil.delete("config:key:" + config.getConfig_key());
        redisCacheUtil.delete("admin:dashboard");
    }

    private String logCacheKey(String scope, LogQueryDTO dto) {
        return "logs:" + scope + ":" +
                blankToAll(dto.getLog_type()) + ":" +
                blankToAll(dto.getModule()) + ":" +
                (dto.getUser_id() == null ? "all" : dto.getUser_id()) + ":p" +
                dto.getPage() + ":s" + dto.getSize();
    }

    private String blankToAll(String value) {
        return value == null || value.isBlank() ? "all" : value;
    }

    private List<LogVO> filterLogs(LogQueryDTO dto, String forcedType) {
        return logMapper.findAll().stream()
                .filter(l -> forcedType == null || forcedType.equals(l.getLog_type()))
                .filter(l -> dto.getLog_type() == null || dto.getLog_type().isBlank() || dto.getLog_type().equals(l.getLog_type()))
                .filter(l -> dto.getModule() == null || dto.getModule().isBlank() || dto.getModule().equals(l.getModule()))
                .filter(l -> dto.getUser_id() == null || dto.getUser_id().equals(l.getUser_id()))
                .map(this::toLogVO)
                .toList();
    }

    private PageResult<LogVO> pageLogs(List<LogVO> all, LogQueryDTO dto) {
        int page = dto.getPage() <= 0 ? 1 : dto.getPage();
        int size = dto.getSize() <= 0 ? 10 : dto.getSize();
        int from = Math.min((page - 1) * size, all.size());
        int to = Math.min(from + size, all.size());
        return new PageResult<>(all.size(), page, size, all.subList(from, to));
    }

    private LogVO toLogVO(Sys_Log log) {
        LogVO vo = new LogVO();
        BeanUtil.copyProperties(log, vo);
        vo.setCreated_at(log.getCreate_at());
        return vo;
    }
}


