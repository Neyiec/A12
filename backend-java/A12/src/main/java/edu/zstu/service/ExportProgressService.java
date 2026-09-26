package edu.zstu.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.data.redis.connection.stream.*;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.time.Duration;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.Executor;

@Slf4j
@Service
public class ExportProgressService {
    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper;
    private final Executor executor;

    public ExportProgressService(StringRedisTemplate redisTemplate, ObjectMapper objectMapper,
                                 @Qualifier("exportEventExecutor") Executor executor) {
        this.redisTemplate = redisTemplate; this.objectMapper = objectMapper; this.executor = executor;
    }

    public void publish(int taskId, String status, int progress, String message) {
        String key = key(taskId);
        Map<String, String> payload = new LinkedHashMap<>();
        payload.put("task_id", String.valueOf(taskId)); payload.put("status", status);
        payload.put("progress", String.valueOf(progress)); payload.put("message", message == null ? "" : message);
        payload.put("timestamp", Instant.now().toString());
        try {
            redisTemplate.opsForStream().add(StreamRecords.mapBacked(payload).withStreamKey(key));
            redisTemplate.opsForStream().trim(key, 500);
            redisTemplate.expire(key, Duration.ofHours(24));
            redisTemplate.opsForValue().set("a12:export:state:" + taskId,
                    objectMapper.writeValueAsString(payload), Duration.ofHours(24));
        } catch (Exception e) { log.warn("Publish export progress failed, taskId={}", taskId, e); }
    }

    public SseEmitter stream(int taskId, String lastEventId) {
        SseEmitter emitter = new SseEmitter(620_000L);
        executor.execute(() -> relay(taskId, lastEventId, emitter));
        return emitter;
    }

    private void relay(int taskId, String lastEventId, SseEmitter emitter) {
        String offset = lastEventId == null || lastEventId.isBlank() ? "0-0" : lastEventId;
        long deadline = System.currentTimeMillis() + 600_000L;
        try {
            while (System.currentTimeMillis() < deadline) {
                List<MapRecord<String, Object, Object>> records = redisTemplate.opsForStream().read(
                        StreamReadOptions.empty().count(50).block(Duration.ofSeconds(15)),
                        StreamOffset.create(key(taskId), ReadOffset.from(offset)));
                if (records == null || records.isEmpty()) { emitter.send(SseEmitter.event().name("heartbeat").data("{}")); continue; }
                for (MapRecord<String, Object, Object> record : records) {
                    offset = record.getId().getValue();
                    Map<String, Object> data = new LinkedHashMap<>();
                    record.getValue().forEach((k, v) -> data.put(String.valueOf(k), v));
                    emitter.send(SseEmitter.event().id(offset).name("progress").data(objectMapper.writeValueAsString(data)));
                    if (List.of("success", "failed", "cancelled").contains(String.valueOf(data.get("status")))) {
                        emitter.complete(); return;
                    }
                }
            }
            emitter.complete();
        } catch (Exception e) { log.debug("Export progress stream closed, taskId={}: {}", taskId, e.getMessage()); emitter.complete(); }
    }

    private String key(int taskId) { return "a12:events:export:" + taskId; }
}
