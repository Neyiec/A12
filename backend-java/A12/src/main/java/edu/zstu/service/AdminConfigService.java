package edu.zstu.service;

/**
 * 后台 — AI配置、安全策略、监控告警 Service 接口<br>提供AI模型配置管理、安全策略管理、审计日志、数据看板、告警管理等业务方法。
 */

public interface AdminConfigService {
    Object listAiConfigs();
    Object createAiConfig();
    Object publishAiConfig(String id);
    Object rollbackAiConfig(String id);
    Object listSecurityPolicies();
    Object updateSecurityPolicy(String id);
    Object publishSecurityPolicy(String id);
    Object listAuditLogs();
    Object listSystemLogs();
    Object getDashboard();
    Object listAlerts();
    Object getAlert(String id);
    Object acknowledgeAlert(String id);
    Object resolveAlert(String id);
}

