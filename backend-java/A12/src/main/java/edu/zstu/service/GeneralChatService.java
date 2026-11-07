package edu.zstu.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.zstu.dto.GeneralChatDTO;
import edu.zstu.dto.TaskCreateDTO;
import edu.zstu.entity.AI_Conversation;
import edu.zstu.mapper.AiConversationMapper;
import edu.zstu.utils.CurrentHolder;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/** Java 只保管会话与消息；分流和回复由浏览器直连 Python。 */
@Service
@RequiredArgsConstructor
public class GeneralChatService {
    private final AiConversationMapper conversationMapper;
    private final ObjectMapper objectMapper;
    private final AIService aiService;

    @Transactional
    public Map<String, Object> beginTurn(GeneralChatDTO request) {
        Integer userId = requireUser();
        String prompt = request == null || request.getMessage() == null ? "" : request.getMessage().trim();
        if (prompt.isEmpty() || prompt.length() > 60000) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "消息长度不合法");
        String model = allowed(request.getModel_profile(), Set.of("fast", "standard", "deep"), "standard");
        String effort = allowed(request.getReasoning_effort(), Set.of("low", "medium", "high"), "medium");
        String turnId = UUID.randomUUID().toString();
        Map<String, Object> userMessage = messageRecord("user", prompt, turnId, "completed", model, effort);
        AI_Conversation conversation;
        if (request.getSession_id() == null) {
            conversation = new AI_Conversation();
            conversation.setUser_id(userId);
            conversation.setTitle(prompt.substring(0, Math.min(40, prompt.length())));
            conversation.setStatus("general");
            conversation.setMessages(toJson(List.of(userMessage)));
            conversationMapper.insert(conversation);
        } else {
            conversation = ownedGeneral(request.getSession_id(), userId);
            append(conversation.getId(), userId, userMessage);
            conversation = conversationMapper.findById(conversation.getId());
        }
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("conversation_id", conversation.getId());
        data.put("title", conversation.getTitle());
        data.put("turn_id", turnId);
        data.put("user_message_id", userMessage.get("message_id"));
        data.put("created_at", userMessage.get("created_at"));
        data.put("messages", modelHistory(conversation.getMessages()));
        return data;
    }

    @Transactional
    public Map<String, Object> completeTurn(Integer sessionId, Map<String, Object> result) {
        Integer userId = requireUser();
        AI_Conversation conversation = conversationMapper.findById(sessionId);
        if (conversation == null || !userId.equals(conversation.getUser_id())) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "普通聊天会话不存在");
        }
        String turnId = String.valueOf(result.getOrDefault("turn_id", ""));
        List<Map<String, Object>> saved = storedMessages(conversation.getMessages());
        if (saved.stream().noneMatch(item -> "user".equals(item.get("role")) && turnId.equals(item.get("turn_id")))) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "回合不存在");
        }
        for (Map<String, Object> item : saved) {
            if ("assistant".equals(item.get("role")) && turnId.equals(item.get("turn_id"))) {
                return trace(item, turnId);
            }
        }
        String route = "planning".equals(result.get("route")) ? "planning" : "batch".equals(result.get("route")) ? "batch" : "chat";
        String content = String.valueOf(result.getOrDefault("content", "")).trim();
        if (content.isEmpty() || content.length() > 200000) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "回复长度不合法");
        String status = "failed".equals(result.get("status")) ? "failed" : "completed";
        String model = allowed((String) result.get("model_profile"), Set.of("fast", "standard", "deep"), "standard");
        String effort = allowed((String) result.get("reasoning_effort"), Set.of("low", "medium", "high"), "medium");
        Map<String, Object> routeRecord = messageRecord("system", "意图分流：" + route, turnId, "completed", model, effort);
        routeRecord.put("source", "intent_router");
        routeRecord.put("route", route);
        routeRecord.put("reason", String.valueOf(result.getOrDefault("reason", "")));
        append(sessionId, userId, routeRecord);
        if ("planning".equals(route) && "general".equals(conversation.getStatus())) {
            TaskCreateDTO task = new TaskCreateDTO();
            task.setTitle(conversation.getTitle());
            task.setResource_ids(String.valueOf(result.getOrDefault("resource_ids", "[]")));
            aiService.promoteGeneralSession(sessionId, task);
        }
        Map<String, Object> assistant = messageRecord("assistant", content, turnId, status, model, effort);
        if ("failed".equals(status)) assistant.put("error", content);
        if ("planning".equals(route)) assistant.put("type", "workflow_prompt");
        append(sessionId, userId, assistant);
        return trace(assistant, turnId);
    }

    private Integer requireUser() {
        Integer userId = CurrentHolder.getCurrentId();
        if (userId == null) throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "请先登录");
        return userId;
    }

    private AI_Conversation ownedGeneral(Integer id, Integer userId) {
        AI_Conversation conversation = conversationMapper.findById(id);
        if (conversation == null || !userId.equals(conversation.getUser_id()) || !"general".equals(conversation.getStatus())) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "普通聊天会话不存在");
        }
        return conversation;
    }

    private void append(Integer conversationId, Integer userId, Map<String, Object> message) {
        if (conversationMapper.appendMessage(conversationId, userId, toJson(message)) != 1) {
            throw new IllegalStateException("聊天消息保存失败");
        }
    }

    private List<Map<String, Object>> storedMessages(String raw) {
        try { return objectMapper.readValue(raw, new TypeReference<>() {}); }
        catch (Exception e) { throw new IllegalStateException("会话历史读取失败", e); }
    }

    private List<Map<String, String>> modelHistory(String raw) {
        List<Map<String, String>> history = new ArrayList<>();
        for (Map<String, Object> item : storedMessages(raw)) {
            String role = String.valueOf(item.getOrDefault("role", ""));
            String content = String.valueOf(item.getOrDefault("content", ""));
            String status = String.valueOf(item.getOrDefault("status", "completed"));
            if (("user".equals(role) || ("assistant".equals(role) && "completed".equals(status))) && !content.isBlank()) {
                history.add(Map.of("role", role, "content", content));
            }
        }
        return history.subList(Math.max(0, history.size() - 30), history.size());
    }

    private Map<String, Object> messageRecord(String role, String content, String turnId, String status,
                                               String model, String effort) {
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("message_id", UUID.randomUUID().toString());
        item.put("turn_id", turnId);
        item.put("role", role);
        item.put("content", content);
        item.put("created_at", Instant.now().toString());
        item.put("status", status);
        item.put("source", "general_chat");
        item.put("model_profile", model);
        item.put("reasoning_effort", effort);
        return item;
    }

    private Map<String, Object> trace(Map<String, Object> item, String turnId) {
        return Map.of("message_id", item.get("message_id"), "turn_id", turnId,
                "created_at", item.get("created_at"), "status", item.getOrDefault("status", "completed"));
    }

    private String toJson(Object value) {
        try { return objectMapper.writeValueAsString(value); }
        catch (Exception e) { throw new IllegalStateException("聊天消息序列化失败", e); }
    }

    private String allowed(String value, Set<String> options, String fallback) {
        return value != null && options.contains(value) ? value : fallback;
    }
}
