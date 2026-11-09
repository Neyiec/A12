package edu.zstu.service.impl;

import cn.hutool.core.bean.BeanUtil;
import edu.zstu.dto.ConfigDTO;
import edu.zstu.dto.LogQueryDTO;
import edu.zstu.dto.RollbackDTO;
import edu.zstu.dto.SecurityPolicyDTO;
import edu.zstu.entity.*;
import edu.zstu.mapper.*;
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
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.stream.Collectors;

@Slf4j
@Service
public class AdminConfigServiceImpl implements AdminConfigService {

    private final SysConfigMapper configMapper;
    private final AiConfigVersionMapper versionMapper;
    private final SysLogMapper logMapper;
    private final SysUserMapper userMapper;
    private final ResMaterialMapper materialMapper;
    private final AdmResourceMapper admResourceMapper;
    private final AiTaskMapper aiTaskMapper;
    private final ExpTaskMapper expTaskMapper;
    private final AdmAuditMapper auditMapper;
    private final ComContentMapper contentMapper;
    private final SysRoleMapper roleMapper;
    private final BusinessLogService businessLogService;
    private final RedisCacheUtil redisCacheUtil;

    public AdminConfigServiceImpl(SysConfigMapper configMapper, AiConfigVersionMapper versionMapper,
                                  SysLogMapper logMapper, SysUserMapper userMapper,
                                  ResMaterialMapper materialMapper, AdmResourceMapper admResourceMapper,
                                  AiTaskMapper aiTaskMapper, ExpTaskMapper expTaskMapper,
                                  AdmAuditMapper auditMapper, ComContentMapper contentMapper,
                                  SysRoleMapper roleMapper,
                                  BusinessLogService businessLogService, RedisCacheUtil redisCacheUtil) {
        this.configMapper = configMapper;
        this.versionMapper = versionMapper;
        this.logMapper = logMapper;
        this.userMapper = userMapper;
        this.materialMapper = materialMapper;
        this.admResourceMapper = admResourceMapper;
        this.aiTaskMapper = aiTaskMapper;
        this.expTaskMapper = expTaskMapper;
        this.auditMapper = auditMapper;
        this.contentMapper = contentMapper;
        this.roleMapper = roleMapper;
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
            // 更新现有配置：新值、新描述、版本+1
            existing.setConfig_value(dto.getConfig_value());
            existing.setDescription(dto.getDescription());
            existing.setVersion(existing.getVersion() + 1);
            existing.setUpdated_by(currentUser);
            existing.setStatus("draft");
            configMapper.update(existing);

            // 将新版本写入历史表（创建时已记录 v1，此处记录版本+1 后的新版本，避免 uk_config_version 冲突）
            AiConfigVersion history = new AiConfigVersion();
            history.setConfigId(existing.getId());
            history.setVersion(existing.getVersion());
            history.setConfigValue(dto.getConfig_value());
            history.setCreatedBy(currentUser);
            history.setCreatedAt(LocalDateTime.now());
            versionMapper.insert(history);

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

        // Python 为按需拉取配置，不能在此声称各节点已加载。
        return Map.of("status", "published", "delivery", "python_pull_within_60s",
                "config_group", config.getConfig_group());
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

        // 将当前配置更新为目标版本的配置值（当前版本在创建/更新时已写入历史表，无需重复记录）
        config.setConfig_value(targetVersion.getConfigValue());
        config.setVersion(config.getVersion() + 1);
        config.setUpdated_by(currentUser);
        config.setStatus("draft");
        configMapper.update(config);

        // 回滚产生的新版本写入历史表，reason 记录回滚原因
        AiConfigVersion rollbackHistory = new AiConfigVersion();
        rollbackHistory.setConfigId(config.getId());
        rollbackHistory.setVersion(config.getVersion());
        rollbackHistory.setConfigValue(targetVersion.getConfigValue());
        rollbackHistory.setReason(dto.getReason());
        rollbackHistory.setCreatedBy(currentUser);
        rollbackHistory.setCreatedAt(LocalDateTime.now());
        versionMapper.insert(rollbackHistory);

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
                    List<Sys_User> users = userMapper.findAll();
                    List<Res_Material> materials = materialMapper.findAll();
                    List<Adm_Resource> platformResources = admResourceMapper.findAll();
                    List<AI_Task> aiTasks = aiTaskMapper.findAll();
                    List<Exp_Task> exportTasks = expTaskMapper.findAll();
                    List<Adm_Audit> audits = auditMapper.findAll();
                    List<Com_Content> communityContents = contentMapper.findAll();
                    List<Sys_Log> logs = logMapper.findAll();

                    long activeUserCount = users.stream().filter(u -> u.getDeleted_at() == null && u.getIs_active() == 1).count();
                    long activeMaterialCount = materials.stream().filter(m -> Objects.equals(m.getStatus(), 1)).count();
                    long activePlatformResourceCount = platformResources.stream().filter(r -> Objects.equals(r.getStatus(), 1)).count();
                    long pendingModerationCount = audits.stream().filter(a -> "pending".equals(a.getStatus())).count();
                    long pendingReviewCount = audits.stream().filter(a -> "audit".equals(a.getAudit_type()) && "pending".equals(a.getStatus())).count();
                    long pendingReportCount = audits.stream().filter(a -> "report".equals(a.getAudit_type()) && "pending".equals(a.getStatus())).count();
                    // 成功率口径：仅以终态任务（completed/failed）计算，planning/confirmed/executing 在途任务不进分母
                    long aiSuccessCount = aiTasks.stream().filter(t -> "completed".equals(t.getStatus())).count();
                    long aiFailedCount = aiTasks.stream().filter(t -> "failed".equals(t.getStatus())).count();
                    long exportSuccessCount = exportTasks.stream().filter(t -> "success".equals(t.getStatus())).count();

                    LocalDateTime todayStart = LocalDate.now().atStartOfDay();
                    Map<String, Object> totals = new LinkedHashMap<>();
                    totals.put("user_count", activeUserCount);
                    totals.put("resource_count", activeMaterialCount + activePlatformResourceCount);
                    totals.put("personal_resource_count", activeMaterialCount);
                    totals.put("platform_resource_count", activePlatformResourceCount);
                    totals.put("ai_task_count", aiTasks.size());
                    totals.put("export_task_count", exportTasks.size());
                    totals.put("community_content_count", communityContents.size());
                    totals.put("moderation_pending_count", pendingModerationCount);
                    totals.put("review_pending_count", pendingReviewCount);
                    totals.put("report_pending_count", pendingReportCount);
                    totals.put("log_count", logs.size());

                    Map<String, Object> today = new LinkedHashMap<>();
                    today.put("new_user_count", countSince(users, Sys_User::getCreated_at, todayStart));
                    today.put("new_resource_count", countSince(materials, Res_Material::getCreated_at, todayStart)
                            + countSince(platformResources, Adm_Resource::getCreated_at, todayStart));
                    today.put("new_ai_task_count", countSince(aiTasks, AI_Task::getCreated_at, todayStart));
                    today.put("new_export_task_count", countSince(exportTasks, Exp_Task::getCreated_at, todayStart));
                    today.put("new_community_content_count", countSince(communityContents, Com_Content::getCreated_at, todayStart));
                    today.put("new_log_count", countSince(logs, Sys_Log::getCreate_at, todayStart));

                    Map<String, Object> distribution = new LinkedHashMap<>();
                    // RBAC 重构后按角色(role_code)统计用户分布，键名保持 users_by_type 兼容前端
                    Map<String, Object> usersByRole = new LinkedHashMap<>();
                    for (Map<String, Object> row : roleMapper.countUsersGroupByRole()) {
                        usersByRole.put(String.valueOf(row.get("role_code")), row.get("user_count"));
                    }
                    distribution.put("users_by_type", usersByRole);
                    distribution.put("resources_by_type", mergeCounts(groupCount(materials, Res_Material::getFile_type),
                            groupCount(platformResources, Adm_Resource::getResource_type)));
                    distribution.put("materials_by_ai_index_status", groupCount(materials, Res_Material::getAi_index_status));
                    distribution.put("ai_tasks_by_status", groupCount(aiTasks, AI_Task::getStatus));
                    distribution.put("export_tasks_by_status", groupCount(exportTasks, Exp_Task::getStatus));
                    distribution.put("moderation_by_type_status", auditTypeStatusCount(audits));
                    distribution.put("community_by_status", groupCount(communityContents, Com_Content::getStatus));
                    distribution.put("logs_by_type", groupCount(logs, Sys_Log::getLog_type));

                    Map<String, Object> quality = new LinkedHashMap<>();
                    quality.put("ai_task_success_rate", rate(aiSuccessCount, aiSuccessCount + aiFailedCount));
                    quality.put("export_success_rate", rate(exportSuccessCount, exportTasks.size()));
                    quality.put("export_failed_count", exportTasks.stream().filter(t -> "failed".equals(t.getStatus())).count());
                    quality.put("ai_task_failed_count", aiFailedCount);
                    quality.put("avg_export_duration_ms", averageExportDurationMs(exportTasks));

                    Map<String, Object> result = new LinkedHashMap<>();
                    result.putAll(totals);
                    result.put("today", today);
                    result.put("trend_7d", buildSevenDayTrend(users, materials, platformResources, aiTasks, exportTasks, communityContents, logs));
                    result.put("distribution", distribution);
                    result.put("quality", quality);
                    result.put("recent_activities", recentActivities(logs, 10));
                    result.put("generated_at", LocalDateTime.now().toString());
                    return result;
                });
    }

    @Override
    public PageResult<Map<String, Object>> listAlerts(String level, String source, String status, int page, int size) {
        log.info("listAlerts level={}, source={}, status={}, page={}, size={}", level, source, status, page, size);
        int p = page <= 0 ? 1 : page;
        int s = size <= 0 ? 10 : size;
        // 派生告警恒为 open：查询其它状态（acknowledged/resolved）时无持久化数据，返回空页
        if (status != null && !status.isBlank() && !"open".equals(status)) {
            return new PageResult<>(0, p, s, List.of());
        }
        List<Map<String, Object>> filtered = deriveAlerts().stream()
                .filter(a -> level == null || level.isBlank() || level.equals(a.get("level")))
                .filter(a -> source == null || source.isBlank() || source.equals(a.get("source")))
                .toList();
        int total = filtered.size();
        int from = Math.min((p - 1) * s, total);
        int to = Math.min(from + s, total);
        return new PageResult<>(total, p, s, new ArrayList<>(filtered.subList(from, to)));
    }

    @Override
    public Map<String, Object> getAlert(String id) {
        log.info("getAlert alertId={}", id);
        return deriveAlerts().stream()
                .filter(a -> id != null && id.equals(String.valueOf(a.get("id"))))
                .findFirst()
                .orElse(Map.of("id", id == null ? "" : id, "level", "info", "source", "system",
                        "title", "告警不存在", "detail", "派生式告警随数据恢复自动消失", "status", "resolved"));
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

    // ==================== 派生式告警（第一阶段：无告警存储表，数据驱动投影） ====================

    /**
     * 派生式告警总入口：从既有业务数据投影当前异常（设计见 doc/admin-dashboard-workflow.md 3④）
     * 告警无持久化，id 为派生指纹；处置（acknowledge/resolve）仅记审计日志，数据恢复后告警自动消失
     */
    private List<Map<String, Object>> deriveAlerts() {
        List<Map<String, Object>> alerts = new ArrayList<>();
        addTaskFailureAlerts(alerts, expTaskMapper.findAll(), aiTaskMapper.findAll(), materialMapper.findAll());
        addLogErrorAlert(alerts, logMapper.findAll());
        // danger 优先，同级按时间倒序（null 时间排最后）
        Comparator<Map<String, Object>> bySeverity =
                Comparator.comparingInt(a -> severityWeight((String) a.get("level")));
        alerts.sort(bySeverity.thenComparing(
                (Map<String, Object> a) -> (LocalDateTime) a.get("created_at"),
                Comparator.nullsLast(Comparator.reverseOrder())));
        return alerts;
    }

    /**
     * 任务类告警规则：导出失败 / AI 任务失败 / 素材 AI 索引失败 / 导出队列积压（处理超 30 分钟）
     */
    private void addTaskFailureAlerts(List<Map<String, Object>> alerts,
                                      List<Exp_Task> exportTasks, List<AI_Task> aiTasks,
                                      List<Res_Material> materials) {
        List<Exp_Task> exportFailed = exportTasks.stream()
                .filter(t -> "failed".equals(t.getStatus())).toList();
        if (!exportFailed.isEmpty()) {
            alerts.add(derivedAlert("derived:export_failed", "warning", "export", "导出任务存在失败",
                    "共 " + exportFailed.size() + " 项导出任务失败，建议前往导出记录排查",
                    latestTime(exportFailed.stream().map(Exp_Task::getCreated_at).toList())));
        }
        List<AI_Task> aiFailed = aiTasks.stream()
                .filter(t -> "failed".equals(t.getStatus())).toList();
        if (!aiFailed.isEmpty()) {
            alerts.add(derivedAlert("derived:ai_task_failed", "warning", "ai", "AI 生成任务存在失败",
                    "共 " + aiFailed.size() + " 项 AI 任务失败，可查看系统日志定位原因",
                    latestTime(aiFailed.stream().map(AI_Task::getCreated_at).toList())));
        }
        List<Res_Material> indexFailed = materials.stream()
                .filter(m -> "failed".equals(m.getAi_index_status())).toList();
        if (!indexFailed.isEmpty()) {
            alerts.add(derivedAlert("derived:material_index_failed", "warning", "resource", "个人素材 AI 索引失败",
                    indexFailed.size() + " 条素材向量化失败，可在资源库中重新开启 AI 引用",
                    latestTime(indexFailed.stream().map(Res_Material::getCreated_at).toList())));
        }
        LocalDateTime backlogDeadline = LocalDateTime.now().minusMinutes(30);
        long backlog = exportTasks.stream()
                .filter(t -> "processing".equals(t.getStatus()))
                .filter(t -> t.getCreated_at() != null && t.getCreated_at().isBefore(backlogDeadline))
                .count();
        if (backlog > 0) {
            alerts.add(derivedAlert("derived:export_backlog", "warning", "export", "导出任务队列积压",
                    backlog + " 项任务处理超过 30 分钟，请检查导出服务状态", LocalDateTime.now()));
        }
    }

    /**
     * 系统日志类告警规则：近 1 小时 error 日志计数（logs_by_type 分布无 status 维度，需单独过滤）
     */
    private void addLogErrorAlert(List<Map<String, Object>> alerts, List<Sys_Log> logs) {
        LocalDateTime windowStart = LocalDateTime.now().minusHours(1);
        long recentErrors = logs.stream()
                .filter(l -> "error".equals(l.getStatus()))
                .filter(l -> l.getCreate_at() != null && l.getCreate_at().isAfter(windowStart))
                .count();
        if (recentErrors > 0) {
            alerts.add(derivedAlert("derived:system_error", "danger", "system", "系统错误日志激增",
                    "近 1 小时产生 " + recentErrors + " 条 error 日志，请前往系统日志排查", LocalDateTime.now()));
        }
    }

    /**
     * 构造一条派生告警（id 为派生指纹，如 derived:export_failed）
     */
    private Map<String, Object> derivedAlert(String id, String level, String source,
                                             String title, String detail, LocalDateTime createdAt) {
        Map<String, Object> alert = new LinkedHashMap<>();
        alert.put("id", id);
        alert.put("level", level);
        alert.put("source", source);
        alert.put("title", title);
        alert.put("detail", detail);
        alert.put("status", "open");
        alert.put("created_at", createdAt);
        return alert;
    }

    /**
     * 告警严重度排序权重：danger → warning → info → 其它
     */
    private int severityWeight(String level) {
        return switch (level == null ? "" : level) {
            case "danger" -> 0;
            case "warning" -> 1;
            case "info" -> 2;
            default -> 9;
        };
    }

    /**
     * 取时间列表中最新的一条（过滤 null，空列表返回 null）
     */
    private LocalDateTime latestTime(List<LocalDateTime> times) {
        return times.stream().filter(Objects::nonNull).max(Comparator.naturalOrder()).orElse(null);
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
                (dto.getUser_id() == null ? "all" : dto.getUser_id()) + ":" +
                blankToAll(dto.getKeyword()) + ":" +
                (dto.getStart_time() == null ? "all" : dto.getStart_time()) + ":" +
                (dto.getEnd_time() == null ? "all" : dto.getEnd_time()) + ":p" +
                dto.getPage() + ":s" + dto.getSize();
    }

    private String blankToAll(String value) {
        return value == null || value.isBlank() ? "all" : value;
    }

    private <T> long countSince(List<T> items, java.util.function.Function<T, LocalDateTime> timeGetter, LocalDateTime start) {
        return items.stream()
                .map(timeGetter)
                .filter(Objects::nonNull)
                .filter(time -> !time.isBefore(start))
                .count();
    }

    private <T> Map<String, Long> groupCount(List<T> items, java.util.function.Function<T, String> keyGetter) {
        Map<String, Long> result = new LinkedHashMap<>();
        for (T item : items) {
            String key = keyGetter.apply(item);
            if (key == null || key.isBlank()) {
                key = "unknown";
            }
            result.put(key, result.getOrDefault(key, 0L) + 1);
        }
        return result;
    }

    private Map<String, Long> mergeCounts(Map<String, Long> left, Map<String, Long> right) {
        Map<String, Long> result = new LinkedHashMap<>(left);
        right.forEach((key, value) -> result.put(key, result.getOrDefault(key, 0L) + value));
        return result;
    }

    private Map<String, Long> auditTypeStatusCount(List<Adm_Audit> audits) {
        Map<String, Long> result = new LinkedHashMap<>();
        for (Adm_Audit audit : audits) {
            String type = audit.getAudit_type() == null ? "unknown" : audit.getAudit_type();
            String status = audit.getStatus() == null ? "unknown" : audit.getStatus();
            String key = type + ":" + status;
            result.put(key, result.getOrDefault(key, 0L) + 1);
        }
        return result;
    }

    private double rate(long numerator, long denominator) {
        if (denominator <= 0) {
            return 0.0;
        }
        return Math.round((numerator * 10000.0 / denominator)) / 100.0;
    }

    private long averageExportDurationMs(List<Exp_Task> exportTasks) {
        List<Long> durations = exportTasks.stream()
                .filter(t -> t.getStarted_at() != null && t.getCompleted_at() != null)
                .map(t -> Duration.between(t.getStarted_at(), t.getCompleted_at()).toMillis())
                .filter(v -> v >= 0)
                .toList();
        if (durations.isEmpty()) {
            return 0;
        }
        return Math.round(durations.stream().mapToLong(Long::longValue).average().orElse(0));
    }

    private List<Map<String, Object>> buildSevenDayTrend(List<Sys_User> users,
                                                         List<Res_Material> materials,
                                                         List<Adm_Resource> platformResources,
                                                         List<AI_Task> aiTasks,
                                                         List<Exp_Task> exportTasks,
                                                         List<Com_Content> communityContents,
                                                         List<Sys_Log> logs) {
        List<Map<String, Object>> trend = new ArrayList<>();
        LocalDate today = LocalDate.now();
        for (int i = 6; i >= 0; i--) {
            LocalDate date = today.minusDays(i);
            LocalDateTime start = date.atStartOfDay();
            LocalDateTime end = date.plusDays(1).atStartOfDay();
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("date", date.toString());
            row.put("new_users", countBetween(users, Sys_User::getCreated_at, start, end));
            row.put("new_resources", countBetween(materials, Res_Material::getCreated_at, start, end)
                    + countBetween(platformResources, Adm_Resource::getCreated_at, start, end));
            row.put("ai_tasks", countBetween(aiTasks, AI_Task::getCreated_at, start, end));
            row.put("export_tasks", countBetween(exportTasks, Exp_Task::getCreated_at, start, end));
            row.put("community_contents", countBetween(communityContents, Com_Content::getCreated_at, start, end));
            row.put("logs", countBetween(logs, Sys_Log::getCreate_at, start, end));
            trend.add(row);
        }
        return trend;
    }

    private <T> long countBetween(List<T> items, java.util.function.Function<T, LocalDateTime> timeGetter,
                                  LocalDateTime start, LocalDateTime end) {
        return items.stream()
                .map(timeGetter)
                .filter(Objects::nonNull)
                .filter(time -> !time.isBefore(start) && time.isBefore(end))
                .count();
    }

    private List<Map<String, Object>> recentActivities(List<Sys_Log> logs, int limit) {
        return logs.stream()
                .sorted(Comparator.comparing(Sys_Log::getCreate_at,
                        Comparator.nullsLast(Comparator.reverseOrder())))
                .limit(limit)
                .map(log -> {
                    Map<String, Object> item = new LinkedHashMap<>();
                    item.put("id", log.getId());
                    item.put("user_id", log.getUser_id());
                    item.put("log_type", log.getLog_type());
                    item.put("module", log.getModule());
                    item.put("action", log.getAction());
                    item.put("target_type", log.getTarget_type());
                    item.put("target_id", log.getTarget_id());
                    item.put("status", log.getStatus());
                    item.put("created_at", log.getCreate_at());
                    return item;
                })
                .toList();
    }

    private List<LogVO> filterLogs(LogQueryDTO dto, String forcedType) {
        String keyword = dto.getKeyword() == null ? "" : dto.getKeyword().trim().toLowerCase();
        return logMapper.findAll().stream()
                .filter(l -> forcedType == null || forcedType.equals(l.getLog_type()))
                .filter(l -> dto.getLog_type() == null || dto.getLog_type().isBlank() || dto.getLog_type().equals(l.getLog_type()))
                .filter(l -> dto.getModule() == null || dto.getModule().isBlank() || dto.getModule().equals(l.getModule()))
                .filter(l -> dto.getUser_id() == null || dto.getUser_id().equals(l.getUser_id()))
                .filter(l -> dto.getStart_time() == null || l.getCreate_at() != null && !l.getCreate_at().isBefore(dto.getStart_time()))
                .filter(l -> dto.getEnd_time() == null || l.getCreate_at() != null && !l.getCreate_at().isAfter(dto.getEnd_time()))
                .filter(l -> keyword.isEmpty()
                        || (l.getAction() != null && l.getAction().toLowerCase().contains(keyword))
                        || (l.getDetail() != null && l.getDetail().toLowerCase().contains(keyword)))
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


