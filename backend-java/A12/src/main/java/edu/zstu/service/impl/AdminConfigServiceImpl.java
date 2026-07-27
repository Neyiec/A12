package edu.zstu.service.impl;

import cn.hutool.core.bean.BeanUtil;
import edu.zstu.dto.ConfigDTO;
import edu.zstu.dto.RollbackDTO;
import edu.zstu.entity.AiConfigVersion;
import edu.zstu.entity.Sys_Config;
import edu.zstu.mapper.AiConfigVersionMapper;
import edu.zstu.mapper.SysConfigMapper;
import edu.zstu.service.AdminConfigService;
import edu.zstu.utils.CurrentHolder;
import edu.zstu.vo.ConfigVO;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class AdminConfigServiceImpl implements AdminConfigService {

    private final SysConfigMapper configMapper;
    private final AiConfigVersionMapper versionMapper;

    public AdminConfigServiceImpl(SysConfigMapper configMapper, AiConfigVersionMapper versionMapper) {
        this.configMapper = configMapper;
        this.versionMapper = versionMapper;
    }

    // ==================== API-98 查询AI配置列表 ====================

    @Override
    public List<ConfigVO> listAiConfigs(String configGroup) {
        List<Sys_Config> list;
        if (configGroup != null && !configGroup.isBlank()) {
            list = configMapper.findByGroup(configGroup);
        } else {
            list = configMapper.findAll();
        }
        return list.stream().map(this::toConfigVO).collect(Collectors.toList());
    }

    // ==================== API-99 创建/更新AI配置 ====================

    @Override
    @Transactional
    public ConfigVO createAiConfig(ConfigDTO dto) {
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

            // 同时写入历史表（version 1）
            AiConfigVersion history = new AiConfigVersion();
            history.setConfigId(config.getId());
            history.setVersion(1);
            history.setConfigValue(dto.getConfig_value());
            history.setCreatedBy(currentUser);
            history.setCreatedAt(LocalDateTime.now());
            versionMapper.insert(history);

            return toConfigVO(config);
        }
    }

    // ==================== API-100 发布AI配置 ====================

    @Override
    @Transactional
    public Map<String, Object> publishAiConfig(Integer id) {
        Sys_Config config = configMapper.findById(id);
        if (config == null) {
            throw new RuntimeException("配置不存在");
        }

        configMapper.updateStatus(id, "published");

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

        return toConfigVO(config);
    }

    // ==================== 以下为占位实现（后续 API 继续实现） ====================

    @Override
    public Object listSecurityPolicies() { return null; }
    @Override
    public Object updateSecurityPolicy(String id) { return null; }
    @Override
    public Object publishSecurityPolicy(String id) { return null; }
    @Override
    public Object listAuditLogs() { return null; }
    @Override
    public Object listSystemLogs() { return null; }
    @Override
    public Object getDashboard() { return null; }
    @Override
    public Object listAlerts() { return null; }
    @Override
    public Object getAlert(String id) { return null; }
    @Override
    public Object acknowledgeAlert(String id) { return null; }
    @Override
    public Object resolveAlert(String id) { return null; }

    // ==================== 内部辅助 ====================

    private ConfigVO toConfigVO(Sys_Config config) {
        ConfigVO vo = new ConfigVO();
        BeanUtil.copyProperties(config, vo);
        return vo;
    }
}
