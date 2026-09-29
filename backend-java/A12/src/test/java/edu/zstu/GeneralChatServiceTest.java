package edu.zstu;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.zstu.dto.GeneralChatDTO;
import edu.zstu.entity.AI_Conversation;
import edu.zstu.mapper.AiConversationMapper;
import edu.zstu.service.AIService;
import edu.zstu.service.GeneralChatService;
import edu.zstu.utils.CurrentHolder;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class GeneralChatServiceTest {
    private final ObjectMapper json = new ObjectMapper();

    @AfterEach void clearUser() { CurrentHolder.remove(); }

    @Test
    void directFlowPersistsQuestionRouteAndReplyWithoutModelClient() throws Exception {
        CurrentHolder.setCurrentId(7);
        AiConversationMapper mapper = mock(AiConversationMapper.class);
        AI_Conversation conversation = new AI_Conversation();
        doAnswer(invocation -> {
            AI_Conversation inserted = invocation.getArgument(0);
            inserted.setId(42);
            conversation.setId(42);
            conversation.setUser_id(7);
            conversation.setTitle(inserted.getTitle());
            conversation.setStatus(inserted.getStatus());
            conversation.setMessages(inserted.getMessages());
            return 1;
        }).when(mapper).insert(any());
        when(mapper.findById(42)).thenReturn(conversation);
        when(mapper.appendMessage(eq(42), eq(7), anyString())).thenAnswer(invocation -> {
            List<Map<String, Object>> saved = json.readValue(conversation.getMessages(), new TypeReference<>() {});
            saved.add(json.readValue((String) invocation.getArgument(2), new TypeReference<Map<String, Object>>() {}));
            conversation.setMessages(json.writeValueAsString(saved));
            return 1;
        });
        GeneralChatService service = new GeneralChatService(mapper, json, mock(AIService.class));
        GeneralChatDTO request = new GeneralChatDTO();
        request.setMessage("如何设计导入环节？");
        Map<String, Object> begun = service.beginTurn(request);
        assertEquals(1, ((List<?>) begun.get("messages")).size());
        Map<String, Object> completed = service.completeTurn(42, Map.of(
                "turn_id", begun.get("turn_id"), "route", "chat", "content", "先提出一个真实问题。"));
        assertEquals("completed", completed.get("status"));
        List<Map<String, Object>> saved = json.readValue(conversation.getMessages(), new TypeReference<>() {});
        assertEquals(List.of("user", "system", "assistant"), saved.stream().map(item -> item.get("role")).toList());
        assertEquals(saved.get(0).get("turn_id"), saved.get(2).get("turn_id"));
        service.completeTurn(42, Map.of("turn_id", begun.get("turn_id"), "route", "chat", "content", "重复提交"));
        assertEquals(3, json.readValue(conversation.getMessages(), new TypeReference<List<?>>() {}).size());
    }

    @Test
    void rejectsAnotherUsersSession() {
        CurrentHolder.setCurrentId(7);
        AiConversationMapper mapper = mock(AiConversationMapper.class);
        AI_Conversation other = new AI_Conversation();
        other.setId(42);
        other.setUser_id(8);
        other.setStatus("general");
        when(mapper.findById(42)).thenReturn(other);
        GeneralChatDTO request = new GeneralChatDTO();
        request.setSession_id(42);
        request.setMessage("私有对话");
        GeneralChatService service = new GeneralChatService(mapper, json, mock(AIService.class));
        assertThrows(ResponseStatusException.class, () -> service.beginTurn(request));
        verify(mapper, never()).appendMessage(anyInt(), anyInt(), anyString());
    }
}
