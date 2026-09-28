package edu.zstu.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.zstu.dto.GeneralChatDTO;
import edu.zstu.dto.TaskCreateDTO;
import edu.zstu.entity.AI_Conversation;
import edu.zstu.mapper.AiConversationMapper;
import edu.zstu.utils.CurrentHolder;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;

/** 普通聊天由 Java 保管会话和逐条消息，Python 只负责生成回复。 */
@Slf4j
@Service
@RequiredArgsConstructor
public class GeneralChatService {
    private final AiConversationMapper conversationMapper;
    private final PythonPptClient pythonPptClient;
    private final ObjectMapper objectMapper;
    private final AIService aiService;

    public SseEmitter stream(GeneralChatDTO request) {
        Integer userId = CurrentHolder.getCurrentId();
        if (userId == null) throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "请先登录");
        String prompt = request == null || request.getMessage() == null ? "" : request.getMessage().trim();
        if (prompt.isEmpty() || prompt.length() > 60000) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "消息不能为空且不能超过 60000 字");
        }
        String modelProfile = allowed(request.getModel_profile(), Set.of("fast", "standard", "deep"), "standard");
        String reasoningEffort = allowed(request.getReasoning_effort(), Set.of("low", "medium", "high"), "medium");
        String turnId = UUID.randomUUID().toString();
        Map<String, Object> userMessage = messageRecord("user", prompt, turnId, "completed", modelProfile, reasoningEffort, null);

        AI_Conversation conversation;
        if (request.getSession_id() == null) {
            conversation = new AI_Conversation();
            conversation.setUser_id(userId);
            conversation.setTitle(prompt.substring(0, Math.min(40, prompt.length())));
            conversation.setStatus("general");
            conversation.setMessages(toJson(List.of(userMessage)));
            conversationMapper.insert(conversation);
        } else {
            conversation = conversationMapper.findById(request.getSession_id());
            if (conversation == null || conversation.getUser_id() != userId || !"general".equals(conversation.getStatus())) {
                throw new ResponseStatusException(HttpStatus.NOT_FOUND, "普通聊天会话不存在");
            }
            append(conversation.getId(), userId, userMessage);
            conversation = conversationMapper.findById(conversation.getId());
        }

        int conversationId = conversation.getId();
        RouteDecision decision = decideRoute(request.getRoute_preference(), userId,
                modelHistory(conversation.getMessages()));
        if ("planning".equals(decision.route())) {
            TaskCreateDTO task = new TaskCreateDTO();
            task.setTitle(prompt.substring(0, Math.min(40, prompt.length())));
            task.setResource_ids(request.getResource_ids() == null ? "[]" : request.getResource_ids());
            aiService.promoteGeneralSession(conversationId, task);
            conversation.setTitle(task.getTitle());
        }
        Map<String, Object> routeRecord = messageRecord("system", "意图分流：" + decision.route(), turnId,
                "completed", modelProfile, reasoningEffort, null);
        routeRecord.put("source", "intent_router");
        routeRecord.put("route", decision.route());
        routeRecord.put("reason", decision.reason());
        routeRecord.put("confidence", decision.confidence());
        routeRecord.put("forced", decision.forced());
        append(conversationId, userId, routeRecord);

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("user_id", String.valueOf(userId));
        payload.put("mode", "chat");
        payload.put("model_profile", modelProfile);
        payload.put("reasoning_effort", reasoningEffort);
        payload.put("messages", modelHistory(conversation.getMessages()));

        SseEmitter emitter = new SseEmitter(620_000L);
        Map<String, Object> sessionEvent = Map.of(
                "conversation_id", conversationId, "title", conversation.getTitle(),
                "turn_id", turnId, "user_message_id", userMessage.get("message_id"),
                "created_at", userMessage.get("created_at"));
        Map<String, Object> routeEvent = new LinkedHashMap<>();
        routeEvent.put("target", decision.route());
        routeEvent.put("reason", decision.reason());
        routeEvent.put("confidence", decision.confidence());
        routeEvent.put("forced", decision.forced());
        routeEvent.put("decision_id", routeRecord.get("message_id"));
        if ("planning".equals(decision.route())) {
            String reply = "已进入备课流程，请补充课程信息。";
            Map<String, Object> assistant = messageRecord("assistant", reply, turnId, "completed",
                    modelProfile, reasoningEffort, null);
            assistant.put("type", "workflow_prompt");
            append(conversationId, userId, assistant);
            routeEvent.put("assistant_content", reply);
            routeEvent.put("assistant_message_id", assistant.get("message_id"));
            routeEvent.put("created_at", assistant.get("created_at"));
        }
        CompletableFuture.runAsync(() -> {
            sendEvent(emitter, "session", sessionEvent);
            sendEvent(emitter, "route", routeEvent);
            if ("planning".equals(decision.route())) {
                emitter.complete();
                return;
            }
            pythonPptClient.streamWorkspaceChatToEmitter(payload, emitter, result -> {
                String status = result.error == null ? "completed" : (result.content.isBlank() ? "failed" : "interrupted");
                String content = result.content.isBlank()
                        ? "大模型暂时无法回复：" + (result.error == null ? "模型未返回有效内容" : result.error)
                        : result.content;
                Map<String, Object> assistant = messageRecord("assistant", content, turnId, status,
                        modelProfile, reasoningEffort, result.error);
                append(conversationId, userId, assistant);
                sendEvent(emitter, "message_saved", Map.of(
                        "message_id", assistant.get("message_id"), "turn_id", turnId,
                        "created_at", assistant.get("created_at"), "status", status));
            });
        });
        return emitter;
    }

    private RouteDecision decideRoute(String preference, Integer userId,
                                      List<Map<String, String>> history) {
        Map<String, Object> modelDecision = pythonPptClient.routeTeachingChat(String.valueOf(userId),
                history.subList(Math.max(0, history.size() - 8), history.size()), preference);
        if (modelDecision == null) return new RouteDecision("chat", 0, "分流服务不可用，继续普通对话", false);
        String route = "planning".equals(modelDecision.get("route")) ? "planning" : "chat";
        double confidence = modelDecision.get("confidence") instanceof Number number ? number.doubleValue() : 0;
        String reason = String.valueOf(modelDecision.getOrDefault("reason", "模型判断"));
        boolean forced = Boolean.TRUE.equals(modelDecision.get("forced"));
        return new RouteDecision(route, confidence, reason, forced);
    }

    private record RouteDecision(String route, double confidence, String reason, boolean forced) {}

    private void append(Integer conversationId, Integer userId, Map<String, Object> message) {
        if (conversationMapper.appendMessage(conversationId, userId, toJson(message)) != 1) {
            throw new IllegalStateException("聊天消息保存失败");
        }
    }

    private List<Map<String, String>> modelHistory(String rawMessages) {
        List<Map<String, String>> history = new ArrayList<>();
        try {
            List<Map<String, Object>> saved = objectMapper.readValue(rawMessages, new TypeReference<>() {});
            for (Map<String, Object> item : saved) {
                String role = String.valueOf(item.getOrDefault("role", ""));
                String content = String.valueOf(item.getOrDefault("content", ""));
                String status = String.valueOf(item.getOrDefault("status", "completed"));
                if (("user".equals(role) || ("assistant".equals(role) && "completed".equals(status))) && !content.isBlank()) {
                    history.add(Map.of("role", role, "content", content));
                }
            }
        } catch (Exception e) {
            throw new IllegalStateException("会话历史读取失败", e);
        }
        return history.subList(Math.max(0, history.size() - 30), history.size());
    }

    private Map<String, Object> messageRecord(String role, String content, String turnId, String status,
                                               String modelProfile, String reasoningEffort, String error) {
        Map<String, Object> record = new LinkedHashMap<>();
        record.put("message_id", UUID.randomUUID().toString());
        record.put("turn_id", turnId);
        record.put("role", role);
        record.put("content", content);
        record.put("created_at", Instant.now().toString());
        record.put("status", status);
        record.put("source", "general_chat");
        record.put("model_profile", modelProfile);
        record.put("reasoning_effort", reasoningEffort);
        if (error != null) record.put("error", error);
        return record;
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (Exception e) {
            throw new IllegalStateException("聊天消息序列化失败", e);
        }
    }

    private String allowed(String value, Set<String> values, String fallback) {
        return value != null && values.contains(value) ? value : fallback;
    }

    private void sendEvent(SseEmitter emitter, String name, Map<String, Object> data) {
        try {
            emitter.send(SseEmitter.event().name(name).data(toJson(data)));
        } catch (IOException | IllegalStateException e) {
            log.debug("聊天客户端已断开 event={}", name);
        }
    }
}
