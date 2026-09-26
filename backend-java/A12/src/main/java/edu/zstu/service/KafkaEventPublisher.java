package edu.zstu.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

/** 发布可回放业务事件；Kafka 关闭或不可用时由调用方回退原 HTTP 链路。 */
@Slf4j
@Service
public class KafkaEventPublisher {
    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;
    private final boolean enabled;
    private final long timeoutSeconds;
    private final String resourceIndexRequestTopic;
    private final String classroomEventTopic;
    private final String teacherFeedbackTopic;

    public KafkaEventPublisher(
            KafkaTemplate<String, String> kafkaTemplate,
            ObjectMapper objectMapper,
            @Value("${a12.kafka.enabled:false}") boolean enabled,
            @Value("${a12.kafka.publish-timeout-seconds:3}") long timeoutSeconds,
            @Value("${a12.kafka.topics.resource-index-request:a12.resource.index.requested}") String resourceIndexRequestTopic,
            @Value("${a12.kafka.topics.classroom-event:a12.classroom.events}") String classroomEventTopic,
            @Value("${a12.kafka.topics.teacher-feedback:a12.teacher.feedback}") String teacherFeedbackTopic) {
        this.kafkaTemplate = kafkaTemplate;
        this.objectMapper = objectMapper;
        this.enabled = enabled;
        this.timeoutSeconds = timeoutSeconds;
        this.resourceIndexRequestTopic = resourceIndexRequestTopic;
        this.classroomEventTopic = classroomEventTopic;
        this.teacherFeedbackTopic = teacherFeedbackTopic;
    }

    public PublishResult publishResourceIndex(Map<String, Object> payload) {
        String sourceType = String.valueOf(payload.getOrDefault("source_type", "unknown"));
        String resourceId = String.valueOf(payload.getOrDefault("resource_id", "unknown"));
        return publish(resourceIndexRequestTopic, sourceType + ":" + resourceId,
                "resource.index.requested", payload);
    }

    public PublishResult publishClassroomEvent(Map<String, Object> payload) {
        String key = String.valueOf(payload.getOrDefault("project_id", payload.getOrDefault("user_id", "unknown")));
        return publish(classroomEventTopic, key, "classroom.event.recorded", payload);
    }

    public PublishResult publishTeacherFeedback(Map<String, Object> payload) {
        return publish(teacherFeedbackTopic, String.valueOf(payload.getOrDefault("user_id", "unknown")),
                "teacher.feedback.recorded", payload);
    }

    private PublishResult publish(String topic, String key, String eventType, Map<String, Object> payload) {
        String eventId = UUID.randomUUID().toString();
        if (!enabled) return new PublishResult(false, eventId);
        Map<String, Object> event = new LinkedHashMap<>();
        event.put("event_id", eventId);
        event.put("event_type", eventType);
        event.put("schema_version", 1);
        event.put("occurred_at", Instant.now().toString());
        event.put("payload", payload);
        try {
            String body = objectMapper.writeValueAsString(event);
            kafkaTemplate.send(topic, key, body).get(timeoutSeconds, TimeUnit.SECONDS);
            return new PublishResult(true, eventId);
        } catch (Exception e) {
            log.warn("Kafka publish failed, topic={}, key={}, falling back", topic, key, e);
            return new PublishResult(false, eventId);
        }
    }

    public record PublishResult(boolean accepted, String eventId) {}
}
