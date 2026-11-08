package edu.zstu;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.zstu.entity.AI_Conversation;
import edu.zstu.entity.AI_Task;
import edu.zstu.mapper.*;
import edu.zstu.service.BusinessLogService;
import edu.zstu.service.impl.AIServiceImpl;
import edu.zstu.utils.CurrentHolder;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import java.util.Map;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class CourseInfoConfirmationTest {
    @AfterEach void clearUser() { CurrentHolder.remove(); }
    @Test void structuredConfirmationRetainsEvidenceAndOrdinaryMessagesRemainVisible() throws Exception {
        CurrentHolder.setCurrentId(7);
        var conversations = mock(AiConversationMapper.class);
        var tasks = mock(AiTaskMapper.class);
        var conversation = new AI_Conversation();
        conversation.setId(42); conversation.setUser_id(7); conversation.setMessages("[]");
        var task = new AI_Task(); task.setId(9); task.setUser_id(7); task.setConversation_id(42);
        when(conversations.findById(42)).thenReturn(conversation);
        when(tasks.findByConversationId(42)).thenReturn(task);
        var json = new ObjectMapper();
        var service = new AIServiceImpl(conversations, tasks, mock(BusinessLogService.class), json, mock(KbRetrievalLogMapper.class));
        service.saveDirectOutlineResult("42", Map.of("message", "大学数学大一，课程名称：微积分入门", "status", "failed",
                "error_message", "联调", "input_kind", "course_info_confirmation"));
        var stored = json.readTree(conversation.getMessages());
        assertEquals("course_info_confirmation", stored.get(0).get("type").asText());
        assertEquals("大学数学大一，课程名称：微积分入门", stored.get(0).get("content").asText());
        service.saveDirectOutlineResult("42", Map.of("message", "请增加函数图像", "status", "failed", "error_message", "联调"));
        stored = json.readTree(conversation.getMessages());
        assertEquals("请增加函数图像", stored.get(2).get("content").asText());
        assertFalse(stored.get(2).has("type"));
    }
}
