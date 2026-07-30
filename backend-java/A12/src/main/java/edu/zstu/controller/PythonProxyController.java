package edu.zstu.controller;

import edu.zstu.service.PythonPptClient;
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
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

@RestController
@RequestMapping("/api/v1/python")
public class PythonProxyController {
    private final PythonPptClient pythonPptClient;

    public PythonProxyController(PythonPptClient pythonPptClient) {
        this.pythonPptClient = pythonPptClient;
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
        return callJson(() -> pythonPptClient.syncResourceIndex(payload));
    }

    @PostMapping("/resources/index/bootstrap")
    @SuppressWarnings("unchecked")
    public Map<String, Object> bootstrapResourceIndex(@RequestBody Map<String, Object> payload) {
        return callJson(() -> pythonPptClient.bootstrapResourceIndex(
                (java.util.List<Map<String, Object>>) payload.getOrDefault("resources", java.util.List.of()),
                Boolean.TRUE.equals(payload.get("force_reparse"))));
    }

    @PatchMapping("/resources/index/metadata")
    public Map<String, Object> updateResourceIndexMetadata(@RequestBody Map<String, Object> payload) {
        return callJson(() -> pythonPptClient.updateResourceIndexMetadata(payload));
    }

    @DeleteMapping("/resources/index/{sourceType}/{resourceId}")
    public Map<String, Object> deleteResourceIndex(@PathVariable String sourceType,
                                                   @PathVariable String resourceId) {
        return callJson(() -> pythonPptClient.deleteResourceIndex(sourceType, resourceId));
    }

    @PostMapping("/outlines/generate")
    public Map<String, Object> generateOutline(@RequestBody Map<String, Object> payload) {
        return callJson(() -> pythonPptClient.generateOutline(payload));
    }

    @PostMapping("/outlines/update")
    public Map<String, Object> updateOutline(@RequestBody Map<String, Object> payload) {
        return callJson(() -> pythonPptClient.updateOutline(payload));
    }

    @PostMapping(value = "/outlines/chat/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter streamOutlineChat(@RequestBody Map<String, Object> payload) {
        SseEmitter emitter = new SseEmitter(0L);
        CompletableFuture.runAsync(() -> pythonPptClient.streamOutlineChatToEmitter(payload, emitter));
        return emitter;
    }

    @GetMapping("/outlines/chat/sessions")
    public Map<String, Object> listOutlineChatSessions(@RequestParam("user_id") String userId,
                                                       @RequestParam(required = false) Integer limit) {
        return callJson(() -> pythonPptClient.listOutlineChatSessions(userId, limit));
    }

    @GetMapping("/teacher-style/profile")
    public Map<String, Object> teacherStyleProfile(@RequestParam("user_id") String userId) {
        return callJson(() -> pythonPptClient.teacherStyleProfile(userId));
    }

    @PostMapping("/presentations/generate")
    public Map<String, Object> generatePresentation(@RequestBody Map<String, Object> payload) {
        return callJson(() -> pythonPptClient.generatePresentation(payload));
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
        byte[] bytes = pythonPptClient.exportPresentationPptx(payload);
        return fileResponse(bytes, filename(payload, "A12 PPT.pptx"), "application/vnd.openxmlformats-officedocument.presentationml.presentation");
    }

    @PostMapping("/lesson-plans/generate")
    public Map<String, Object> generateLessonPlan(@RequestBody Map<String, Object> payload) {
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
