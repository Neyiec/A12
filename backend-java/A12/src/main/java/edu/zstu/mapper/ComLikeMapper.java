package edu.zstu.mapper;

import edu.zstu.entity.Com_Like;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * 社区点赞表 Mapper
 * [数据交互说明] - CommunityServiceImpl: 点赞/取消/点赞态批量查询
 */
@Mapper
public interface ComLikeMapper {

    /** 插入点赞记录（唯一索引 uk_user_target 防重，重复插入抛 DuplicateKeyException） */
    int insert(Com_Like like);

    /** 删除指定用户对指定内容的点赞，返回删除行数（0 表示本来未点赞） */
    int deleteByUserAndTarget(@Param("userId") Integer userId,
                              @Param("targetType") String targetType,
                              @Param("targetId") Integer targetId);

    /** 查询指定用户是否已点赞某内容（存在返回 1） */
    int countByUserAndTarget(@Param("userId") Integer userId,
                             @Param("targetType") String targetType,
                             @Param("targetId") Integer targetId);

    /** 批量查询用户在给定内容集合中已点赞的内容 ID 列表（列表页点赞态注入） */
    List<Integer> findLikedTargetIds(@Param("userId") Integer userId,
                                     @Param("targetType") String targetType,
                                     @Param("targetIds") List<Integer> targetIds);
}
