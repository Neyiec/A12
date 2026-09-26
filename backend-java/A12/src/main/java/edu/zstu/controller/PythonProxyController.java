package edu.zstu.controller;

import edu.zstu.service.PythonPptClient;
import edu.zstu.service.KafkaEventPublisher;
import edu.zstu.utils.CurrentHolder;
import edu.zstu.utils.OssUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

@RestController
// 新前端统一使用 Java AI 网关；旧路径保留兼容已有调用。
@RequestMapping({"/api/v1/ai/engine", "/api/v1/python"})
public class PythonProxyController {
    private final PythonPptClient pythonPptClient;
    private final OssUtil ossUtil;
    private final KafkaEventPublisher kafkaEventPublisher;

    @Autowired
    public PythonProxyController(PythonPptClient pythonPptClient, OssUtil ossUtil,
                                 KafkaEventPublisher kafkaEventPublisher) {
        this.pythonPptClient = pythonPptClient;
        this.ossUtil = ossUtil;
        this.kafkaEventPublisher = kafkaEventPublisher;
    }

    /** 保留独立 MockMvc/旧调用构造方式；生产环境由上方构造器注入 Kafka publisher。 */
    public PythonProxyController(PythonPptClient pythonPptClient, OssUtil ossUtil) {
        this(pythonPptClient, ossUtil, null);
    }

    @GetMapping("/health")
    public Map<String, Object> health() {
        return callJson(pythonPptClient::health);
    }

    @PostMapping(value = "/audio/asr", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Map<String, Object> transcribeAudio(@RequestParam("file") MultipartFile file,
                                               @RequestParam(required = false) String language) {
        return callJson(() -> pythonPptClient.transcribeAudio(bytes(file), file.getOriginalFilename(), file.getContentType(), language));
    }

    @GetMapping("/templates")
    public Map<String, Object> templates() {
        return callJson(pythonPptClient::templates);
    }

    @PostMapping(value = "/resources/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Map<String, Object> uploadResource(@RequestParam("file") MultipartFile file) {
        return callJson(() -> pythonPptClient.uploadResource(bytes(file), file.getOriginalFilename(), file.getContentType()));
    }

    @PostMapping("/resources/index/sync")
    public Map<String, Object> syncResourceIndex(@RequestBody Map<String, Object> payload) {
        signPayloadFileUrl(payload);
        if (kafkaEventPublisher != null) {
            KafkaEventPublisher.PublishResult published = kafkaEventPublisher.publishResourceIndex(payload);
            if (published.accepted()) return acceptedEvent(published.eventId(), "indexing");
        }
        return callJson(() -> pythonPptClient.syncResourceIndex(payload));
    }

    @PostMapping("/resources/index/bootstrap")
    @SuppressWarnings("unchecked")
    public Map<String, Object> bootstrapResourceIndex(@RequestBody Map<String, Object> payload) {
        java.util.List<Map<String, Object>> resources =
                new java.util.ArrayList<>((java.util.List<Map<String, Object>>) payload.getOrDefault("resources", java.util.List.of()));
        // 前端直发的 bootstrap 载荷里是裸 OSS 地址，逐条补签临时下载 URL
        resources.forEach(this::signPayloadFileUrl);
        return callJson(() -> pythonPptClient.bootstrapResourceIndex(
                resources,
                Boolean.TRUE.equals(payload.get("force_reparse"))));
    }

    @PatchMapping("/resources/index/metadata")
    public Map<String, Object> updateResourceIndexMetadata(@RequestBody Map<String, Object> payload) {
        return callJson(() -> pythonPptClient.updateResourceIndexMetadata(payload));
    }

    @GetMapping("/resources/index/overview")
    public Map<String, Object> resourceIndexOverview() {
        return callJson(pythonPptClient::resourceIndexOverview);
    }

    @GetMapping("/resources/index/resources")
    public Map<String, Object> listResourceIndexResources(@RequestParam(required = false) String source_type,
                                                          @RequestParam(required = false) Boolean available,
                                                          @RequestParam(required = false) Integer limit,
                                                          @RequestParam(required = false) Integer offset,
                                                          @RequestParam(required = false) String parse_status,
                                                          @RequestParam(required = false) String keyword) {
        return callJson(() -> pythonPptClient.listResourceIndexResources(source_type, available, limit, offset, parse_status, keyword));
    }

    @GetMapping("/resources/index/resources/{sourceType}/{resourceId}")
    public Map<String, Object> getResourceIndexResource(@PathVariable String sourceType,
                                                        @PathVariable String resourceId,
                                                        @RequestParam(required = false) Integer chunk_limit) {
        return callJson(() -> pythonPptClient.getResourceIndexResource(sourceType, resourceId, chunk_limit));
    }

    @GetMapping("/resources/index/logs")
    public Map<String, Object> listResourceIndexLogs(@RequestParam(required = false) Integer limit,
                                                     @RequestParam(required = false) Integer offset) {
        return callJson(() -> pythonPptClient.listResourceIndexLogs(limit, offset));
    }

    @PostMapping("/resources/index/search")
    public Map<String, Object> searchResourceIndex(@RequestBody Map<String, Object> payload) {
        return callJson(() -> pythonPptClient.searchResourceIndex(payload));
    }

    @DeleteMapping("/resources/index/{sourceType}/{resourceId}")
    public Map<String, Object> deleteResourceIndex(@PathVariable String sourceType,
                                                   @PathVariable String resourceId) {
        return callJson(() -> pythonPptClient.deleteResourceIndex(sourceType, resourceId));
    }

    @PostMapping("/outlines/generate")
    public Map<String, Object> generateOutline(@RequestBody Map<String, Object> payload) {
        bindCurrentUser(payload);
        return callJson(() -> pythonPptClient.generateOutline(payload));
    }

    @PostMapping("/outlines/update")
    public Map<String, Object> updateOutline(@RequestBody Map<String, Object> payload) {
        return callJson(() -> pythonPptClient.updateOutline(payload));
    }

    @PostMapping("/intent/recognize")
    public Map<String, Object> recognizeIntent(@RequestBody Map<String, Object> payload) {
        bindCurrentUser(payload);
        return callJson(() -> pythonPptClient.recognizeIntent(payload));
    }

    @PostMapping(value = "/outlines/chat/stream", produces = "text/event-stream;charset=UTF-8")
    public SseEmitter streamOutlineChat(@RequestBody Map<String, Object> payload) {
        bindCurrentUser(payload);
        SseEmitter emitter = newGatewayEmitter();
        CompletableFuture.runAsync(() -> pythonPptClient.streamOutlineChatToEmitter(payload, emitter));
        return emitter;
    }

    /** 通用聊天、动作分类和大纲修复的网关入口；上游异常以 error 事件返回。 */
    @PostMapping(value = "/workspace/chat/stream", produces = "text/event-stream;charset=UTF-8")
    public SseEmitter streamWorkspaceChat(@RequestBody Map<String, Object> payload) {
        bindCurrentUser(payload);
        SseEmitter emitter = newGatewayEmitter();
        CompletableFuture.runAsync(() -> pythonPptClient.streamWorkspaceChatToEmitter(payload, emitter));
        return emitter;
    }

    @GetMapping("/outlines/chat/sessions")
    public Map<String, Object> listOutlineChatSessions(@RequestParam(value = "user_id", required = false) String ignoredUserId,
                                                       @RequestParam(required = false) Integer limit) {
        String userId = currentUserId();
        return callJson(() -> pythonPptClient.listOutlineChatSessions(userId, limit));
    }

    @PostMapping("/outlines/chat/sessions")
    public Map<String, Object> createOutlineChatSession(@RequestBody Map<String, Object> payload) {
        bindCurrentUser(payload);
        return callJson(() -> pythonPptClient.createOutlineChatSession(payload));
    }

    @GetMapping("/outlines/chat/sessions/{sessionId}")
    public Map<String, Object> getOutlineChatSession(@PathVariable String sessionId,
                                                     @RequestParam(value = "user_id", required = false) String ignoredUserId) {
        String userId = currentUserId();
        return callJson(() -> pythonPptClient.getOutlineChatSession(userId, sessionId));
    }

    @PatchMapping("/outlines/chat/sessions/{sessionId}")
    public Map<String, Object> updateOutlineChatSession(@PathVariable String sessionId,
                                                        @RequestParam(value = "user_id", required = false) String ignoredUserId,
                                                        @RequestBody Map<String, Object> payload) {
        String userId = currentUserId();
        return callJson(() -> pythonPptClient.updateOutlineChatSession(userId, sessionId, payload));
    }

    @DeleteMapping("/outlines/chat/sessions/{sessionId}")
    public Map<String, Object> deleteOutlineChatSession(@PathVariable String sessionId,
                                                        @RequestParam(value = "user_id", required = false) String ignoredUserId) {
        String userId = currentUserId();
        return callJson(() -> pythonPptClient.deleteOutlineChatSession(userId, sessionId));
    }

    @GetMapping("/teacher-style/profile")
    public Map<String, Object> teacherStyleProfile(@RequestParam(value = "user_id", required = false) String ignoredUserId) {
        String userId = currentUserId();
        return callJson(() -> pythonPptClient.teacherStyleProfile(userId));
    }

    @PostMapping("/presentations/generate")
    public Map<String, Object> generatePresentation(@RequestBody Map<String, Object> payload) {
        bindCurrentUser(payload);
        return callJson(() -> pythonPptClient.generatePresentation(payload));
    }

    @PostMapping("/generation-jobs/presentations")
    public Map<String, Object> enqueuePresentationJob(@RequestBody Map<String, Object> payload) {
        bindCurrentUser(payload);
        return callJson(() -> pythonPptClient.enqueuePresentationJob(payload));
    }

    @PostMapping("/generation-jobs/lesson-plans")
    public Map<String, Object> enqueueLessonPlanJob(@RequestBody Map<String, Object> payload) {
        bindCurrentUser(payload);
        return callJson(() -> pythonPptClient.enqueueLessonPlanJob(payload));
    }

    @GetMapping("/generation-jobs/{jobId}")
    public Map<String, Object> getGenerationJob(@PathVariable String jobId) {
        return callJson(() -> pythonPptClient.getGenerationJob(jobId, currentUserId()));
    }

    @GetMapping(value = "/generation-jobs/{jobId}/events", produces = "text/event-stream;charset=UTF-8")
    public SseEmitter streamGenerationJobEvents(
            @PathVariable String jobId,
            @RequestHeader(value = "Last-Event-ID", required = false) String lastEventId,
            @RequestParam(value = "after", required = false) String after) {
        String offset = lastEventId == null || lastEventId.isBlank() ? after : lastEventId;
        String userId = currentUserId();
        SseEmitter emitter = newGatewayEmitter();
        CompletableFuture.runAsync(() -> pythonPptClient.streamGenerationJobEvents(
                jobId, userId, offset, emitter));
        return emitter;
    }

    @PostMapping("/teacher-style/feedback")
    public Map<String, Object> recordTeacherFeedback(@RequestBody Map<String, Object> payload) {
        bindCurrentUser(payload);
        if (kafkaEventPublisher != null) {
            KafkaEventPublisher.PublishResult published = kafkaEventPublisher.publishTeacherFeedback(payload);
            if (published.accepted()) return acceptedEvent(published.eventId(), "accepted");
        }
        return callJson(() -> pythonPptClient.recordTeacherFeedback(payload));
    }

    @GetMapping("/ai/metrics")
    public Map<String, Object> aiMetrics(@RequestParam(required = false) Integer limit) {
        return callJson(() -> pythonPptClient.aiMetrics(limit));
    }

    @PostMapping("/audio/tts")
    public ResponseEntity<byte[]> synthesizeSpeech(@RequestBody Map<String, Object> payload) {
        PythonPptClient.PythonFileResult file = pythonPptClient.synthesizeSpeech(payload);
        return fileResponse(file.bytes, "a12-speech.mp3", file.contentType);
    }

    @PostMapping("/classroom/events")
    public Map<String, Object> recordClassroomEvent(@RequestBody Map<String, Object> payload) {
        bindCurrentUser(payload);
        if (kafkaEventPublisher != null) {
            KafkaEventPublisher.PublishResult published = kafkaEventPublisher.publishClassroomEvent(payload);
            if (published.accepted()) return acceptedEvent(published.eventId(), "accepted");
        }
        return callJson(() -> pythonPptClient.recordClassroomEvent(payload));
    }

    @GetMapping("/classroom/insights/{projectId}")
    public Map<String, Object> classroomInsights(@PathVariable String projectId) {
        return callJson(() -> pythonPptClient.classroomInsights(currentUserId(), projectId));
    }

    @PostMapping(value = "/presentations/generate/stream", produces = "text/event-stream;charset=UTF-8")
    public SseEmitter streamPresentation(@RequestBody Map<String, Object> payload) {
        bindCurrentUser(payload);
        SseEmitter emitter = newGatewayEmitter();
        CompletableFuture.runAsync(() -> pythonPptClient.streamPresentationToEmitter(payload, emitter));
        return emitter;
    }

    @PostMapping("/presentations/slides/modify")
    public Map<String, Object> modifySlide(@RequestBody Map<String, Object> payload) {
        return callJson(() -> pythonPptClient.modifySlide(payload));
    }

    @PostMapping("/presentations/modify")
    public Map<String, Object> modifyPresentation(@RequestBody Map<String, Object> payload) {
        return callJson(() -> pythonPptClient.modifyPresentation(payload));
    }

    @PostMapping("/presentations/html/validate")
    public Map<String, Object> validateHtml(@RequestBody Map<String, Object> payload) {
        return callJson(() -> pythonPptClient.validateHtml(payload));
    }

    @PostMapping("/presentations/export/pptx")
    public ResponseEntity<byte[]> exportPresentationPptx(@RequestBody Map<String, Object> payload) {
        PythonPptClient.PythonFileResult file = pythonPptClient.exportPresentationFile(payload);
        String fallback = "application/zip".equals(file.contentType) ? "A12 PPT.zip" : "A12 PPT.pptx";
        return fileResponse(file.bytes, firstNotBlank(file.filename, filename(payload, fallback)), file.contentType);
    }

    @PostMapping("/lesson-plans/generate")
    public Map<String, Object> generateLessonPlan(@RequestBody Map<String, Object> payload) {
        bindCurrentUser(payload);
        return callJson(() -> pythonPptClient.generateLessonPlan(payload));
    }

    @PostMapping("/lesson-plans/export/docx")
    public ResponseEntity<byte[]> exportLessonPlanDocx(@RequestBody Map<String, Object> payload) {
        byte[] bytes = pythonPptClient.exportLessonPlanDocx(payload);
        return fileResponse(bytes, filename(payload, "A12 教案.docx"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document");
    }

    @PostMapping("/interactive-modules/generate")
    public Map<String, Object> generateInteractiveModule(@RequestBody Map<String, Object> payload) {
        return callJson(() -> pythonPptClient.generateInteractiveModule(payload));
    }

    private SseEmitter newGatewayEmitter() {
        return new SseEmitter(620_000L) {
            @Override
            protected void extendResponse(org.springframework.http.server.ServerHttpResponse response) {
                super.extendResponse(response);
                response.getHeaders().setContentType(new MediaType("text", "event-stream", StandardCharsets.UTF_8));
                response.getHeaders().setCacheControl("no-cache");
                response.getHeaders().set("X-Accel-Buffering", "no");
            }
        };
    }

    private String currentUserId() {
        Integer userId = CurrentHolder.getCurrentId();
        if (userId == null) {
            throw new org.springframework.web.server.ResponseStatusException(org.springframework.http.HttpStatus.UNAUTHORIZED, "请先登录");
        }
        return String.valueOf(userId);
    }

    private void bindCurrentUser(Map<String, Object> payload) {
        // 在请求线程读取身份；异步 SSE 线程没有 CurrentHolder 的 ThreadLocal。
        payload.put("user_id", currentUserId());
    }

    private Map<String, Object> acceptedEvent(String eventId, String status) {
        return Map.of(
                "code", 200,
                "message", "事件已进入 Kafka",
                "data", Map.of("accepted", true, "event_id", eventId, "status", status)
        );
    }

    private Map<String, Object> callJson(JsonCall call) {
        try {
            return call.execute();
        } catch (RuntimeException e) {
            Map<String, Object> error = new java.util.LinkedHashMap<>();
            error.put("code", 400);
            error.put("message", e.getMessage());
            error.put("data", null);
            return error;
        }
    }

    /**
     * 为索引同步载荷补签临时下载 URL（60 分钟有效）
     * 归属校验：仅允许签名本人 uploads/{userId}/ 前缀的素材与 public/ 前缀的公共资源，
     * 防止接口被当作任意对象的签名预言机；其余地址原样透传
     */
    private void signPayloadFileUrl(Map<String, Object> payload) {
        if (payload == null || !(payload.get("file_url") instanceof String fileUrl) || fileUrl.isBlank()) {
            return;
        }
        String objectKey = ossUtil.tryExtractObjectKey(fileUrl);
        if (objectKey == null) {
            return;
        }
        Integer userId = CurrentHolder.getCurrentId();
        boolean ownMaterial = userId != null && objectKey.startsWith("uploads/" + userId + "/");
        boolean publicResource = objectKey.startsWith("public/");
        if (ownMaterial || publicResource) {
            payload.put("file_url", ossUtil.resolveDownloadUrl(fileUrl, 60));
        }
    }

    private byte[] bytes(MultipartFile file) {
        try {
            return file.getBytes();
        } catch (Exception e) {
            throw new RuntimeException("读取上传文件失败: " + e.getMessage(), e);
        }
    }

    private String filename(Map<String, Object> payload, String fallback) {
        Object filename = payload == null ? null : payload.get("filename");
        return filename == null || String.valueOf(filename).isBlank() ? fallback : String.valueOf(filename);
    }

    private String firstNotBlank(String first, String second) {
        return first == null || first.isBlank() ? second : first;
    }

    private ResponseEntity<byte[]> fileResponse(byte[] bytes, String filename, String contentType) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.parseMediaType(contentType));
        headers.setContentDisposition(ContentDisposition.attachment()
                .filename(filename, StandardCharsets.UTF_8)
                .build());
        headers.setContentLength(bytes.length);
        return ResponseEntity.ok().headers(headers).body(bytes);
    }

    @FunctionalInterface
    private interface JsonCall {
        Map<String, Object> execute();
    }
}
