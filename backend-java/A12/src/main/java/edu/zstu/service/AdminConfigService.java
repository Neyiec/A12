package edu.zstu.service;

import edu.zstu.dto.ConfigDTO;
import edu.zstu.dto.RollbackDTO;
import edu.zstu.vo.ConfigVO;

import java.util.List;
import java.util.Map;

/**
 * 后台 — AI配置、安全策略、监控告警 Service 接口
 */
public interface AdminConfigService {
    List<ConfigVO> listAiConfigs(String configGroup);
    ConfigVO createAiConfig(ConfigDTO dto);
    Map<String, Object> publishAiConfig(Integer id);
    ConfigVO rollbackAiConfig(Integer id, RollbackDTO dto);
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
