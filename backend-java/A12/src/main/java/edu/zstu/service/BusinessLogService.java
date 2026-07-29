package edu.zstu.service;

import cn.hutool.json.JSONUtil;
import edu.zstu.entity.Sys_Log;
import edu.zstu.mapper.SysLogMapper;
import edu.zstu.utils.CurrentHolder;
import edu.zstu.utils.RedisCacheUtil;
import org.springframework.stereotype.Service;

import java.util.Map;

@Service
public class BusinessLogService {
    private final SysLogMapper logMapper;
    private final RedisCacheUtil redisCacheUtil;

    public BusinessLogService(SysLogMapper logMapper, RedisCacheUtil redisCacheUtil) {
        this.logMapper = logMapper;
        this.redisCacheUtil = redisCacheUtil;
    }

    public void record(String logType, String module, String action, String targetType, Integer targetId) {
        record(logType, module, action, targetType, targetId, Map.of());
    }

    public void record(String logType, String module, String action, String targetType,
                       Integer targetId, Map<String, Object> detail) {
        Sys_Log log = new Sys_Log();
        Integer currentId = CurrentHolder.getCurrentId();
        log.setUser_id(currentId == null ? 0 : currentId);
        log.setLog_type(logType);
        log.setModule(module);
        log.setAction(action);
        log.setTarget_type(targetType);
        log.setTarget_id(targetId == null ? 0 : targetId);
        log.setDetail(detail == null || detail.isEmpty() ? "{}" : JSONUtil.toJsonStr(detail));
        log.setIp("");
        logMapper.insert(log);
        redisCacheUtil.delete("admin:dashboard");
    }
}
