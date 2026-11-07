package edu.zstu.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.zstu.dto.ConversationDTO;
import edu.zstu.dto.PlanConfirmationDTO;
import edu.zstu.dto.TaskCreateDTO;
import edu.zstu.entity.AI_Conversation;
import edu.zstu.entity.AI_Task;
import edu.zstu.entity.Kb_Retrieval_Log;
import edu.zstu.mapper.AiConversationMapper;
import edu.zstu.mapper.AiTaskMapper;
import edu.zstu.mapper.KbRetrievalLogMapper;
import edu.zstu.service.AIService;
import edu.zstu.service.BusinessLogService;
import edu.zstu.utils.CurrentHolder;
import edu.zstu.vo.ConversationVO;
import edu.zstu.vo.TaskVO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Slf4j
@Service
public class AIServiceImpl implements AIService {
    private final AiConversationMapper conversationMapper;
    private final AiTaskMapper taskMapper;
    private final BusinessLogService businessLogService;
    private final ObjectMapper objectMapper;
    private final KbRetrievalLogMapper retrievalLogMapper;

    public AIServiceImpl(AiConversationMapper conversationMapper,
                         AiTaskMapper taskMapper,
                         BusinessLogService businessLogService,
                         ObjectMapper objectMapper,
                         KbRetrievalLogMapper retrievalLogMapper) {
        this.conversationMapper = conversationMapper;
        this.taskMapper = taskMapper;
        this.businessLogService = businessLogService;
        this.objectMapper = objectMapper;
        this.retrievalLogMapper = retrievalLogMapper;
    }

    @Override
    @Transactional
    public TaskVO createSession(TaskCreateDTO dto) {
        log.info("createSession title={}, subject={}, grade={}", dto.getTitle(), dto.getSubject(), dto.getGrade());
        Integer userId = requireLogin();
        if (isBlank(dto.getTitle())) throw new RuntimeException("会话标题不能为空");
//        if (isBlank(dto.getSubject())) throw new RuntimeException("学科不能为空");
//        if (isBlank(dto.getGrade())) throw new RuntimeException("年级不能为空");
        // Python 会话由浏览器首次直连 FastAPI 时创建，再由 outline-results 回填 ID。
        String pythonSessionId = null;

        AI_Conversation conversation = new AI_Conversation();
        conversation.setUser_id(userId);
        conversation.setTitle(dto.getTitle());
        conversation.setStatus(defaultString(dto.getStatus(), "active"));
        conversation.setMessages(defaultJson(dto.getMessages(), "[]"));
        conversation.setContext_summary(null);
        conversation.setPython_session_id(pythonSessionId);
        conversation.setLast_question(null);
        conversationMapper.insert(conversation);

        AI_Task task = new AI_Task();
        task.setUser_id(userId);
        task.setConversation_id(conversation.getId());
        task.setTitle(dto.getTitle());
        task.setSubject(dto.getSubject());
        task.setGrade(dto.getGrade());
        task.setStatus("planning");
        task.setUploaded_refs(defaultJson(firstNotBlank(dto.getUploaded_refs(), dto.getResource_ids()), "[]"));
        task.setPlan_json(defaultJson(dto.getPlan_json(), initialPlanJson(dto)));
        task.setPlan_confirm_status("pending");
        task.setExec_steps("[]");
        task.setReflections("[]");
        task.setPython_session_id(pythonSessionId);
        task.setPython_outline_id(null);
        task.setPython_presentation_id(null);
        task.setGeneration_mode("python");
        task.setError_message(null);
        taskMapper.insert(task);

        log.info("createSession success userId={}, conversationId={}, taskId={}", userId, conversation.getId(), task.getId());
        businessLogService.record("operation", "ai", "create_session", "ai_task", task.getId(),
                Map.of("conversation_id", conversation.getId(), "title", dto.getTitle(), "generation_mode", "python"));
        return toTaskVO(task);
    }

    /** 普通聊天转备课时沿用原会话 ID 和完整消息时间线。 */
    @Override
    @Transactional
    public TaskVO promoteGeneralSession(Integer conversationId, TaskCreateDTO dto) {
        Integer userId = requireLogin();
        AI_Conversation conversation = conversationMapper.findById(conversationId);
        if (conversation == null || conversation.getUser_id() != userId || !"general".equals(conversation.getStatus())) {
            throw new IllegalArgumentException("普通聊天会话不存在或已进入备课流程");
        }
        if (taskMapper.findByConversationId(conversationId) != null) {
            throw new IllegalStateException("此会话已有备课任务");
        }
        String title = defaultString(dto.getTitle(), conversation.getTitle());
        String pythonSessionId = null;
        AI_Task task = new AI_Task();
        task.setUser_id(userId);
        task.setConversation_id(conversationId);
        task.setTitle(title);
        task.setSubject(dto.getSubject());
        task.setGrade(dto.getGrade());
        task.setStatus("planning");
        task.setUploaded_refs(defaultJson(firstNotBlank(dto.getUploaded_refs(), dto.getResource_ids()), "[]"));
        task.setPlan_json(defaultJson(dto.getPlan_json(), initialPlanJson(dto)));
        task.setPlan_confirm_status("pending");
        task.setExec_steps("[]");
        task.setReflections("[]");
        task.setPython_session_id(pythonSessionId);
        task.setGeneration_mode("python");
        if (conversationMapper.promoteToPlanning(conversationId, userId, pythonSessionId, title) != 1) {
            throw new IllegalStateException("会话状态已变化，请重新打开对话");
        }
        taskMapper.insert(task);
        businessLogService.record("operation", "ai", "promote_general_session", "ai_task", task.getId(),
                Map.of("conversation_id", conversationId, "title", title));
        return toTaskVO(task);
    }

    @Override
    public List<ConversationVO> listSessions() {
        Integer userId = requireLogin();
        return conversationMapper.findByUserId(userId).stream()
                .map(this::toConversationVO)
                .collect(Collectors.toList());
    }

    @Override
    public ConversationVO getSession(String id) {
        AI_Conversation conversation = requireConversation(id);
        Integer userId = requireLogin();
        if (conversation.getUser_id() != userId) throw new RuntimeException("无权操作该会话");
        return toConversationVO(conversation);
    }

    @Override
    @Transactional
    public ConversationVO updateSession(String id, ConversationDTO dto) {
        AI_Conversation conversation = requireConversation(id);
        Integer userId = requireLogin();
        if (conversation.getUser_id() != userId) throw new RuntimeException("无权操作该会话");
        if (dto.getTitle() != null) {
            conversation.setTitle(dto.getTitle());
        }
        // 重命名/改状态只更新元数据；不能用旧快照覆盖正在流式追加的聊天消息。
        conversationMapper.updateMetadata(conversation.getId(), userId,
                dto.getTitle(), dto.getStatus(), dto.getContext_summary());
        return toConversationVO(conversationMapper.findById(conversation.getId()));
    }

    @Override
    @Transactional
    public void deleteSession(String id) {
        AI_Conversation conversation = requireConversation(id);
        Integer userId = requireLogin();
        if (conversation.getUser_id() != userId) throw new RuntimeException("无权操作该会话");
        taskMapper.deleteByConversationId(conversation.getId(), userId);
        conversationMapper.deleteById(conversation.getId(), userId);
    }

    @Override
    @Transactional
    public ConversationVO saveDirectOutlineResult(String id, Map<String, Object> data) {
        AI_Conversation conversation = requireConversation(id);
        AI_Task task = requireTaskByConversation(id);
        Integer userId = requireLogin();
        if (!userId.equals(conversation.getUser_id())) throw new RuntimeException("无权操作该会话");
        String message = String.valueOf(data.getOrDefault("message", "")).trim();
        if (message.isEmpty() || message.length() > 60000) throw new RuntimeException("消息长度不合法");
        String status = String.valueOf(data.getOrDefault("status", ""));
        if (!List.of("completed", "need_clarification", "awaiting_graph_confirmation", "failed").contains(status)) throw new RuntimeException("无效大纲状态");
        Object rawFinal = data.get("final_data");
        if ("completed".equals(status) && !(rawFinal instanceof Map<?, ?>)) throw new RuntimeException("大纲结果不能为空");
        OutlineResult pythonResult = new OutlineResult();
        if ("course_info_confirmation".equals(data.get("input_kind"))) pythonResult.inputKind = "course_info_confirmation";
        pythonResult.status = status;
        pythonResult.pythonSessionId = String.valueOf(data.getOrDefault("python_session_id", ""));
        pythonResult.question = String.valueOf(data.getOrDefault("question", ""));
        pythonResult.errorMessage = String.valueOf(data.getOrDefault("error_message", ""));
        if (rawFinal == null && "awaiting_graph_confirmation".equals(status)) rawFinal = data.get("graph_data");
        if (rawFinal instanceof Map<?, ?> map) {
            Map<String, Object> finalData = new LinkedHashMap<>();
            map.forEach((key, value) -> finalData.put(String.valueOf(key), value));
            pythonResult.finalData = finalData;
            Map<String, Object> outline = new LinkedHashMap<>();
            Object rawOutline = finalData.get("outline");
            if (rawOutline instanceof Map<?, ?> outlineMap) {
                outlineMap.forEach((key, value) -> outline.put(String.valueOf(key), value));
            } else {
                outline.putAll(finalData);
            }
            if (finalData.containsKey("learning_graphs")) outline.put("learning_graphs", finalData.get("learning_graphs"));
            pythonResult.outline = outline;
            pythonResult.outlineId = String.valueOf(finalData.getOrDefault("outline_id", ""));
            pythonResult.title = String.valueOf(finalData.getOrDefault("title", ""));
            pythonResult.slides = finalData.get("slides");
            pythonResult.intent = finalData.get("intent");
        }
        ConversationDTO dto = new ConversationDTO();
        persistOutlineMessage(conversation, task, dto, message, pythonResult);
        return toConversationVO(conversationMapper.findById(conversation.getId()));
    }

    /**
     * 将一次大纲交互的用户消息与 Python 结果落库到会话与任务。
     */
    private void persistOutlineMessage(AI_Conversation conversation, AI_Task task, ConversationDTO dto,
                                       String userMessage, OutlineResult pythonResult) {
        if (dto.getTitle() != null) conversation.setTitle(dto.getTitle());
        if (dto.getStatus() != null) conversation.setStatus(dto.getStatus());
        conversation.setMessages(appendMessageJson(conversation.getMessages(), userMessage, pythonResult));
        conversation.setContext_summary(dto.getContext_summary() != null ? dto.getContext_summary() : toJson(pythonResult.intent));
        if (!isBlank(pythonResult.pythonSessionId)) conversation.setPython_session_id(pythonResult.pythonSessionId);
        conversation.setLast_question(pythonResult.question == null ? "" : pythonResult.question);
        conversationMapper.update(conversation);

        updateTaskFromPythonResult(task, pythonResult, userMessage);
        taskMapper.update(task);

        businessLogService.record("operation", "ai", "send_message", "ai_conversation", conversation.getId(),
                Map.of("python_status", pythonResult.status, "python_session_id", defaultString(pythonResult.pythonSessionId, "")));
    }

    @Override
    public TaskVO getPlan(String id) {
        log.info("getPlan conversationId={}", id);
        AI_Task task = requireTaskByConversation(id);
        assertTaskOwner(task);
        return toTaskVO(task);
    }

    @Override
    @Transactional
    public void confirmPlan(String id, PlanConfirmationDTO dto) {
        log.info("confirmPlan conversationId={}, action={}, planVersion={}", id, dto.getAction(), dto.getPlan_version());
        AI_Task task = requireTaskByConversation(id);
        assertTaskOwner(task);
        String action = dto.getAction();
        if (!"confirm".equals(action) && !"reject".equals(action) && !"supplement".equals(action)) {
            throw new RuntimeException("无效操作: " + action);
        }
        task.setPlan_confirm_status("confirm".equals(action) ? "confirmed" : "rejected");
        task.setStatus("confirm".equals(action) ? "confirmed" : "planning");
        if (!isBlank(dto.getComment())) {
            task.setReflections("[{\"action\":\"" + escapeJson(action) + "\",\"comment\":\"" + escapeJson(dto.getComment()) + "\"}]");
        }
        taskMapper.update(task);
        log.info("confirmPlan success taskId={}, action={}, status={}", task.getId(), action, task.getStatus());
        businessLogService.record("operation", "ai", "plan_confirmation", "ai_task", task.getId(),
                Map.of("action", action, "plan_version", dto.getPlan_version()));
    }

    @Override
    @Transactional
    public TaskVO createRun(String id) {
        log.info("createRun conversationId={}", id);
        AI_Task task = requireTaskByConversation(id);
        assertTaskOwner(task);
        if (!"confirmed".equals(task.getPlan_confirm_status())) throw new RuntimeException("请先确认教学设计大纲");
        task.setStatus("executing");
        task.setExec_steps("[{\"step\":\"python_outline_ready\",\"status\":\"completed\"},{\"step\":\"presentation_generate\",\"status\":\"waiting_for_python_api\"}]");
        taskMapper.update(task);
        log.info("createRun success taskId={}, status={}", task.getId(), task.getStatus());
        businessLogService.record("operation", "ai", "create_run", "ai_task", task.getId());
        return toTaskVO(taskMapper.findById(task.getId()));
    }

    @Override
    public TaskVO getRun(String runId) {
        log.info("getRun runId={}", runId);
        AI_Task task = taskMapper.findById(parseId(runId));
        if (task == null) throw new RuntimeException("执行任务不存在");
        assertTaskOwner(task);
        return toTaskVO(task);
    }

    private Map<String, Object> buildOutlinePayload(Integer userId, AI_Conversation conversation,
                                                    AI_Task task, ConversationDTO dto, String userMessage) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("user_id", String.valueOf(userId));
        if (!isBlank(conversation.getPython_session_id())) {
            payload.put("session_id", conversation.getPython_session_id());
        }
        payload.put("message", userMessage);
        payload.put("resource_ids", requestResourceIds(dto, task));
        payload.put("enable_rag", requestBoolean(dto.getEnable_rag(), task, "enable_rag"));
        payload.put("enable_web", requestBoolean(dto.getEnable_web(), task, "enable_web"));
        payload.put("slide_count", requestSlideCount(dto, task));
        Map<String, Object> knownContext = buildKnownContext(task, dto.getKnown_context());
        String priorDiscussion = priorGeneralChatContext(conversation.getMessages());
        if (!priorDiscussion.isBlank()) {
            String requirements = String.valueOf(knownContext.getOrDefault("requirements", ""));
            knownContext.put("requirements", (requirements + "\n已讨论背景（本次明确要求优先）：\n" + priorDiscussion).trim());
        }
        payload.put("known_context", knownContext);
        payload.put("model_profile", firstNotBlank(dto.getModel_profile(), "standard"));
        payload.put("reasoning_effort", firstNotBlank(dto.getReasoning_effort(), "medium"));
        return payload;
    }

    private Object requestResourceIds(ConversationDTO dto, AI_Task task) {
        if (!isBlank(dto.getResource_ids())) {
            return parseJsonOrDefault(dto.getResource_ids(), List.of());
        }
        return parseJsonOrDefault(task.getUploaded_refs(), List.of());
    }

    private boolean requestBoolean(Boolean value, AI_Task task, String key) {
        if (value != null) {
            return value;
        }
        Object options = planOption(task, key);
        return options instanceof Boolean bool && bool;
    }

    private int requestSlideCount(ConversationDTO dto, AI_Task task) {
        if (dto.getSlide_count() != null) {
            return dto.getSlide_count();
        }
        Object option = planOption(task, "slide_count");
        if (option instanceof Number number) {
            return number.intValue();
        }
        if (option instanceof String text) {
            try {
                return Integer.parseInt(text);
            } catch (NumberFormatException ignored) {
                return 8;
            }
        }
        return 8;
    }

    @SuppressWarnings("unchecked")
    private Object planOption(AI_Task task, String key) {
        Object parsed = parseJsonOrDefault(task.getPlan_json(), Map.of());
        if (parsed instanceof Map<?, ?> map) {
            Object options = map.get("generation_options");
            if (options instanceof Map<?, ?> optionMap) {
                return optionMap.get(key);
            }
        }
        return null;
    }

    private Map<String, Object> buildKnownContext(AI_Task task, String knownContextJson) {
        Map<String, Object> knownContext = new LinkedHashMap<>();
        knownContext.put("title", task.getTitle());
        knownContext.put("subject", task.getSubject());
        knownContext.put("grade", task.getGrade());
        Object parsed = parseJsonOrDefault(knownContextJson, Map.of());
        if (parsed instanceof Map<?, ?> map) {
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                if (entry.getKey() != null && entry.getValue() != null && !String.valueOf(entry.getValue()).isBlank()) {
                    knownContext.put(String.valueOf(entry.getKey()), entry.getValue());
                }
            }
        }
        return knownContext;
    }

    private String priorGeneralChatContext(String rawMessages) {
        if (isBlank(rawMessages)) return "";
        try {
            List<Map<String, Object>> saved = objectMapper.readValue(rawMessages, new TypeReference<>() {});
            List<Map<String, Object>> discussion = saved.stream()
                    .filter(item -> "general_chat".equals(item.get("source")))
                    .filter(item -> "user".equals(item.get("role"))
                            || ("assistant".equals(item.get("role")) && "completed".equals(item.get("status"))))
                    .toList();
            String transcript = discussion.stream()
                    .skip(Math.max(0, discussion.size() - 12))
                    .map(item -> ("user".equals(item.get("role")) ? "教师：" : "AI：") + item.get("content"))
                    .collect(Collectors.joining("\n"));
            return transcript.substring(0, Math.min(3000, transcript.length()));
        } catch (Exception e) {
            log.warn("priorGeneralChatContext parse failed: {}", e.getMessage());
            return "";
        }
    }

    private String extractAsrText(Map<String, Object> response) {
        if (response == null) {
            return "";
        }
        Object data = response.get("data");
        if (data instanceof Map<?, ?> map) {
            Object text = map.get("text");
            return text == null ? "" : String.valueOf(text).trim();
        }
        Object text = response.get("text");
        return text == null ? "" : String.valueOf(text).trim();
    }

    private String mergeVoiceMessage(String manualMessage, String transcript) {
        if (isBlank(manualMessage)) {
            return transcript;
        }
        return manualMessage.trim() + "\n" + transcript.trim();
    }

    private void updateTaskFromPythonResult(AI_Task task, OutlineResult result, String userMessage) {
        task.setGeneration_mode("python");
        if (!isBlank(result.pythonSessionId)) task.setPython_session_id(result.pythonSessionId);
        if (!isBlank(result.outlineId)) task.setPython_outline_id(result.outlineId);

        if ("need_clarification".equals(result.status)) {
            task.setStatus("planning");
            task.setPlan_confirm_status("pending");
            task.setReflections("[{\"type\":\"clarification\",\"question\":\"" + escapeJson(result.question) + "\"}]");
        } else if ("awaiting_graph_confirmation".equals(result.status)) {
            task.setStatus("planning");
            task.setPlan_confirm_status("pending");
            task.setPlan_json(toJson(result.outline != null ? result.outline : result.finalData));
            task.setExec_steps("[{\"step\":\"learning_graph_review\",\"status\":\"awaiting_confirmation\"}]");
            task.setError_message("");
        } else if ("completed".equals(result.status)) {
            task.setStatus("planning");
            task.setPlan_confirm_status("pending");
            task.setPlan_json(toJson(result.outline != null ? result.outline : result.finalData));
            task.setReflections(buildGenerationReflections(result));
            task.setExec_steps("[{\"step\":\"python_outline_chat\",\"status\":\"completed\"}]");
            task.setError_message("");
            recordRetrievalLog(task, result, userMessage);
        } else if ("failed".equals(result.status)) {
            task.setStatus("failed");
            task.setError_message(result.errorMessage);
        }
    }

    private AI_Conversation requireConversation(String id) {
        AI_Conversation conversation = conversationMapper.findById(parseId(id));
        if (conversation == null) throw new RuntimeException("会话不存在");
        return conversation;
    }

    private void recordRetrievalLog(AI_Task task, OutlineResult result, String userMessage) {
        try {
            Object toolTrace = result.finalData == null ? null : result.finalData.get("tool_trace");
            if (!(toolTrace instanceof List<?> traces)) {
                return;
            }
            Object ragTrace = traces.stream()
                    .filter(item -> item instanceof Map<?, ?> map && "rag_search".equals(String.valueOf(map.get("tool"))))
                    .findFirst()
                    .orElse(null);
            if (ragTrace == null) {
                return;
            }
            Kb_Retrieval_Log logItem = new Kb_Retrieval_Log();
            logItem.setUser_id(task.getUser_id());
            logItem.setTask_id(task.getId());
            logItem.setType("retrieval");
            logItem.setQuery_text(userMessage);
            logItem.setResult_chunks(objectMapper.writeValueAsString(ragTrace));
            logItem.setPrompt_context(truncateString(String.valueOf(result.finalData.getOrDefault("title", "")), 1000));
            logItem.setGenerated_content(null);
            logItem.setModel_name("python-rag-hybrid-rerank");
            retrievalLogMapper.insert(logItem);
        } catch (Exception e) {
            log.warn("recordRetrievalLog failed taskId={}: {}", task.getId(), e.getMessage());
        }
    }
    private AI_Task requireTaskByConversation(String id) {
        AI_Task task = taskMapper.findByConversationId(parseId(id));
        if (task == null) throw new RuntimeException("会话任务不存在");
        return task;
    }

    private void assertTaskOwner(AI_Task task) {
        Integer userId = requireLogin();
        if (task.getUser_id() != userId) throw new RuntimeException("无权操作该任务");
    }

    private Integer requireLogin() {
        Integer userId = CurrentHolder.getCurrentId();
        if (userId == null) throw new RuntimeException("未登录");
        return userId;
    }

    private int parseId(String id) {
        try {
            return Integer.parseInt(id);
        } catch (NumberFormatException e) {
            throw new RuntimeException("ID格式错误");
        }
    }

    private String defaultString(String value, String fallback) {
        return isBlank(value) ? fallback : value;
    }

    private String defaultJson(String value, String fallback) {
        return isBlank(value) ? fallback : value;
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (Exception e) {
            return "null";
        }
    }

    private String firstNotBlank(String first, String second) {
        if (!isBlank(first)) return first;
        return second;
    }

    private String latestUserMessage(String messagesJson) {
        if (isBlank(messagesJson)) return messagesJson;
        try {
            Object parsed = objectMapper.readValue(messagesJson, new TypeReference<Object>() {});
            if (parsed instanceof List<?> list) {
                for (int i = list.size() - 1; i >= 0; i--) {
                    Object item = list.get(i);
                    if (item instanceof Map<?, ?> message) {
                        Object role = message.get("role");
                        Object content = message.get("content");
                        if ((role == null || "user".equals(String.valueOf(role))) && content != null && !String.valueOf(content).isBlank()) {
                            return String.valueOf(content);
                        }
                    } else if (item instanceof String text && !text.isBlank()) {
                        return text;
                    }
                }
            }
        } catch (Exception ignored) {
            return messagesJson;
        }
        return messagesJson;
    }

    private boolean isBlank(String value) {
        return value == null || value.isBlank();
    }

    private Object parseJsonOrDefault(String value, Object fallback) {
        if (isBlank(value)) return fallback;
        try {
            return objectMapper.readValue(value, new TypeReference<Object>() {});
        } catch (Exception ignored) {
            return fallback;
        }
    }

    private String initialPlanJson(TaskCreateDTO dto) {
        Map<String, Object> plan = new LinkedHashMap<>();
        plan.put("version", 1);
        plan.put("title", dto.getTitle());
        plan.put("slides", List.of());
        Map<String, Object> options = new LinkedHashMap<>();
        options.put("resource_ids", parseJsonOrDefault(firstNotBlank(dto.getResource_ids(), dto.getUploaded_refs()), List.of()));
        options.put("enable_rag", Boolean.TRUE.equals(dto.getEnable_rag()));
        options.put("enable_web", Boolean.TRUE.equals(dto.getEnable_web()));
        options.put("slide_count", dto.getSlide_count() == null ? 8 : dto.getSlide_count());
        plan.put("generation_options", options);
        try {
            return objectMapper.writeValueAsString(plan);
        } catch (Exception e) {
            return "{\"version\":1,\"title\":\"" + escapeJson(dto.getTitle()) + "\",\"slides\":[]}";
        }
    }

    private String appendMessageJson(String oldMessages, String userMessage, OutlineResult result) {
        try {
            List<Object> messages = objectMapper.readValue(defaultJson(oldMessages, "[]"), new TypeReference<>() {});
            Map<String, Object> userEntry = new LinkedHashMap<>();
            userEntry.put("role", "user");
            userEntry.put("content", userMessage);
            if (result.inputKind != null) userEntry.put("type", result.inputKind);
            messages.add(userEntry);
            if (!isBlank(result.question)) {
                messages.add(Map.of("role", "assistant", "content", result.question, "type", "question"));
            } else if ("awaiting_graph_confirmation".equals(result.status)) {
                messages.add(Map.of("role", "assistant", "content", "知识图谱与技能图谱已生成，请核对后确认，再生成大纲。",
                        "type", "graph_review"));
            } else if ("completed".equals(result.status)) {
                Map<String, Object> assistant = new LinkedHashMap<>();
                assistant.put("role", "assistant");
                assistant.put("content", assistantOutlineMessage(result));
                if (!isBlank(result.outlineId)) assistant.put("outline_id", result.outlineId);
                messages.add(assistant);
            } else if ("failed".equals(result.status)) {
                messages.add(Map.of("role", "assistant", "content",
                        "大纲生成失败：" + defaultString(result.errorMessage, "未知错误"), "type", "error"));
            }
            return objectMapper.writeValueAsString(messages);
        } catch (Exception e) {
            return defaultJson(oldMessages, "[]");
        }
    }

    private String assistantOutlineMessage(OutlineResult result) {
        String title = isBlank(result.title) ? "未命名大纲" : result.title;
        int slideCount = 0;
        if (result.slides instanceof List<?> list) {
            slideCount = list.size();
        }
        StringBuilder message = new StringBuilder("已生成《").append(title).append("》的大纲");
        if (slideCount > 0) {
            message.append("，共 ").append(slideCount).append(" 页");
        }
        message.append("。");
        Object assets = result.finalData == null ? null : result.finalData.get("interactive_assets");
        if (assets instanceof List<?> list && !list.isEmpty()) {
            message.append("\n已规划动画/小游戏资源，生成 PPT 后导出时会随 static 目录一起打包。");
        }
        return message.toString();
    }

    private String buildGenerationReflections(OutlineResult result) {
        try {
            Map<String, Object> data = result.finalData == null ? Map.of() : result.finalData;
            Object reflection = result.reflection != null ? result.reflection : data.get("reflection");
            Object toolTrace = data.get("tool_trace");
            Object qualityReport = data.get("quality_report");
            if (qualityReport == null && data.get("outline") instanceof Map<?, ?> outline) {
                qualityReport = outline.get("quality_report");
            }
            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("type", "generation_reflection");
            payload.put("reflection", reflection == null ? Map.of() : reflection);
            payload.put("tool_trace", toolTrace == null ? List.of() : toolTrace);
            payload.put("quality_report", qualityReport == null ? Map.of() : qualityReport);
            return objectMapper.writeValueAsString(List.of(payload));
        } catch (Exception e) {
            return "[{\"type\":\"generation_reflection\",\"error\":\"" + escapeJson(e.getMessage()) + "\"}]";
        }
    }

    private String truncateString(String value, int maxLength) {
        if (value == null) {
            return null;
        }
        if (value.length() <= maxLength) {
            return value;
        }
        return value.substring(0, maxLength);
    }

    private String escapeJson(String value) {
        return value == null ? "" : value.replace("\\", "\\\\").replace("\"", "\\\"");
    }

    private static class OutlineResult {
        String inputKind;
        String status;
        String pythonSessionId;
        String outlineId;
        String title;
        String question;
        String errorMessage;
        Object intent;
        Object outline;
        Object slides;
        Object reflection;
        Map<String, Object> finalData = new LinkedHashMap<>();
    }

    private TaskVO toTaskVO(AI_Task task) {
        TaskVO vo = new TaskVO();
        BeanUtil.copyProperties(task, vo);
        return vo;
    }

    private ConversationVO toConversationVO(AI_Conversation conversation) {
        ConversationVO vo = new ConversationVO();
        BeanUtil.copyProperties(conversation, vo);
        return vo;
    }
}
