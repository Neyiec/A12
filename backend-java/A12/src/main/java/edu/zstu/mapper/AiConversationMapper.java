package edu.zstu.mapper;

import edu.zstu.entity.AI_Conversation;
import org.apache.ibatis.annotations.*;
import java.util.List;

@Mapper
public interface AiConversationMapper {
    AI_Conversation findById(@Param("id") Integer id);
    List<AI_Conversation> findByUserId(@Param("userId") Integer userId);
    int insert(AI_Conversation conversation);
    int update(AI_Conversation conversation);
    int deleteById(@Param("id") Integer id, @Param("userId") Integer userId);
}
