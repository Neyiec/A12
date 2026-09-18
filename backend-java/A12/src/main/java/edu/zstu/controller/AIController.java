package edu.zstu.controller;

import edu.zstu.dto.ConversationDTO;
import edu.zstu.dto.IntentRecognitionDTO;
import edu.zstu.dto.PlanConfirmationDTO;
import edu.zstu.dto.TaskCreateDTO;
import edu.zstu.service.AIService;
import edu.zstu.service.PythonPptClient;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.zstu.utils.Result;
import edu.zstu.vo.ConversationVO;
import edu.zstu.vo.TaskVO;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * AI 教学引擎 Controller
 * API-10~16：备课会话、消息、计划、执行
 *
 * <p>负责AI备课会话的创建、消息交互、教学大纲确认、任务执行以及实时事件订阅。</p>
 */
@RestController
@RequestMapping("/api/v1/ai")
public class AIController {
    @Autowired
    private AIService aiService;
    @Autowired
    private PythonPptClient pythonPptClient;
    @Autowired
    private ObjectMapper objectMapper;

    /**
     * API-10 创建备课会话
     *
     * <p>创建备课会话并提交文字、语音、参考资料、Skill和课程信息。</p>
     *
     * @param dto 会话创建参数（title、subject、grade 必填）
     * @return 新创建的AI教学任务信息 {@link TaskVO}
     */
    @PostMapping("/sessions")
    public Result<TaskVO> createSession(@RequestBody TaskCreateDTO dto) {
        try {
            return Result.success(aiService.createSession(dto));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @GetMapping("/sessions")
    public Result<List<ConversationVO>> listSessions() {
        try {
            return Result.success(aiService.listSessions());
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @GetMapping("/sessions/{id}")
    public Result<ConversationVO> getSession(@PathVariable String id) {
        try {
            return Result.success(aiService.getSession(id));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PatchMapping("/sessions/{id}")
    public Result<ConversationVO> updateSession(@PathVariable String id,
                                                @RequestBody ConversationDTO dto) {
        try {
            return Result.success(aiService.updateSession(id, dto));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @DeleteMapping("/sessions/{id}")
    public Result<Void> deleteSession(@PathVariable String id) {
        try {
            aiService.deleteSession(id);
            return Result.success();
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-11 发送会话消息
     *
     * <p>在已有备课会话中补充需求、回答澄清问题或提交反馈。</p>
     *
     * @param id  会话ID（路径参数）
     * @param dto 消息请求参数 {@link ConversationDTO}（messages 必填）
     * @return 更新后的会话信息 {@link ConversationVO}
     */
    @PostMapping("/sessions/{id}/messages")
    public Result<ConversationVO> sendMessage(@PathVariable String id,
                                              @RequestBody ConversationDTO dto) {
        try {
            return Result.success(aiService.sendMessage(id, dto));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-13S 流式发送会话消息（SSE）
     *
     * <p>与 sendMessage 等价但以 text/event-stream 返回：边生成边回传
     * session/outline_delta/question/final/error 等事件，流结束前后端会一次性落库。</p>
     *
     * @param id  会话ID（路径参数）
     * @param dto 消息请求参数 {@link ConversationDTO}
     * @return SSE 事件流
     */
    @PostMapping(value = "/sessions/{id}/messages/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter sendMessageStream(@PathVariable String id, @RequestBody ConversationDTO dto) {
        return aiService.sendMessageStream(id, dto);
    }

    @PostMapping(value = "/sessions/{id}/audio-messages", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Result<ConversationVO> sendAudioMessage(@PathVariable String id,
                                                   @RequestParam("file") MultipartFile file,
                                                   @RequestParam(required = false) String language,
                                                   @RequestParam(required = false) String message,
                                                   @RequestParam(required = false) String resource_ids,
                                                   @RequestParam(required = false) Boolean enable_rag,
                                                   @RequestParam(required = false) Boolean enable_web,
                                                   @RequestParam(required = false) Integer slide_count,
                                                   @RequestParam(required = false) String known_context,
                                                   @RequestParam(required = false) String context_summary) {
        try {
            ConversationDTO dto = new ConversationDTO();
            dto.setMessage(message);
            dto.setResource_ids(resource_ids);
            dto.setEnable_rag(enable_rag);
            dto.setEnable_web(enable_web);
            dto.setSlide_count(slide_count);
            dto.setKnown_context(known_context);
            dto.setContext_summary(context_summary);
            return Result.success(aiService.sendAudioMessage(id, file, language, dto));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PostMapping("/intent/recognize")
    public Result<?> recognizeIntent(@RequestBody IntentRecognitionDTO dto) {
        try {
            return Result.success(pythonData(pythonPptClient.recognizeIntent(intentPayload(dto, "text"))));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PostMapping(value = "/intent/recognize-audio", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Result<?> recognizeAudioIntent(@RequestParam("file") MultipartFile file,
                                          @RequestParam(required = false) String language,
                                          @RequestParam(required = false) String user_id,
                                          @RequestParam(required = false) String session_id,
                                          @RequestParam(required = false) String title,
                                          @RequestParam(required = false) String message,
                                          @RequestParam(required = false) String history,
                                          @RequestParam(required = false) String known_context,
                                          @RequestParam(required = false) String resource_ids,
                                          @RequestParam(required = false) Boolean enable_rag,
                                          @RequestParam(required = false) Boolean enable_web,
                                          @RequestParam(required = false) Integer slide_count) {
        try {
            Map<String, Object> asr = pythonPptClient.transcribeAudio(file.getBytes(), file.getOriginalFilename(), file.getContentType(), language);
            String transcript = extractAsrText(asr);
            if (transcript.isBlank()) {
                return Result.error(400, "语音转写未返回有效文本");
            }
            IntentRecognitionDTO dto = new IntentRecognitionDTO();
            dto.setUser_id(user_id);
            dto.setSession_id(session_id);
            dto.setTitle(title);
            dto.setMessage(mergeMessage(message, transcript));
            dto.setHistory(history);
            dto.setKnown_context(known_context);
            dto.setResource_ids(resource_ids);
            dto.setEnable_rag(enable_rag);
            dto.setEnable_web(enable_web);
            dto.setSlide_count(slide_count);
            dto.setLanguage(language);
            Object data = pythonData(pythonPptClient.recognizeIntent(intentPayload(dto, "audio")));
            if (data instanceof Map<?, ?> map) {
                Map<String, Object> enriched = new LinkedHashMap<>();
                for (Map.Entry<?, ?> entry : map.entrySet()) {
                    if (entry.getKey() != null) {
                        enriched.put(String.valueOf(entry.getKey()), entry.getValue());
                    }
                }
                enriched.put("asr", asr.get("data"));
                return Result.success(enriched);
            }
            return Result.success(data);
        } catch (IOException e) {
            return Result.error(400, "读取语音文件失败: " + e.getMessage());
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-12 获取教学设计大纲
     *
     * <p>获取当前会话的教学设计大纲及其版本号。</p>
     *
     * @param id 会话ID（路径参数）
     * @return 当前教学任务信息（含 plan_json、plan_confirm_status）{@link TaskVO}
     */
    @GetMapping("/sessions/{id}/plan")
    public Result<TaskVO> getPlan(@PathVariable String id) {
        try {
            return Result.success(aiService.getPlan(id));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-13 确认/退回/补充教学设计大纲
     *
     * <p>教师确认大纲、退回修改或补充需求。需携带大纲版本号防止并发冲突。</p>
     *
     * @param id           会话ID（路径参数）
     * @param dto          操作请求参数 {@link PlanConfirmationDTO}
     * @return 操作结果（无数据体）
     */
    @PostMapping("/sessions/{id}/plan-confirmations")
    public Result<Void> confirmPlan(@PathVariable String id,
                                    @RequestBody PlanConfirmationDTO dto) {
        try {
            aiService.confirmPlan(id, dto);
            return Result.success();
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-14 创建执行任务
     *
     * <p>依据已确认的教学计划创建执行任务。</p>
     *
     * @param id 会话ID（路径参数）
     * @return 创建的执行任务 {@link TaskVO}（status 转为 running）
     */
    @PostMapping("/sessions/{id}/runs")
    public Result<TaskVO> createRun(@PathVariable String id) {
        try {
            return Result.success(aiService.createRun(id));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-15 查询执行任务状态
     *
     * <p>查询AI生成、反思及失败状态。</p>
     *
     * @param runId 执行任务ID（路径参数）
     * @return 任务当前状态 {@link TaskVO}
     */
    @GetMapping("/runs/{runId}")
    public Result<TaskVO> getRun(@PathVariable String runId) {
        try {
            return Result.success(aiService.getRun(runId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-16 获取执行事件流（SSE）
     *
     * <p>通过 Server-Sent Events 接收阶段、进度和预览更新，支持断线续传。
     * 返回值类型为 text/event-stream。</p>
     *
     * @param runId       执行任务ID（路径参数）
     * @param lastEventId 断线续传时携带最后收到的 eventId（选填）
     * @return SSE 事件流，包含阶段进度和预览数据
     */
    @GetMapping(value = "/runs/{runId}/events", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter getRunEvents(@PathVariable String runId,
                                   @RequestParam(required = false) String lastEventId) {
        SseEmitter emitter = new SseEmitter(30_000L);
        try {
            TaskVO task = aiService.getRun(runId);
            emitter.send(SseEmitter.event()
                    .id(lastEventId == null ? "1" : lastEventId)
                    .name("status")
                    .data(task));
            emitter.complete();
        } catch (RuntimeException | IOException e) {
            emitter.completeWithError(e);
        }
        return emitter;
    }

    private Map<String, Object> intentPayload(IntentRecognitionDTO dto, String inputType) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("user_id", String.valueOf(edu.zstu.utils.CurrentHolder.getCurrentId()));
        payload.put("session_id", blankToNull(dto.getSession_id()));
        payload.put("title", blankToNull(dto.getTitle()));
        payload.put("message", dto.getMessage());
        payload.put("history", parseJsonOrDefault(dto.getHistory(), List.of()));
        payload.put("known_context", parseJsonOrDefault(dto.getKnown_context(), Map.of()));
        payload.put("resource_ids", parseJsonOrDefault(dto.getResource_ids(), List.of()));
        payload.put("enable_rag", Boolean.TRUE.equals(dto.getEnable_rag()));
        payload.put("enable_web", Boolean.TRUE.equals(dto.getEnable_web()));
        payload.put("slide_count", dto.getSlide_count() == null ? 8 : dto.getSlide_count());
        payload.put("language", blankToDefault(dto.getLanguage(), "zh-CN"));
        payload.put("input_type", inputType);
        return payload;
    }

    private Object parseJsonOrDefault(String raw, Object fallback) {
        if (raw == null || raw.isBlank()) return fallback;
        try {
            return objectMapper.readValue(raw, new TypeReference<Object>() {});
        } catch (Exception ignored) {
            return fallback;
        }
    }

    private String extractAsrText(Map<String, Object> response) {
        Object data = response == null ? null : response.get("data");
        if (data instanceof Map<?, ?> map) {
            Object text = map.get("text");
            return text == null ? "" : String.valueOf(text).trim();
        }
        return "";
    }

    private Object pythonData(Map<String, Object> response) {
        if (response == null) return null;
        Object code = response.get("code");
        if (code != null && !"200".equals(String.valueOf(code))) {
            throw new RuntimeException(String.valueOf(response.getOrDefault("message", "Python服务调用失败")));
        }
        return response.get("data");
    }

    private String mergeMessage(String manualMessage, String transcript) {
        if (manualMessage == null || manualMessage.isBlank()) return transcript;
        return manualMessage.trim() + "\n" + transcript.trim();
    }

    private String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value;
    }

    private String blankToDefault(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value;
    }
}
