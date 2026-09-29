package edu.zstu;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.zstu.dto.TaskCreateDTO;
import edu.zstu.entity.AI_Conversation;
import edu.zstu.entity.AI_Task;
import edu.zstu.mapper.AiConversationMapper;
import edu.zstu.mapper.AiTaskMapper;
import edu.zstu.mapper.KbRetrievalLogMapper;
import edu.zstu.service.BusinessLogService;
import edu.zstu.service.impl.AIServiceImpl;
import edu.zstu.utils.CurrentHolder;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;


import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class AiPlanningPromotionTest {
    @AfterEach
    void clearUser() {
        CurrentHolder.remove();
    }

    @Test
    void promotesExistingConversationWithoutCreatingOrReplacingItsMessages() {
        CurrentHolder.setCurrentId(7);
        AiConversationMapper conversations = mock(AiConversationMapper.class);
        AiTaskMapper tasks = mock(AiTaskMapper.class);
        AI_Conversation conversation = new AI_Conversation();
        conversation.setId(42);
        conversation.setUser_id(7);
        conversation.setStatus("general");
        conversation.setTitle("原聊天");
        conversation.setMessages("[{\"role\":\"user\",\"content\":\"之前的提问\"}]");
        when(conversations.findById(42)).thenReturn(conversation);
        when(conversations.promoteToPlanning(eq(42), eq(7), isNull(), eq("分数课件"))).thenReturn(1);
        AIServiceImpl service = new AIServiceImpl(conversations, tasks, mock(BusinessLogService.class),
                new ObjectMapper(), mock(KbRetrievalLogMapper.class));
        TaskCreateDTO request = new TaskCreateDTO();
        request.setTitle("分数课件");

        service.promoteGeneralSession(42, request);

        ArgumentCaptor<AI_Task> savedTask = ArgumentCaptor.forClass(AI_Task.class);
        verify(tasks).insert(savedTask.capture());
        assertEquals(42, savedTask.getValue().getConversation_id());
        assertEquals(null, savedTask.getValue().getPython_session_id());
        verify(conversations, never()).insert(any());
        verify(conversations, never()).update(any());
        assertEquals("[{\"role\":\"user\",\"content\":\"之前的提问\"}]", conversation.getMessages());
    }
}
