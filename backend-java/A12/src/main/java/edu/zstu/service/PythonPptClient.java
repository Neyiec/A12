package edu.zstu.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Stream;

@Slf4j
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
                // 强制 HTTP/1.1：JDK 默认 HTTP/2 会在新连接上发送 h2c Upgrade 前缀，
                // uvicorn 无法处理该升级，会以 400 "Invalid HTTP request received." 拒绝请求正文，
                // 导致 Python 服务偶发调用失败（正文被当作空）。
                .version(HttpClient.Version.HTTP_1_1)
                .build();
    }

    public Map<String, Object> health() {
        return getJson("/api/v1/python/health", Map.of());
    }

    public Map<String, Object> templates() {
        return getJson("/api/v1/python/templates", Map.of());
    }

    /**
     * 管理后台创建 PPT 模板 — Python 落盘为 {theme}.json
     * @param name         模板名称（即 theme / 文件名去后缀）
     * @param templateData 模板 JSON 文件文本内容（必须含 html_template 字段）
     * @param description  模板描述（选填）
     */
    public Map<String, Object> createTemplate(String name, String templateData, String description) {
        log.info("createTemplate name={}", name);
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("name", name);
        payload.put("template_data", templateData);
        if (description != null && !description.isBlank()) payload.put("description", description);
        return postJson("/api/v1/python/templates", payload);
    }

    /** 管理后台替换 PPT 模板内容（覆盖 {theme}.json，默认模板由 Python 侧拒绝） */
    public Map<String, Object> replaceTemplate(String theme, String templateData, String description) {
        log.info("replaceTemplate theme={}", theme);
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("template_data", templateData);
        if (description != null && !description.isBlank()) payload.put("description", description);
        return patchJson("/api/v1/python/templates/" + urlEncode(theme), payload);
    }

    /** 管理后台删除 PPT 模板（默认模板由 Python 侧拒绝） */
    public Map<String, Object> deleteTemplate(String theme) {
        log.info("deleteTemplate theme={}", theme);
        return deleteJson("/api/v1/python/templates/" + urlEncode(theme), Map.of());
    }

    /** 管理后台下载模板 JSON 文件（业务错误由 Python 以非 2xx 返回，此处抛出异常） */
    public PythonFileResult downloadTemplate(String theme) {
        try {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(baseUrl + "/api/v1/python/templates/" + urlEncode(theme) + "/file"))
                    .timeout(Duration.ofSeconds(requestTimeoutSeconds))
                    .GET()
                    .build();
            HttpResponse<byte[]> response = httpClient.send(request, HttpResponse.BodyHandlers.ofByteArray());
            log.info("downloadTemplate theme={}, statusCode={}", theme, response.statusCode());
            if (response.statusCode() < 200 || response.statusCode() >= 300) {
                throw new RuntimeException("Python服务调用失败，HTTP " + response.statusCode());
            }
            String contentType = response.headers().firstValue("content-type")
                    .orElse("application/json")
                    .split(";")[0]
                    .trim();
            String filename = response.headers().firstValue("content-disposition")
                    .map(this::filenameFromContentDisposition)
                    .filter(value -> value != null && !value.isBlank())
                    .orElse(theme + ".json");
            return new PythonFileResult(response.body(), contentType, filename);
        } catch (RuntimeException e) {
            throw e;
        } catch (Exception e) {
            throw new RuntimeException("下载Python模板文件失败: " + e.getMessage(), e);
        }
    }

    public Map<String, Object> uploadResource(byte[] fileBytes, String filename, String contentType) {
        return uploadFile("/api/v1/python/resources/upload", fileBytes, filename, contentType, Map.of());
    }

    public Map<String, Object> transcribeAudio(byte[] audioBytes, String filename, String contentType, String language) {
        Map<String, String> fields = new LinkedHashMap<>();
        if (language != null && !language.isBlank()) {
            fields.put("language", language);
        }
        return uploadFile("/api/v1/python/audio/asr", audioBytes, filename, contentType, fields);
    }

    public Map<String, Object> generateOutline(Map<String, Object> payload) {
        log.info("generateOutline title={}, subject={}", payload.get("title"), payload.get("subject"));
        return postJson("/api/v1/python/outlines/generate", payload);
    }

    public Map<String, Object> updateOutline(Map<String, Object> payload) {
        log.info("updateOutline hasOutline={}, instruction={}", payload.containsKey("outline"), payload.get("instruction"));
        return postJson("/api/v1/python/outlines/update", payload);
    }

    public Map<String, Object> recognizeIntent(Map<String, Object> payload) {
        log.info("recognizeIntent inputType={}, hasMessage={}", payload.get("input_type"), payload.containsKey("message"));
        return postJson("/api/v1/python/intent/recognize", payload);
    }

    public OutlineChatResult streamOutlineChat(Map<String, Object> payload) {
        try {
            log.info("streamOutlineChat hasSessionId={}, enableRag={}, enableWeb={}",
                    payload.containsKey("session_id"), payload.get("enable_rag"), payload.get("enable_web"));
            HttpResponse<String> response = postJsonResponse("/api/v1/python/outlines/chat/stream", payload);
            OutlineChatResult result = parseSse(response.body());
            log.info("streamOutlineChat parsed status={}, pythonSessionId={}, outlineId={}",
                    result.status, result.pythonSessionId, result.outlineId);
            return result;
        } catch (Exception e) {
            throw new RuntimeException("调用Python大纲服务失败: " + e.getMessage(), e);
        }
    }

    public String streamOutlineChatRaw(Map<String, Object> payload) {
        try {
            return postJsonResponse("/api/v1/python/outlines/chat/stream", payload).body();
        } catch (Exception e) {
            throw new RuntimeException("调用Python对话大纲流服务失败: " + e.getMessage(), e);
        }
    }

    public void streamOutlineChatToEmitter(Map<String, Object> payload, SseEmitter emitter) {
        streamToEmitter("/api/v1/python/outlines/chat/stream", payload, emitter);
    }

    public void streamWorkspaceChatToEmitter(Map<String, Object> payload, SseEmitter emitter) {
        streamToEmitter("/api/v1/python/workspace/chat/stream", payload, emitter);
    }

    public void streamPresentationToEmitter(Map<String, Object> payload, SseEmitter emitter) {
        streamToEmitter("/api/v1/python/presentations/generate/stream", payload, emitter);
    }

    private void streamToEmitter(String path, Map<String, Object> payload, SseEmitter emitter) {
        String event = "message";
        StringBuilder data = new StringBuilder();
        try {
            HttpResponse<Stream<String>> response = postJsonLinesResponse(path, payload);
            log.info("streamOutlineChatToEmitter statusCode={}", response.statusCode());
            try (Stream<String> lines = response.body()) {
                for (java.util.Iterator<String> iterator = lines.iterator(); iterator.hasNext(); ) {
                    String line = iterator.next();
                    if (line.isEmpty()) {
                        sendSseEvent(emitter, event, data);
                        event = "message";
                        data.setLength(0);
                    } else if (line.startsWith("event:")) {
                        event = line.substring("event:".length()).trim();
                    } else if (line.startsWith("data:")) {
                        if (data.length() > 0) {
                            data.append('\n');
                        }
                        data.append(line.substring("data:".length()).trim());
                    }
                }
            }
            sendSseEvent(emitter, event, data);
            emitter.complete();
        } catch (Exception e) {
            log.warn("streamOutlineChatToEmitter failed", e);
            try {
                emitter.send(SseEmitter.event().name("error").data(toJson(Map.of(
                        "message", "AI 服务调用失败: " + e.getMessage())),
                        org.springframework.http.MediaType.APPLICATION_JSON));
                emitter.complete();
            } catch (IOException | IllegalStateException disconnected) {
                emitter.completeWithError(e);
            }
        }
    }

    /**
     * 流式调用 Python 大纲对话：边读取边把每个 Python 事件原样透传给 SseEmitter，
     * 同时累计解析为 {@link OutlineChatResult}，供调用方在流结束后一次性落库。
     *
     * <p>事件与 Python 一致：session / question / outline_delta / memory / reflection / final / error。
     * 各事件 data 保持 Python 原始 JSON 结构。</p>
     *
     * @return 累计解析完成的结果（status 为 completed / need_clarification / failed）
     */
    public OutlineChatResult streamOutlineChatStreamed(Map<String, Object> payload, SseEmitter emitter) {
        OutlineChatResult result = new OutlineChatResult();
        try {
            log.info("streamOutlineChatStreamed enableRag={}, enableWeb={}",
                    payload.get("enable_rag"), payload.get("enable_web"));
            HttpResponse<Stream<String>> response = postJsonLinesResponse("/api/v1/python/outlines/chat/stream", payload);
            String event = "message";
            StringBuilder dataBuf = new StringBuilder();
            try (Stream<String> lines = response.body()) {
                for (java.util.Iterator<String> iterator = lines.iterator(); iterator.hasNext(); ) {
                    String line = iterator.next();
                    if (line.isEmpty()) {
                        if (dataBuf.length() > 0) {
                            handleStreamEvent(event, dataBuf.toString(), result, emitter);
                            dataBuf.setLength(0);
                        }
                        event = "message";
                    } else if (line.startsWith("event:")) {
                        event = line.substring("event:".length()).trim();
                    } else if (line.startsWith("data:")) {
                        if (dataBuf.length() > 0) {
                            dataBuf.append('\n');
                        }
                        dataBuf.append(line.substring("data:".length()).trim());
                    }
                }
            }
            if (dataBuf.length() > 0) {
                handleStreamEvent(event, dataBuf.toString(), result, emitter);
            }
            log.info("streamOutlineChatStreamed done status={}, outlineId={}", result.status, result.outlineId);
            return result;
        } catch (Exception e) {
            log.warn("streamOutlineChatStreamed failed: {}", e.getMessage());
            if (e instanceof RuntimeException runtimeException) {
                throw runtimeException;
            }
            throw new RuntimeException("调用Python大纲服务失败: " + e.getMessage(), e);
        }
    }

    private void handleStreamEvent(String event, String rawData, OutlineChatResult result, SseEmitter emitter) throws Exception {
        if (rawData == null || rawData.isBlank()) {
            return;
        }
        Map<String, Object> parsed = objectMapper.readValue(rawData, new TypeReference<>() {});
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
        } else if ("reflection".equals(event)) {
            result.reflection = parsed;
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
        sendSseEvent(emitter, event, new StringBuilder(objectMapper.writeValueAsString(parsed)));
    }

    public Map<String, Object> listOutlineChatSessions(String userId, Integer limit) {
        Map<String, Object> query = new LinkedHashMap<>();
        query.put("user_id", userId);
        if (limit != null) query.put("limit", limit);
        return getJson("/api/v1/python/outlines/chat/sessions", query);
    }

    public Map<String, Object> createOutlineChatSession(Map<String, Object> payload) {
        return postJson("/api/v1/python/outlines/chat/sessions", payload);
    }

    public Map<String, Object> getOutlineChatSession(String userId, String sessionId) {
        return getJson("/api/v1/python/outlines/chat/sessions/" + urlEncode(sessionId), Map.of("user_id", userId));
    }

    public Map<String, Object> updateOutlineChatSession(String userId, String sessionId, Map<String, Object> payload) {
        return patchJson("/api/v1/python/outlines/chat/sessions/" + urlEncode(sessionId) + toQueryString(Map.of("user_id", userId)), payload);
    }

    public Map<String, Object> deleteOutlineChatSession(String userId, String sessionId) {
        return deleteJson("/api/v1/python/outlines/chat/sessions/" + urlEncode(sessionId), Map.of("user_id", userId));
    }

    public Map<String, Object> teacherStyleProfile(String userId) {
        return getJson("/api/v1/python/teacher-style/profile", Map.of("user_id", userId));
    }

    public Map<String, Object> recordTeacherFeedback(Map<String, Object> payload) {
        return postJson("/api/v1/python/teacher-style/feedback", payload);
    }

    public Map<String, Object> aiMetrics(Integer limit) {
        return getJson("/api/v1/python/ai/metrics", limit == null ? Map.of() : Map.of("limit", limit));
    }

    public PythonFileResult synthesizeSpeech(Map<String, Object> payload) {
        return postFile("/api/v1/python/audio/tts", payload, "调用Python语音合成服务失败");
    }

    public Map<String, Object> recordClassroomEvent(Map<String, Object> payload) {
        return postJson("/api/v1/python/classroom/events", payload);
    }

    public Map<String, Object> classroomInsights(String userId, String projectId) {
        return getJson("/api/v1/python/classroom/insights/" + urlEncode(projectId), Map.of("user_id", userId));
    }

    public Map<String, Object> generatePresentation(Map<String, Object> payload) {
        log.info("generatePresentation title={}, outlineId={}", payload.get("title"), payload.get("outline_id"));
        return postJson("/api/v1/python/presentations/generate", payload);
    }

    public Map<String, Object> enqueuePresentationJob(Map<String, Object> payload) {
        return postJson("/api/v1/python/generation-jobs/presentations", payload);
    }

    public Map<String, Object> enqueueLessonPlanJob(Map<String, Object> payload) {
        return postJson("/api/v1/python/generation-jobs/lesson-plans", payload);
    }

    public Map<String, Object> getGenerationJob(String jobId, String userId) {
        return getJson("/api/v1/python/generation-jobs/" + urlEncode(jobId), Map.of("user_id", userId));
    }

    public void streamGenerationJobEvents(String jobId, String userId, String after, SseEmitter emitter) {
        String path = "/api/v1/python/generation-jobs/" + urlEncode(jobId) + "/events"
                + toQueryString(Map.of("user_id", userId, "after", after == null || after.isBlank() ? "0-0" : after));
        String event = "message";
        String eventId = null;
        StringBuilder data = new StringBuilder();
        try {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(baseUrl + path))
                    .timeout(Duration.ofSeconds(650))
                    .header("Accept", "text/event-stream")
                    .GET().build();
            HttpResponse<Stream<String>> response = httpClient.send(request, HttpResponse.BodyHandlers.ofLines());
            try (Stream<String> lines = response.body()) {
                for (java.util.Iterator<String> iterator = lines.iterator(); iterator.hasNext(); ) {
                    String line = iterator.next();
                    if (line.isEmpty()) {
                        if (data.length() > 0) {
                            SseEmitter.SseEventBuilder builder = SseEmitter.event().name(event)
                                    .data(data.toString(), org.springframework.http.MediaType.APPLICATION_JSON);
                            if (eventId != null) builder.id(eventId);
                            emitter.send(builder);
                        }
                        event = "message";
                        eventId = null;
                        data.setLength(0);
                    } else if (line.startsWith("id:")) {
                        eventId = line.substring(3).trim();
                    } else if (line.startsWith("event:")) {
                        event = line.substring(6).trim();
                    } else if (line.startsWith("data:")) {
                        if (data.length() > 0) data.append('\n');
                        data.append(line.substring(5).trim());
                    }
                }
            }
            emitter.complete();
        } catch (Exception e) {
            try {
                emitter.send(SseEmitter.event().name("error").data(toJson(Map.of("message", e.getMessage()))));
            } catch (Exception ignored) {
            }
            emitter.complete();
        }
    }

    public Map<String, Object> modifySlide(Map<String, Object> payload) {
        log.info("modifySlide presentationId={}, slideNo={}", payload.get("presentation_id"), payload.get("slide_no"));
        return postJson("/api/v1/python/presentations/slides/modify", payload);
    }

    public Map<String, Object> modifyPresentation(Map<String, Object> payload) {
        log.info("modifyPresentation presentationId={}, title={}", payload.get("presentation_id"), payload.get("title"));
        return postJson("/api/v1/python/presentations/modify", payload);
    }

    public Map<String, Object> validateHtml(Map<String, Object> payload) {
        log.info("validateHtml strict={}", payload.get("strict"));
        return postJson("/api/v1/python/presentations/html/validate", payload);
    }

    public byte[] exportPresentationPptx(Map<String, Object> payload) {
        return postBytes("/api/v1/python/presentations/export/pptx", payload, "调用Python PPTX导出服务失败");
    }

    public PythonFileResult exportPresentationFile(Map<String, Object> payload) {
        return postFile("/api/v1/python/presentations/export/pptx", payload, "调用Python PPTX导出服务失败");
    }

    public Map<String, Object> generateLessonPlan(Map<String, Object> payload) {
        log.info("generateLessonPlan title={}, subject={}", payload.get("title"), payload.get("subject"));
        return postJson("/api/v1/python/lesson-plans/generate", payload);
    }

    public byte[] exportLessonPlanDocx(Map<String, Object> payload) {
        return postBytes("/api/v1/python/lesson-plans/export/docx", payload, "调用Python教案导出服务失败");
    }

    public PythonFileResult exportLessonPlanFile(Map<String, Object> payload) {
        return postFile("/api/v1/python/lesson-plans/export/docx", payload, "调用Python教案导出服务失败");
    }

    public Map<String, Object> generateInteractiveModule(Map<String, Object> payload) {
        log.info("generateInteractiveModule title={}, type={}", payload.get("title"), payload.get("module_type"));
        return postJson("/api/v1/python/interactive-modules/generate", payload);
    }

    public Map<String, Object> syncResourceIndex(Map<String, Object> payload) {
        log.info("syncResourceIndex sourceType={}, resourceId={}", payload.get("source_type"), payload.get("resource_id"));
        return postJson("/api/v1/python/resources/index/sync", payload);
    }

    public Map<String, Object> bootstrapResourceIndex(List<Map<String, Object>> resources, boolean forceReparse) {
        log.info("bootstrapResourceIndex resourceCount={}, forceReparse={}", resources.size(), forceReparse);
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("resources", resources);
        payload.put("force_reparse", forceReparse);
        return postJson("/api/v1/python/resources/index/bootstrap", payload);
    }

    public Map<String, Object> updateResourceIndexMetadata(Map<String, Object> payload) {
        log.info("updateResourceIndexMetadata sourceType={}, resourceId={}, available={}",
                payload.get("source_type"), payload.get("resource_id"), payload.get("available"));
        return patchJson("/api/v1/python/resources/index/metadata", payload);
    }

    public Map<String, Object> resourceIndexOverview() {
        return getJson("/api/v1/python/resources/index/overview", Map.of());
    }

    public Map<String, Object> listResourceIndexResources(String sourceType, Boolean available, Integer limit, Integer offset,
                                                          String parseStatus, String keyword) {
        Map<String, Object> query = new LinkedHashMap<>();
        if (sourceType != null && !sourceType.isBlank()) query.put("source_type", sourceType);
        if (available != null) query.put("available", available);
        if (limit != null) query.put("limit", limit);
        if (offset != null) query.put("offset", offset);
        if (parseStatus != null && !parseStatus.isBlank()) query.put("parse_status", parseStatus);
        if (keyword != null && !keyword.isBlank()) query.put("keyword", keyword);
        return getJson("/api/v1/python/resources/index/resources", query);
    }

    public Map<String, Object> getResourceIndexResource(String sourceType, String resourceId, Integer chunkLimit) {
        Map<String, Object> query = new LinkedHashMap<>();
        if (chunkLimit != null) query.put("chunk_limit", chunkLimit);
        String path = "/api/v1/python/resources/index/resources/" + urlEncode(sourceType) + "/" + urlEncode(resourceId);
        return getJson(path, query);
    }

    public Map<String, Object> listResourceIndexLogs(Integer limit, Integer offset) {
        Map<String, Object> query = new LinkedHashMap<>();
        if (limit != null) query.put("limit", limit);
        if (offset != null) query.put("offset", offset);
        return getJson("/api/v1/python/resources/index/logs", query);
    }

    public Map<String, Object> searchResourceIndex(Map<String, Object> payload) {
        return postJson("/api/v1/python/resources/index/search", payload);
    }

    public Map<String, Object> deleteResourceIndex(String sourceType, Object resourceId) {
        try {
            String path = "/api/v1/python/resources/index/" + urlEncode(sourceType) + "/" + urlEncode(String.valueOf(resourceId));
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(baseUrl + path))
                    .timeout(Duration.ofSeconds(requestTimeoutSeconds))
                    .DELETE()
                    .build();
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            log.info("deleteResourceIndex sourceType={}, resourceId={}, statusCode={}", sourceType, resourceId, response.statusCode());
            return parseJsonResponse(response);
        } catch (Exception e) {
            throw new RuntimeException("删除Python资源索引失败: " + e.getMessage(), e);
        }
    }

    private Map<String, Object> getJson(String path, Map<String, Object> query) {
        try {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(baseUrl + path + toQueryString(query)))
                    .timeout(Duration.ofSeconds(requestTimeoutSeconds))
                    .GET()
                    .build();
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            log.info("getJson path={}, statusCode={}", path, response.statusCode());
            return parseJsonResponse(response);
        } catch (Exception e) {
            throw new RuntimeException("调用Python服务失败: " + e.getMessage(), e);
        }
    }

    private Map<String, Object> postJson(String path, Map<String, Object> payload) {
        return sendJson("POST", path, payload);
    }

    private Map<String, Object> patchJson(String path, Map<String, Object> payload) {
        return sendJson("PATCH", path, payload);
    }

    private Map<String, Object> deleteJson(String path, Map<String, Object> query) {
        try {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(baseUrl + path + toQueryString(query)))
                    .timeout(Duration.ofSeconds(requestTimeoutSeconds))
                    .DELETE()
                    .build();
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            log.info("deleteJson path={}, statusCode={}", path, response.statusCode());
            return parseJsonResponse(response);
        } catch (Exception e) {
            throw new RuntimeException("调用Python服务失败: " + e.getMessage(), e);
        }
    }

    private Map<String, Object> sendJson(String method, String path, Map<String, Object> payload) {
        try {
            HttpResponse<String> response = sendJsonResponse(method, path, payload);
            log.info("sendJson method={}, path={}, statusCode={}", method, path, response.statusCode());
            return parseJsonResponse(response);
        } catch (Exception e) {
            throw new RuntimeException("调用Python服务失败: " + e.getMessage(), e);
        }
    }

    private HttpResponse<String> postJsonResponse(String path, Map<String, Object> payload) throws Exception {
        return sendJsonResponse("POST", path, payload);
    }

    private HttpResponse<Stream<String>> postJsonLinesResponse(String path, Map<String, Object> payload) throws Exception {
        String body = objectMapper.writeValueAsString(payload == null ? Map.of() : payload);
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + path))
                .timeout(Duration.ofSeconds(requestTimeoutSeconds))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(body))
                .build();
        HttpResponse<Stream<String>> response = httpClient.send(request, HttpResponse.BodyHandlers.ofLines());
        if (response.statusCode() < 200 || response.statusCode() >= 300) {
            response.body().close();
            throw new RuntimeException("Python服务调用失败，HTTP " + response.statusCode());
        }
        return response;
    }

    private HttpResponse<String> sendJsonResponse(String method, String path, Map<String, Object> payload) throws Exception {
        String body = objectMapper.writeValueAsString(payload == null ? Map.of() : payload);
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + path))
                .timeout(Duration.ofSeconds(requestTimeoutSeconds))
                .header("Content-Type", "application/json")
                .method(method, HttpRequest.BodyPublishers.ofString(body))
                .build();
        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        if (response.statusCode() < 200 || response.statusCode() >= 300) {
            throw new RuntimeException("Python服务调用失败，HTTP " + response.statusCode());
        }
        return response;
    }

    private byte[] postBytes(String path, Map<String, Object> payload, String errorPrefix) {
        return postFile(path, payload, errorPrefix).bytes;
    }

    private PythonFileResult postFile(String path, Map<String, Object> payload, String errorPrefix) {
        try {
            String body = objectMapper.writeValueAsString(payload == null ? Map.of() : payload);
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(baseUrl + path))
                    .timeout(Duration.ofSeconds(requestTimeoutSeconds))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(body))
                    .build();
            HttpResponse<byte[]> response = httpClient.send(request, HttpResponse.BodyHandlers.ofByteArray());
            log.info("postBytes path={}, statusCode={}", path, response.statusCode());
            if (response.statusCode() < 200 || response.statusCode() >= 300) {
                throw new RuntimeException("Python服务调用失败，HTTP " + response.statusCode());
            }
            String contentType = response.headers().firstValue("content-type")
                    .orElse("application/octet-stream")
                    .split(";")[0]
                    .trim();
            String filename = response.headers().firstValue("content-disposition")
                    .map(this::filenameFromContentDisposition)
                    .filter(value -> value != null && !value.isBlank())
                    .orElse(null);
            return new PythonFileResult(response.body(), contentType, filename);
        } catch (Exception e) {
            throw new RuntimeException(errorPrefix + ": " + e.getMessage(), e);
        }
    }

    private Map<String, Object> uploadFile(String path, byte[] fileBytes, String filename, String contentType, Map<String, String> fields) {
        try {
            String boundary = "----A12Boundary" + UUID.randomUUID();
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(baseUrl + path))
                    .timeout(Duration.ofSeconds(requestTimeoutSeconds))
                    .header("Content-Type", "multipart/form-data; boundary=" + boundary)
                    .POST(ofMultipartFileData(boundary, fileBytes, filename, contentType, fields))
                    .build();
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            log.info("uploadFile path={}, filename={}, statusCode={}", path, filename, response.statusCode());
            return parseJsonResponse(response);
        } catch (Exception e) {
            throw new RuntimeException("调用Python文件上传服务失败: " + e.getMessage(), e);
        }
    }

    private HttpRequest.BodyPublisher ofMultipartFileData(String boundary, byte[] fileBytes, String filename,
                                                          String contentType, Map<String, String> fields) {
        List<byte[]> parts = new ArrayList<>();
        String fileHeader = "--" + boundary + "\r\n"
                + "Content-Disposition: form-data; name=\"file\"; filename=\"" + (filename == null ? "upload.bin" : filename) + "\"\r\n"
                + "Content-Type: " + (contentType == null || contentType.isBlank() ? "application/octet-stream" : contentType) + "\r\n\r\n";
        parts.add(fileHeader.getBytes(StandardCharsets.UTF_8));
        parts.add(fileBytes);
        parts.add("\r\n".getBytes(StandardCharsets.UTF_8));
        for (Map.Entry<String, String> entry : fields.entrySet()) {
            if (entry.getValue() == null) continue;
            String fieldPart = "--" + boundary + "\r\n"
                    + "Content-Disposition: form-data; name=\"" + entry.getKey() + "\"\r\n\r\n"
                    + entry.getValue() + "\r\n";
            parts.add(fieldPart.getBytes(StandardCharsets.UTF_8));
        }
        parts.add(("--" + boundary + "--\r\n").getBytes(StandardCharsets.UTF_8));
        return HttpRequest.BodyPublishers.ofByteArrays(parts);
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
            } else if ("reflection".equals(event)) {
                result.reflection = parsed;
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

    private String toQueryString(Map<String, Object> query) {
        if (query == null || query.isEmpty()) return "";
        StringBuilder builder = new StringBuilder("?");
        boolean first = true;
        for (Map.Entry<String, Object> entry : query.entrySet()) {
            if (entry.getValue() == null) continue;
            if (!first) builder.append("&");
            first = false;
            builder.append(urlEncode(entry.getKey())).append("=").append(urlEncode(String.valueOf(entry.getValue())));
        }
        return first ? "" : builder.toString();
    }

    private String urlEncode(String value) {
        return URLEncoder.encode(value, StandardCharsets.UTF_8);
    }

    private String stringValue(Object value) {
        return value == null ? null : String.valueOf(value);
    }

    private String filenameFromContentDisposition(String contentDisposition) {
        if (contentDisposition == null || contentDisposition.isBlank()) {
            return null;
        }
        for (String part : contentDisposition.split(";")) {
            String clean = part.trim();
            if (clean.startsWith("filename*=")) {
                String value = clean.substring("filename*=".length()).trim();
                int marker = value.indexOf("''");
                if (marker >= 0) {
                    value = value.substring(marker + 2);
                }
                return java.net.URLDecoder.decode(stripQuotes(value), StandardCharsets.UTF_8);
            }
            if (clean.startsWith("filename=")) {
                return stripQuotes(clean.substring("filename=".length()).trim());
            }
        }
        return null;
    }

    private String stripQuotes(String value) {
        if (value == null) {
            return null;
        }
        if (value.length() >= 2 && value.startsWith("\"") && value.endsWith("\"")) {
            return value.substring(1, value.length() - 1);
        }
        return value;
    }

    private void sendSseEvent(SseEmitter emitter, String event, StringBuilder data) throws IOException {
        if (data == null || data.length() == 0) {
            return;
        }
        emitter.send(SseEmitter.event()
                .name(event == null || event.isBlank() ? "message" : event)
                .data(data.toString(), org.springframework.http.MediaType.APPLICATION_JSON));
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
        public Object reflection;
        public Map<String, Object> finalData = new LinkedHashMap<>();
        public List<Object> outlineDeltas = new ArrayList<>();
    }

    public static class PythonFileResult {
        public final byte[] bytes;
        public final String contentType;
        public final String filename;

        public PythonFileResult(byte[] bytes, String contentType, String filename) {
            this.bytes = bytes;
            this.contentType = contentType;
            this.filename = filename;
        }
    }
}
