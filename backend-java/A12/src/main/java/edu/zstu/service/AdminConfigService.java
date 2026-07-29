package edu.zstu.service;

import edu.zstu.dto.ConfigDTO;
import edu.zstu.dto.LogQueryDTO;
import edu.zstu.dto.RollbackDTO;
import edu.zstu.dto.SecurityPolicyDTO;
import edu.zstu.utils.PageResult;
import edu.zstu.vo.ConfigVO;
import edu.zstu.vo.LogVO;

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
    List<ConfigVO> listSecurityPolicies();
    ConfigVO updateSecurityPolicy(String id, SecurityPolicyDTO dto);
    Map<String, Object> publishSecurityPolicy(String id);
    PageResult<LogVO> listAuditLogs(LogQueryDTO dto);
    PageResult<LogVO> listSystemLogs(LogQueryDTO dto);
    Map<String, Object> getDashboard();
    PageResult<Map<String, Object>> listAlerts(String level, String source, String status, int page, int size);
    Map<String, Object> getAlert(String id);
    void acknowledgeAlert(String id);
    void resolveAlert(String id, String resolution);
}
