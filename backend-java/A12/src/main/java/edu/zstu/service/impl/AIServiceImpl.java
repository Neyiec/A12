package edu.zstu.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.zstu.dto.ConversationDTO;
import edu.zstu.dto.PlanConfirmationDTO;
import edu.zstu.dto.TaskCreateDTO;
import edu.zstu.entity.AI_Conversation;
import edu.zstu.entity.AI_Task;
import edu.zstu.mapper.AiConversationMapper;
import edu.zstu.mapper.AiTaskMapper;
import edu.zstu.service.AIService;
import edu.zstu.service.BusinessLogService;
import edu.zstu.service.PythonPptClient;
import edu.zstu.utils.CurrentHolder;
import edu.zstu.vo.ConversationVO;
import edu.zstu.vo.TaskVO;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class AIServiceImpl implements AIService {
    private final AiConversationMapper conversationMapper;
    private final AiTaskMapper taskMapper;
    private final BusinessLogService businessLogService;
    private final PythonPptClient pythonPptClient;
    private final ObjectMapper objectMapper;

    public AIServiceImpl(AiConversationMapper conversationMapper,
                         AiTaskMapper taskMapper,
                         BusinessLogService businessLogService,
                         PythonPptClient pythonPptClient,
                         ObjectMapper objectMapper) {
        this.conversationMapper = conversationMapper;
        this.taskMapper = taskMapper;
        this.businessLogService = businessLogService;
        this.pythonPptClient = pythonPptClient;
        this.objectMapper = objectMapper;
    }

    @Override
    @Transactional
    public TaskVO createSession(TaskCreateDTO dto) {
        Integer userId = requireLogin();
        if (isBlank(dto.getTitle())) throw new RuntimeException("会话标题不能为空");
        if (isBlank(dto.getSubject())) throw new RuntimeException("学科不能为空");
        if (isBlank(dto.getGrade())) throw new RuntimeException("年级不能为空");

        AI_Conversation conversation = new AI_Conversation();
        conversation.setUser_id(userId);
        conversation.setTitle(dto.getTitle());
        conversation.setStatus(defaultString(dto.getStatus(), "active"));
        conversation.setMessages(defaultJson(dto.getMessages(), "[]"));
        conversation.setContext_summary(null);
        conversation.setPython_session_id(null);
        conversation.setLast_question(null);
        conversationMapper.insert(conversation);

        AI_Task task = new AI_Task();
        task.setUser_id(userId);
        task.setConversation_id(conversation.getId());
        task.setTitle(dto.getTitle());
        task.setSubject(dto.getSubject());
        task.setGrade(dto.getGrade());
        task.setStatus("planning");
        task.setUploaded_refs(defaultJson(dto.getUploaded_refs(), "[]"));
        task.setPlan_json(defaultJson(dto.getPlan_json(), "{\"version\":1,\"title\":\"" + escapeJson(dto.getTitle()) + "\",\"slides\":[]}"));
        task.setPlan_confirm_status("pending");
        task.setExec_steps("[]");
        task.setReflections("[]");
        task.setPython_session_id(null);
        task.setPython_outline_id(null);
        task.setPython_presentation_id(null);
        task.setGeneration_mode("python");
        task.setError_message(null);
        taskMapper.insert(task);

        businessLogService.record("operation", "ai", "create_session", "ai_task", task.getId(),
                Map.of("conversation_id", conversation.getId(), "title", dto.getTitle(), "generation_mode", "python"));
        return toTaskVO(task);
    }

    @Override
    @Transactional
    public ConversationVO sendMessage(String id, ConversationDTO dto) {
        AI_Conversation conversation = requireConversation(id);
        AI_Task task = requireTaskByConversation(id);
        Integer userId = requireLogin();
        if (conversation.getUser_id() != userId) throw new RuntimeException("无权操作该会话");

        String userMessage = firstNotBlank(dto.getMessage(), dto.getMessages());
        if (isBlank(userMessage)) throw new RuntimeException("消息内容不能为空");

        PythonPptClient.OutlineChatResult pythonResult = callPythonOutline(userId, conversation, task, dto, userMessage);

        if (dto.getTitle() != null) conversation.setTitle(dto.getTitle());
        if (dto.getStatus() != null) conversation.setStatus(dto.getStatus());
        conversation.setMessages(appendMessageJson(conversation.getMessages(), userMessage, pythonResult));
        conversation.setContext_summary(dto.getContext_summary() != null ? dto.getContext_summary() : pythonPptClient.toJson(pythonResult.intent));
        if (!isBlank(pythonResult.pythonSessionId)) conversation.setPython_session_id(pythonResult.pythonSessionId);
        conversation.setLast_question(pythonResult.question == null ? "" : pythonResult.question);
        conversationMapper.update(conversation);

        updateTaskFromPythonResult(task, pythonResult);
        taskMapper.update(task);

        businessLogService.record("operation", "ai", "send_message", "ai_conversation", conversation.getId(),
                Map.of("python_status", pythonResult.status, "python_session_id", defaultString(pythonResult.pythonSessionId, "")));
        return toConversationVO(conversationMapper.findById(conversation.getId()));
    }

    @Override
    public TaskVO getPlan(String id) {
        AI_Task task = requireTaskByConversation(id);
        assertTaskOwner(task);
        return toTaskVO(task);
    }

    @Override
    @Transactional
    public void confirmPlan(String id, PlanConfirmationDTO dto) {
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
        businessLogService.record("operation", "ai", "plan_confirmation", "ai_task", task.getId(),
                Map.of("action", action, "plan_version", dto.getPlan_version()));
    }

    @Override
    @Transactional
    public TaskVO createRun(String id) {
        AI_Task task = requireTaskByConversation(id);
        assertTaskOwner(task);
        if (!"confirmed".equals(task.getPlan_confirm_status())) throw new RuntimeException("请先确认教学设计大纲");
        task.setStatus("executing");
        task.setExec_steps("[{\"step\":\"python_outline_ready\",\"status\":\"completed\"},{\"step\":\"presentation_generate\",\"status\":\"waiting_for_python_api\"}]");
        taskMapper.update(task);
        businessLogService.record("operation", "ai", "create_run", "ai_task", task.getId());
        return toTaskVO(taskMapper.findById(task.getId()));
    }

    @Override
    public TaskVO getRun(String runId) {
        AI_Task task = taskMapper.findById(parseId(runId));
        if (task == null) throw new RuntimeException("执行任务不存在");
        assertTaskOwner(task);
        return toTaskVO(task);
    }

    private PythonPptClient.OutlineChatResult callPythonOutline(Integer userId, AI_Conversation conversation,
                                                                AI_Task task, ConversationDTO dto, String userMessage) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("user_id", String.valueOf(userId));
        if (!isBlank(conversation.getPython_session_id())) {
            payload.put("session_id", conversation.getPython_session_id());
        }
        payload.put("message", userMessage);
        payload.put("resource_ids", parseJsonOrDefault(dto.getResource_ids(), List.of()));
        payload.put("enable_rag", Boolean.TRUE.equals(dto.getEnable_rag()));
        payload.put("enable_web", Boolean.TRUE.equals(dto.getEnable_web()));
        payload.put("slide_count", dto.getSlide_count() == null ? 8 : dto.getSlide_count());
        payload.put("known_context", parseJsonOrDefault(dto.getKnown_context(), Map.of(
                "title", task.getTitle(),
                "subject", task.getSubject(),
                "grade", task.getGrade()
        )));
        return pythonPptClient.streamOutlineChat(payload);
    }

    private void updateTaskFromPythonResult(AI_Task task, PythonPptClient.OutlineChatResult result) {
        task.setGeneration_mode("python");
        if (!isBlank(result.pythonSessionId)) task.setPython_session_id(result.pythonSessionId);
        if (!isBlank(result.outlineId)) task.setPython_outline_id(result.outlineId);

        if ("need_clarification".equals(result.status)) {
            task.setStatus("planning");
            task.setPlan_confirm_status("pending");
            task.setReflections("[{\"type\":\"clarification\",\"question\":\"" + escapeJson(result.question) + "\"}]");
        } else if ("completed".equals(result.status)) {
            task.setStatus("planning");
            task.setPlan_confirm_status("pending");
            task.setPlan_json(pythonPptClient.toJson(result.outline != null ? result.outline : result.finalData));
            task.setExec_steps("[{\"step\":\"python_outline_chat\",\"status\":\"completed\"}]");
            task.setError_message("");
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

    private String firstNotBlank(String first, String second) {
        if (!isBlank(first)) return first;
        return second;
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

    private String appendMessageJson(String oldMessages, String userMessage, PythonPptClient.OutlineChatResult result) {
        try {
            List<Object> messages = objectMapper.readValue(defaultJson(oldMessages, "[]"), new TypeReference<>() {});
            messages.add(Map.of("role", "user", "content", userMessage));
            if (!isBlank(result.question)) {
                messages.add(Map.of("role", "assistant", "content", result.question, "type", "question"));
            } else if (!isBlank(result.outlineId)) {
                messages.add(Map.of("role", "assistant", "content", "大纲已生成", "outline_id", result.outlineId));
            }
            return objectMapper.writeValueAsString(messages);
        } catch (Exception e) {
            return defaultJson(oldMessages, "[]");
        }
    }

    private String escapeJson(String value) {
        return value == null ? "" : value.replace("\\", "\\\\").replace("\"", "\\\"");
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
