package edu.zstu.mapper;

import edu.zstu.entity.AI_Task;
import org.apache.ibatis.annotations.*;
import java.util.List;

@Mapper
public interface AiTaskMapper {
    AI_Task findById(@Param("id") Integer id);
    List<AI_Task> findByUserId(@Param("userId") Integer userId);
    AI_Task findByConversationId(@Param("conversationId") Integer conversationId);
    List<AI_Task> findAll();
    int insert(AI_Task task);
    int update(AI_Task task);
    int deleteByConversationId(@Param("conversationId") Integer conversationId, @Param("userId") Integer userId);
}
