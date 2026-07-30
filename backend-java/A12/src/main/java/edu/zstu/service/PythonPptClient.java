package edu.zstu.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Component
public class PythonPptClient {
    private final ObjectMapper objectMapper;
    private final HttpClient httpClient;
    private final String baseUrl;
    private final long requestTimeoutSeconds;

    public PythonPptClient(
            ObjectMapper objectMapper,
            @Value("${a12.python.base-url:http://127.0.0.1:8001}") String baseUrl,
            @Value("${a12.python.connect-timeout-seconds:5}") long connectTimeoutSeconds,
            @Value("${a12.python.request-timeout-seconds:180}") long requestTimeoutSeconds) {
        this.objectMapper = objectMapper;
        this.baseUrl = baseUrl.replaceAll("/+$", "");
        this.requestTimeoutSeconds = requestTimeoutSeconds;
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(connectTimeoutSeconds))
                .build();
    }

    public OutlineChatResult streamOutlineChat(Map<String, Object> payload) {
        try {
            String body = objectMapper.writeValueAsString(payload);
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(baseUrl + "/api/v1/python/outlines/chat/stream"))
                    .timeout(Duration.ofSeconds(requestTimeoutSeconds))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(body))
                    .build();
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() < 200 || response.statusCode() >= 300) {
                throw new RuntimeException("Python服务调用失败，HTTP " + response.statusCode());
            }
            return parseSse(response.body());
        } catch (Exception e) {
            throw new RuntimeException("调用Python大纲服务失败: " + e.getMessage(), e);
        }
    }

    public Map<String, Object> syncResourceIndex(Map<String, Object> payload) {
        return postJson("/api/v1/python/resources/index/sync", payload);
    }

    public Map<String, Object> bootstrapResourceIndex(List<Map<String, Object>> resources, boolean forceReparse) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("resources", resources);
        payload.put("force_reparse", forceReparse);
        return postJson("/api/v1/python/resources/index/bootstrap", payload);
    }

    public Map<String, Object> updateResourceIndexMetadata(Map<String, Object> payload) {
        return patchJson("/api/v1/python/resources/index/metadata", payload);
    }

    public Map<String, Object> deleteResourceIndex(String sourceType, Object resourceId) {
        try {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(baseUrl + "/api/v1/python/resources/index/" + sourceType + "/" + resourceId))
                    .timeout(Duration.ofSeconds(requestTimeoutSeconds))
                    .DELETE()
                    .build();
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            return parseJsonResponse(response);
        } catch (Exception e) {
            throw new RuntimeException("删除Python资源索引失败: " + e.getMessage(), e);
        }
    }

    private Map<String, Object> postJson(String path, Map<String, Object> payload) {
        return sendJson("POST", path, payload);
    }

    private Map<String, Object> patchJson(String path, Map<String, Object> payload) {
        return sendJson("PATCH", path, payload);
    }

    private Map<String, Object> sendJson(String method, String path, Map<String, Object> payload) {
        try {
            String body = objectMapper.writeValueAsString(payload);
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(baseUrl + path))
                    .timeout(Duration.ofSeconds(requestTimeoutSeconds))
                    .header("Content-Type", "application/json")
                    .method(method, HttpRequest.BodyPublishers.ofString(body))
                    .build();
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            return parseJsonResponse(response);
        } catch (Exception e) {
            throw new RuntimeException("调用Python资源索引服务失败: " + e.getMessage(), e);
        }
    }

    private Map<String, Object> parseJsonResponse(HttpResponse<String> response) throws Exception {
        if (response.statusCode() < 200 || response.statusCode() >= 300) {
            throw new RuntimeException("Python服务调用失败，HTTP " + response.statusCode());
        }
        return objectMapper.readValue(response.body(), new TypeReference<>() {});
    }

    private OutlineChatResult parseSse(String body) throws Exception {
        OutlineChatResult result = new OutlineChatResult();
        for (String chunk : body.split("\\R\\R")) {
            String event = null;
            String data = null;
            for (String line : chunk.split("\\R")) {
                if (line.startsWith("event:")) {
                    event = line.substring("event:".length()).trim();
                } else if (line.startsWith("data:")) {
                    data = line.substring("data:".length()).trim();
                }
            }
            if (event == null || data == null || data.isBlank()) {
                continue;
            }
            Map<String, Object> parsed = objectMapper.readValue(data, new TypeReference<>() {});
            if ("session".equals(event)) {
                result.pythonSessionId = stringValue(parsed.get("session_id"));
            } else if ("question".equals(event)) {
                result.status = "need_clarification";
                result.pythonSessionId = stringValue(parsed.get("session_id"));
                result.question = stringValue(parsed.get("question"));
                result.intent = parsed.get("intent");
            } else if ("outline_delta".equals(event)) {
                Object slide = parsed.get("slide");
                if (slide != null) {
                    result.outlineDeltas.add(slide);
                }
            } else if ("memory".equals(event)) {
                result.memory = parsed;
            } else if ("final".equals(event)) {
                result.status = "completed";
                result.pythonSessionId = stringValue(parsed.get("session_id"));
                result.outlineId = stringValue(parsed.get("outline_id"));
                result.title = stringValue(parsed.get("title"));
                result.finalData = parsed;
                result.outline = parsed.get("outline");
                result.slides = parsed.get("slides");
            } else if ("error".equals(event)) {
                result.status = "failed";
                result.errorMessage = stringValue(parsed.get("message"));
            }
        }
        return result;
    }

    private String stringValue(Object value) {
        return value == null ? null : String.valueOf(value);
    }

    public String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (Exception e) {
            return "{}";
        }
    }

    public static class OutlineChatResult {
        public String status = "unknown";
        public String pythonSessionId;
        public String outlineId;
        public String title;
        public String question;
        public String errorMessage;
        public Object intent;
        public Object outline;
        public Object slides;
        public Object memory;
        public Map<String, Object> finalData = new LinkedHashMap<>();
        public List<Object> outlineDeltas = new java.util.ArrayList<>();
    }
}
