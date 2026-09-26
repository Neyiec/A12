package edu.zstu.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.zstu.mapper.AdmResourceMapper;
import edu.zstu.mapper.ResMaterialMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Service;

import java.util.Map;

@Slf4j
@Service
public class KafkaResourceIndexResultListener {
    private final ObjectMapper objectMapper;
    private final ResMaterialMapper materialMapper;
    private final AdmResourceMapper resourceMapper;

    public KafkaResourceIndexResultListener(ObjectMapper objectMapper, ResMaterialMapper materialMapper,
                                            AdmResourceMapper resourceMapper) {
        this.objectMapper = objectMapper; this.materialMapper = materialMapper; this.resourceMapper = resourceMapper;
    }

    @KafkaListener(topics = "${a12.kafka.topics.resource-index-result:a12.resource.index.result}",
            groupId = "a12-java-resource-status", autoStartup = "${a12.kafka.enabled:false}")
    public void onResourceIndexResult(String body) {
        try {
            Map<String, Object> event = objectMapper.readValue(body, new TypeReference<>() {});
            String sourceType = String.valueOf(event.get("source_type"));
            Integer resourceId = Integer.valueOf(String.valueOf(event.get("resource_id")));
            String status = "failed".equals(String.valueOf(event.get("status"))) ? "failed" : "completed";
            String error = "failed".equals(status) ? String.valueOf(event.getOrDefault("error_message", "索引失败")) : null;
            if ("personal".equals(sourceType)) materialMapper.updateAiIndexStatus(resourceId, status, error);
            else if ("public".equals(sourceType)) resourceMapper.updateAiIndexStatus(resourceId, status, error);
            else throw new IllegalArgumentException("Unknown source_type: " + sourceType);
        } catch (Exception e) {
            log.error("Apply Kafka resource index result failed: {}", body, e);
            throw new RuntimeException(e);
        }
    }
}
