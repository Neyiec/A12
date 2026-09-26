package edu.zstu.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.util.List;
import java.util.UUID;

/** Redis 可靠列表：任务先移入 processing，完成后确认；过期任务可恢复。 */
@Slf4j
@Component
public class RedisExportTaskQueue {
    private static final String QUEUE = "a12:queue:export";
    private static final String PROCESSING = "a12:queue:export:processing";
    private final StringRedisTemplate redisTemplate;
    private final String workerId = "java-" + UUID.randomUUID().toString().substring(0, 8);

    public RedisExportTaskQueue(StringRedisTemplate redisTemplate) { this.redisTemplate = redisTemplate; }

    public boolean enqueue(int taskId) {
        try { redisTemplate.opsForList().leftPush(QUEUE, String.valueOf(taskId)); return true; }
        catch (Exception e) { log.warn("Redis export queue unavailable, taskId={}", taskId, e); return false; }
    }

    public String claim() {
        try { return redisTemplate.opsForList().rightPopAndLeftPush(QUEUE, PROCESSING); }
        catch (Exception e) { log.warn("Redis export queue claim failed", e); return null; }
    }

    public boolean acquireTaskLock(String taskId) {
        try { return Boolean.TRUE.equals(redisTemplate.opsForValue().setIfAbsent(
                "a12:lock:export:" + taskId, workerId, Duration.ofMinutes(20))); }
        catch (Exception e) { log.warn("Redis export lock unavailable, taskId={}", taskId, e); return false; }
    }

    public void acknowledge(String taskId) {
        try {
            redisTemplate.opsForList().remove(PROCESSING, 1, taskId);
            redisTemplate.delete("a12:lock:export:" + taskId);
        } catch (Exception e) { log.warn("Redis export acknowledge failed, taskId={}", taskId, e); }
    }

    public void discardDuplicateClaim(String taskId) {
        try { redisTemplate.opsForList().remove(PROCESSING, 1, taskId); }
        catch (Exception e) { log.warn("Discard duplicate export claim failed, taskId={}", taskId, e); }
    }

    public int recoverStaleClaims() {
        int recovered = 0;
        try {
            List<String> ids = redisTemplate.opsForList().range(PROCESSING, 0, -1);
            if (ids == null) return 0;
            for (String id : ids) {
                if (Boolean.TRUE.equals(redisTemplate.hasKey("a12:lock:export:" + id))) continue;
                Long removed = redisTemplate.opsForList().remove(PROCESSING, 1, id);
                if (removed != null && removed > 0) { redisTemplate.opsForList().leftPush(QUEUE, id); recovered++; }
            }
        } catch (Exception e) { log.warn("Recover stale export claims failed", e); }
        return recovered;
    }
}
