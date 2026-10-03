package edu.zstu.mapper;

import edu.zstu.entity.Com_Interaction;
import org.apache.ibatis.annotations.*;
import java.util.List;

@Mapper
public interface ComInteractionMapper {
    Com_Interaction findById(@Param("id") Long id);
    List<Com_Interaction> findByUserAndAction(@Param("userId") Integer userId, @Param("actionType") String actionType);
    List<Com_Interaction> findByTarget(@Param("targetType") String targetType, @Param("targetId") Integer targetId);
    int insert(Com_Interaction interaction);
    int deleteByUserAndTarget(@Param("userId") Integer userId, @Param("targetType") String targetType,
                              @Param("targetId") Integer targetId, @Param("actionType") String actionType);
    List<Com_Interaction> findRecentViewsByUser(@Param("userId") Integer userId);
    Com_Interaction findByUserAndTarget(@Param("userId") Integer userId, @Param("actionType") String actionType,
                                        @Param("targetType") String targetType, @Param("targetId") Integer targetId);
    int countByTargetAndAction(@Param("targetId") Integer targetId, @Param("actionType") String actionType);
}
