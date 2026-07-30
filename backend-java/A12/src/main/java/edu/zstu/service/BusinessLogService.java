package edu.zstu.service;

import cn.hutool.json.JSONUtil;
import edu.zstu.entity.Sys_Log;
import edu.zstu.mapper.SysLogMapper;
import edu.zstu.utils.CurrentHolder;
import edu.zstu.utils.RedisCacheUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.stereotype.Service;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.util.Map;
import java.util.concurrent.Executor;

@Slf4j
@Service
public class BusinessLogService {
    private final SysLogMapper logMapper;
    private final RedisCacheUtil redisCacheUtil;
    private final Executor businessLogExecutor;

    public BusinessLogService(SysLogMapper logMapper, RedisCacheUtil redisCacheUtil,
                              @Qualifier("businessLogExecutor") Executor businessLogExecutor) {
        this.logMapper = logMapper;
        this.redisCacheUtil = redisCacheUtil;
        this.businessLogExecutor = businessLogExecutor;
    }

    public void record(String logType, String module, String action, String targetType, Integer targetId) {
        record(logType, module, action, targetType, targetId, Map.of());
    }

    public void record(String logType, String module, String action, String targetType,
                       Integer targetId, Map<String, Object> detail) {
        Sys_Log entry = new Sys_Log();
        Integer currentId = CurrentHolder.getCurrentId();
        entry.setUser_id(currentId == null ? 0 : currentId);
        entry.setLog_type(logType);
        entry.setModule(module);
        entry.setAction(action);
        entry.setTarget_type(targetType);
        entry.setTarget_id(targetId == null ? 0 : targetId);
        entry.setDetail(detail == null || detail.isEmpty() ? "{}" : JSONUtil.toJsonStr(detail));
        enrichRequestInfo(entry);
        businessLogExecutor.execute(() -> {
            try {
                logMapper.insert(entry);
                redisCacheUtil.delete("admin:dashboard");
                log.info("businessLog recorded type={}, module={}, action={}, targetType={}, targetId={}, userId={}",
                        logType, module, action, targetType, targetId, entry.getUser_id());
            } catch (Exception e) {
                log.warn("businessLog async insert failed type={}, module={}, action={}, targetType={}, targetId={}, userId={}",
                        logType, module, action, targetType, targetId, entry.getUser_id(), e);
            }
        });
    }

    private void enrichRequestInfo(Sys_Log entry) {
        try {
            ServletRequestAttributes attributes = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
            if (attributes == null) {
                entry.setIp("");
                entry.setStatus("success");
                return;
            }
            var request = attributes.getRequest();
            String forwardedFor = request.getHeader("X-Forwarded-For");
            entry.setIp(forwardedFor != null && !forwardedFor.isBlank()
                    ? forwardedFor.split(",")[0].trim()
                    : request.getRemoteAddr());
            entry.setRequest_id(request.getHeader("X-Request-Id"));
            entry.setMethod(request.getMethod());
            entry.setPath(request.getRequestURI());
            entry.setUser_agent(request.getHeader("User-Agent"));
            entry.setStatus("success");
        } catch (Exception ignored) {
            entry.setIp("");
            entry.setStatus("success");
        }
    }
}

