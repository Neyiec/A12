package edu.zstu.controller;

import edu.zstu.dto.ConfigDTO;
import edu.zstu.dto.LogQueryDTO;
import edu.zstu.dto.RollbackDTO;
import edu.zstu.dto.SecurityPolicyDTO;
import edu.zstu.dto.AlertResolveDTO;
import edu.zstu.service.AdminConfigService;
import edu.zstu.utils.Result;
import edu.zstu.vo.ConfigVO;
import edu.zstu.vo.LogVO;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * 后台 — AI配置、安全策略、监控告警 Controller
 * API-98~111：AI配置、安全策略、日志看板、告警
 */
@RestController
@RequestMapping("/api/v1/admin")
public class AdminConfigController {

    private final AdminConfigService adminConfigService;

    public AdminConfigController(AdminConfigService adminConfigService) {
        this.adminConfigService = adminConfigService;
    }

    /**
     * API-98 查询AI配置列表
     *
     * @param config_group 配置分组（选填）
     * @return AI配置列表 {@link ConfigVO}
     */
    @GetMapping("/ai-configs")
    public Result<List<ConfigVO>> listAiConfigs(@RequestParam(required = false) String config_group) {
        try {
            return Result.success(adminConfigService.listAiConfigs(config_group));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-99 创建AI配置
     *
     * @param dto 配置参数 {@link ConfigDTO}
     * @return 创建的配置信息 {@link ConfigVO}
     */
    @PostMapping("/ai-configs")
    public Result<ConfigVO> createAiConfig(@RequestBody ConfigDTO dto) {
        try {
            return Result.success(adminConfigService.createAiConfig(dto));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-100 发布AI配置
     *
     * @param id 配置ID（路径参数）
     * @return 各节点加载状态
     */
    @PostMapping("/ai-configs/{id}/publish")
    public Result<Map<String, Object>> publishAiConfig(@PathVariable Integer id) {
        try {
            return Result.success(adminConfigService.publishAiConfig(id));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-101 回滚AI配置
     *
     * @param id  配置ID（路径参数）
     * @param dto 回滚参数
     * @return 回滚后的当前配置 {@link ConfigVO}
     */
    @PostMapping("/ai-configs/{id}/rollback")
    public Result<ConfigVO> rollbackAiConfig(@PathVariable Integer id, @RequestBody RollbackDTO dto) {
        try {
            return Result.success(adminConfigService.rollbackAiConfig(id, dto));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-102 获取安全策略
     */
    @GetMapping("/security-policies")
    public Result<?> listSecurityPolicies() {
        return Result.success();
    }

    /**
     * API-103 更新安全策略
     */
    @PutMapping("/security-policies/{id}")
    public Result<ConfigVO> updateSecurityPolicy(@PathVariable String id, @RequestBody SecurityPolicyDTO dto) {
        return Result.success();
    }

    /**
     * API-104 发布安全策略
     */
    @PostMapping("/security-policies/{id}/publish")
    public Result<?> publishSecurityPolicy(@PathVariable String id) {
        return Result.success();
    }

    /**
     * API-105 查询审计日志
     */
    @GetMapping("/audit-logs")
    public Result<?> listAuditLogs(LogQueryDTO dto) {
        return Result.success();
    }

    /**
     * API-106 查询系统日志
     */
    @GetMapping("/system-logs")
    public Result<?> listSystemLogs(LogQueryDTO dto) {
        return Result.success();
    }

    /**
     * API-107 获取数据看板
     */
    @GetMapping("/dashboard")
    public Result<?> getDashboard() {
        return Result.success();
    }

    /**
     * API-108 分页查询告警
     */
    @GetMapping("/alerts")
    public Result<?> listAlerts(@RequestParam(required = false) String level,
                                @RequestParam(required = false) String source,
                                @RequestParam(required = false) String status,
                                @RequestParam(defaultValue = "1") int page,
                                @RequestParam(defaultValue = "10") int size) {
        return Result.success();
    }

    /**
     * API-109 获取告警详情
     */
    @GetMapping("/alerts/{id}")
    public Result<?> getAlert(@PathVariable String id) {
        return Result.success();
    }

    /**
     * API-110 确认告警
     */
    @PostMapping("/alerts/{id}/acknowledge")
    public Result<Void> acknowledgeAlert(@PathVariable String id) {
        return Result.success();
    }

    /**
     * API-111 解决告警
     */
    @PostMapping("/alerts/{id}/resolve")
    public Result<Void> resolveAlert(@PathVariable String id, @RequestBody AlertResolveDTO dto) {
        return Result.success();
    }
}
