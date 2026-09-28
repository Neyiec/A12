package edu.zstu;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.zstu.dto.GeneralChatDTO;
import edu.zstu.dto.TaskCreateDTO;
import edu.zstu.entity.AI_Conversation;
import edu.zstu.mapper.AiConversationMapper;
import edu.zstu.service.GeneralChatService;
import edu.zstu.service.AIService;
import edu.zstu.service.PythonPptClient;
import edu.zstu.utils.CurrentHolder;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Map;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class GeneralChatServiceTest {
    private final ObjectMapper json = new ObjectMapper();

    @AfterEach
    void clearUser() {
        CurrentHolder.remove();
    }

    @Test
    @SuppressWarnings("unchecked")
    void persistsEveryQuestionAndReplyWithTraceMetadataAndUsesOnlySavedHistory() throws Exception {
        CurrentHolder.setCurrentId(7);
        AiConversationMapper mapper = mock(AiConversationMapper.class);
        PythonPptClient python = mock(PythonPptClient.class);
        when(python.routeTeachingChat(anyString(), anyList(), nullable(String.class)))
                .thenReturn(Map.of("route", "chat", "confidence", 0.9, "reason", "继续聊天", "forced", false));
        AI_Conversation conversation = new AI_Conversation();
        AtomicInteger nextTurn = new AtomicInteger();
        CountDownLatch assistantSaved = new CountDownLatch(2);
        AtomicReference<Map<String, Object>> lastPayload = new AtomicReference<>();

        doAnswer(invocation -> {
            AI_Conversation inserted = invocation.getArgument(0);
            inserted.setId(42);
            conversation.setId(inserted.getId());
            conversation.setUser_id(inserted.getUser_id());
            conversation.setTitle(inserted.getTitle());
            conversation.setStatus(inserted.getStatus());
            conversation.setMessages(inserted.getMessages());
            return 1;
        }).when(mapper).insert(any());
        when(mapper.findById(42)).thenAnswer(invocation -> conversation);
        when(mapper.appendMessage(eq(42), eq(7), anyString())).thenAnswer(invocation -> {
            Map<String, Object> message = json.readValue((String) invocation.getArgument(2), new TypeReference<>() {});
            List<Map<String, Object>> saved = json.readValue(conversation.getMessages(), new TypeReference<>() {});
            saved.add(message);
            conversation.setMessages(json.writeValueAsString(saved));
            if ("assistant".equals(message.get("role"))) assistantSaved.countDown();
            return 1;
        });
        doAnswer(invocation -> {
            lastPayload.set(invocation.getArgument(0));
            var finished = (java.util.function.Consumer<PythonPptClient.WorkspaceChatResult>) invocation.getArgument(2);
            var result = new PythonPptClient.WorkspaceChatResult();
            result.content = "答复" + nextTurn.incrementAndGet();
            finished.accept(result);
            return null;
        }).when(python).streamWorkspaceChatToEmitter(anyMap(), any(), any());

        GeneralChatService service = new GeneralChatService(mapper, python, json, mock(AIService.class));
        GeneralChatDTO first = request(null, "第一问");
        service.stream(first);
        assertTrue(waitForMessages(conversation, 3));

        service.stream(request(42, "第二问"));
        assertTrue(assistantSaved.await(5, TimeUnit.SECONDS));
        List<Map<String, Object>> saved = json.readValue(conversation.getMessages(), new TypeReference<>() {});
        assertEquals(List.of("user", "system", "assistant", "user", "system", "assistant"), saved.stream().map(item -> item.get("role")).toList());
        assertEquals(List.of("第一问", "答复1", "第二问", "答复2"), saved.stream()
                .filter(item -> !"system".equals(item.get("role"))).map(item -> item.get("content")).toList());
        assertEquals(saved.get(0).get("turn_id"), saved.get(2).get("turn_id"));
        assertEquals(saved.get(3).get("turn_id"), saved.get(5).get("turn_id"));
        assertTrue(saved.stream().allMatch(item -> item.get("message_id") != null && item.get("created_at") != null));
        assertEquals("general", conversation.getStatus());
        assertEquals(3, ((List<?>) lastPayload.get().get("messages")).size());
    }

    @Test
    void rejectsAnotherUsersSession() {
        CurrentHolder.setCurrentId(7);
        AiConversationMapper mapper = mock(AiConversationMapper.class);
        AI_Conversation someoneElses = new AI_Conversation();
        someoneElses.setId(42);
        someoneElses.setUser_id(8);
        someoneElses.setStatus("general");
        when(mapper.findById(42)).thenReturn(someoneElses);
        var service = new GeneralChatService(mapper, mock(PythonPptClient.class), json, mock(AIService.class));
        assertThrows(ResponseStatusException.class, () -> service.stream(request(42, "私有对话")));
        verify(mapper, never()).appendMessage(anyInt(), anyInt(), anyString());
    }

    @Test
    void recordsFailedModelReplyForTheSameTurn() throws Exception {
        CurrentHolder.setCurrentId(7);
        AiConversationMapper mapper = mock(AiConversationMapper.class);
        PythonPptClient python = mock(PythonPptClient.class);
        when(python.routeTeachingChat(anyString(), anyList(), nullable(String.class)))
                .thenReturn(Map.of("route", "chat", "confidence", 0.9, "reason", "继续聊天", "forced", false));
        AI_Conversation conversation = new AI_Conversation();
        conversation.setId(42);
        conversation.setUser_id(7);
        conversation.setStatus("general");
        conversation.setTitle("失败也要记录");
        conversation.setMessages("[]");
        when(mapper.findById(42)).thenReturn(conversation);
        CountDownLatch savedReply = new CountDownLatch(1);
        doAnswer(invocation -> {
            List<Map<String, Object>> messages = json.readValue(conversation.getMessages(), new TypeReference<>() {});
            messages.add(json.readValue((String) invocation.getArgument(2), new TypeReference<>() {}));
            conversation.setMessages(json.writeValueAsString(messages));
            if ("assistant".equals(messages.get(messages.size() - 1).get("role"))) savedReply.countDown();
            return 1;
        }).when(mapper).appendMessage(eq(42), eq(7), anyString());
        doAnswer(invocation -> {
            var finished = (java.util.function.Consumer<PythonPptClient.WorkspaceChatResult>) invocation.getArgument(2);
            var result = new PythonPptClient.WorkspaceChatResult();
            result.error = "模型不可用";
            finished.accept(result);
            return null;
        }).when(python).streamWorkspaceChatToEmitter(anyMap(), any(), any());

        new GeneralChatService(mapper, python, json, mock(AIService.class)).stream(request(42, "失败也要记录"));
        assertTrue(savedReply.await(5, TimeUnit.SECONDS));
        List<Map<String, Object>> messages = json.readValue(conversation.getMessages(), new TypeReference<>() {});
        assertEquals(3, messages.size());
        assertEquals("failed", messages.get(2).get("status"));
        assertEquals("模型不可用", messages.get(2).get("error"));
        assertEquals(messages.get(0).get("turn_id"), messages.get(2).get("turn_id"));
    }

    @Test
    void explicitPlanningPromotesTheSameConversationAndDoesNotCallChatModel() throws Exception {
        CurrentHolder.setCurrentId(7);
        AiConversationMapper mapper = mock(AiConversationMapper.class);
        PythonPptClient python = mock(PythonPptClient.class);
        AIService aiService = mock(AIService.class);
        when(python.routeTeachingChat(anyString(), anyList(), eq("planning")))
                .thenReturn(Map.of("route", "planning", "confidence", 1.0, "reason", "用户手动选择", "forced", true));
        AI_Conversation conversation = new AI_Conversation();
        conversation.setId(42);
        conversation.setUser_id(7);
        conversation.setStatus("general");
        conversation.setTitle("原来的聊天");
        conversation.setMessages("[]");
        when(mapper.findById(42)).thenReturn(conversation);
        List<Map<String, Object>> saved = new java.util.ArrayList<>();
        when(mapper.appendMessage(eq(42), eq(7), anyString())).thenAnswer(invocation -> {
            saved.add(json.readValue((String) invocation.getArgument(2), new TypeReference<>() {}));
            conversation.setMessages(json.writeValueAsString(saved));
            return 1;
        });
        GeneralChatDTO request = request(42, "生成一份三年级分数课件");
        request.setRoute_preference("planning");
        new GeneralChatService(mapper, python, json, aiService).stream(request);
        verify(aiService).promoteGeneralSession(eq(42), any(TaskCreateDTO.class));
        verify(python, never()).streamWorkspaceChatToEmitter(anyMap(), any(), any());
        assertEquals(List.of("user", "system", "assistant"), saved.stream().map(item -> item.get("role")).toList());
        assertEquals("planning", saved.get(1).get("route"));
        assertNotEquals("原来的聊天", conversation.getTitle());
    }

    @Test
    void automaticRoutingKeepsHowToQuestionsInChatButPromotesCreationRequests() throws Exception {
        CurrentHolder.setCurrentId(7);
        AiConversationMapper mapper = mock(AiConversationMapper.class);
        PythonPptClient python = mock(PythonPptClient.class);
        AIService aiService = mock(AIService.class);
        when(python.routeTeachingChat(anyString(), anyList(), nullable(String.class)))
                .thenAnswer(invocation -> {
                    List<Map<String, String>> history = invocation.getArgument(1);
                    boolean planning = history.get(history.size() - 1).get("content").contains("请帮我设计一份教案");
                    return Map.of("route", planning ? "planning" : "chat", "confidence", 0.94,
                            "reason", "模型判断", "forced", false);
                });
        AI_Conversation conversation = new AI_Conversation();
        conversation.setId(42);
        conversation.setUser_id(7);
        conversation.setStatus("general");
        conversation.setTitle("原来的聊天");
        conversation.setMessages("[]");
        when(mapper.findById(42)).thenReturn(conversation);
        List<Map<String, Object>> saved = new java.util.ArrayList<>();
        CountDownLatch chatReply = new CountDownLatch(1);
        when(mapper.appendMessage(eq(42), eq(7), anyString())).thenAnswer(invocation -> {
            Map<String, Object> message = json.readValue((String) invocation.getArgument(2), new TypeReference<>() {});
            saved.add(message);
            conversation.setMessages(json.writeValueAsString(saved));
            if ("assistant".equals(message.get("role"))) chatReply.countDown();
            return 1;
        });
        doAnswer(invocation -> {
            var finished = (java.util.function.Consumer<PythonPptClient.WorkspaceChatResult>) invocation.getArgument(2);
            var result = new PythonPptClient.WorkspaceChatResult();
            result.content = "先确定教学目标";
            finished.accept(result);
            return null;
        }).when(python).streamWorkspaceChatToEmitter(anyMap(), any(), any());

        GeneralChatService service = new GeneralChatService(mapper, python, json, aiService);
        service.stream(request(42, "如何设计教案？"));
        assertTrue(chatReply.await(5, TimeUnit.SECONDS));
        verify(aiService, never()).promoteGeneralSession(anyInt(), any());
        service.stream(request(42, "请帮我设计一份教案"));
        verify(aiService).promoteGeneralSession(eq(42), any(TaskCreateDTO.class));
        verify(python, times(1)).streamWorkspaceChatToEmitter(anyMap(), any(), any());
        assertEquals(List.of("chat", "planning"), saved.stream()
                .filter(item -> "intent_router".equals(item.get("source")))
                .map(item -> String.valueOf(item.get("route"))).toList());
    }

    @Test
    void ambiguousTeachingRequestUsesModelDecisionBeforePromotion() throws Exception {
        CurrentHolder.setCurrentId(7);
        AiConversationMapper mapper = mock(AiConversationMapper.class);
        PythonPptClient python = mock(PythonPptClient.class);
        AIService aiService = mock(AIService.class);
        AI_Conversation conversation = new AI_Conversation();
        conversation.setId(42);
        conversation.setUser_id(7);
        conversation.setStatus("general");
        conversation.setTitle("原聊天");
        conversation.setMessages("[]");
        when(mapper.findById(42)).thenReturn(conversation);
        when(python.routeTeachingChat(eq("7"), anyList(), nullable(String.class))).thenReturn(Map.of(
                "route", "planning", "confidence", 0.93, "reason", "明确需要完整教学设计", "forced", false));
        List<Map<String, Object>> saved = new java.util.ArrayList<>();
        when(mapper.appendMessage(eq(42), eq(7), anyString())).thenAnswer(invocation -> {
            saved.add(json.readValue((String) invocation.getArgument(2), new TypeReference<>() {}));
            conversation.setMessages(json.writeValueAsString(saved));
            return 1;
        });

        new GeneralChatService(mapper, python, json, aiService)
                .stream(request(42, "我准备给三年级上一堂分数课"));

        verify(python).routeTeachingChat(eq("7"), anyList(), nullable(String.class));
        verify(aiService).promoteGeneralSession(eq(42), any(TaskCreateDTO.class));
        assertEquals("planning", saved.get(1).get("route"));
        assertEquals("明确需要完整教学设计", saved.get(1).get("reason"));
    }

    private GeneralChatDTO request(Integer sessionId, String message) {
        GeneralChatDTO request = new GeneralChatDTO();
        request.setSession_id(sessionId);
        request.setMessage(message);
        return request;
    }

    private boolean waitForMessages(AI_Conversation conversation, int expected) throws Exception {
        long deadline = System.currentTimeMillis() + 5000;
        while (System.currentTimeMillis() < deadline) {
            if (conversation.getMessages() != null
                    && json.readTree(conversation.getMessages()).size() >= expected) return true;
            Thread.sleep(10);
        }
        return false;
    }
}
