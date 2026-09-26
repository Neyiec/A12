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

@Slf4j
@Service
public class KafkaEventPublisher {
    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;
    private final boolean enabled;
    private final long timeoutSeconds;
    private final String resourceTopic;
    private final String classroomTopic;
    private final String feedbackTopic;

    public KafkaEventPublisher(KafkaTemplate<String, String> kafkaTemplate, ObjectMapper objectMapper,
            @Value("${a12.kafka.enabled:false}") boolean enabled,
            @Value("${a12.kafka.publish-timeout-seconds:3}") long timeoutSeconds,
            @Value("${a12.kafka.topics.resource-index-request:a12.resource.index.requested}") String resourceTopic,
            @Value("${a12.kafka.topics.classroom-event:a12.classroom.events}") String classroomTopic,
            @Value("${a12.kafka.topics.teacher-feedback:a12.teacher.feedback}") String feedbackTopic) {
        this.kafkaTemplate = kafkaTemplate; this.objectMapper = objectMapper; this.enabled = enabled;
        this.timeoutSeconds = timeoutSeconds; this.resourceTopic = resourceTopic;
        this.classroomTopic = classroomTopic; this.feedbackTopic = feedbackTopic;
    }

    public PublishResult publishResourceIndex(Map<String, Object> payload) {
        return publish(resourceTopic, payload.getOrDefault("source_type", "unknown") + ":" +
                payload.getOrDefault("resource_id", "unknown"), "resource.index.requested", payload);
    }
    public PublishResult publishClassroomEvent(Map<String, Object> payload) {
        return publish(classroomTopic, String.valueOf(payload.getOrDefault("project_id", "unknown")),
                "classroom.event.recorded", payload);
    }
    public PublishResult publishTeacherFeedback(Map<String, Object> payload) {
        return publish(feedbackTopic, String.valueOf(payload.getOrDefault("user_id", "unknown")),
                "teacher.feedback.recorded", payload);
    }

    private PublishResult publish(String topic, String key, String type, Map<String, Object> payload) {
        String eventId = UUID.randomUUID().toString();
        if (!enabled) return new PublishResult(false, eventId);
        Map<String, Object> event = new LinkedHashMap<>();
        event.put("event_id", eventId); event.put("event_type", type); event.put("schema_version", 1);
        event.put("occurred_at", Instant.now().toString()); event.put("payload", payload);
        try {
            kafkaTemplate.send(topic, key, objectMapper.writeValueAsString(event)).get(timeoutSeconds, TimeUnit.SECONDS);
            return new PublishResult(true, eventId);
        } catch (Exception e) {
            log.warn("Kafka publish failed, topic={}, key={}, falling back", topic, key, e);
            return new PublishResult(false, eventId);
        }
    }

    public record PublishResult(boolean accepted, String eventId) {}
}
