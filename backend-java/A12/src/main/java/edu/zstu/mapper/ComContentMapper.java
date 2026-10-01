package edu.zstu.mapper;

import edu.zstu.dto.ContentQueryDTO;
import edu.zstu.entity.Com_Content;
import org.apache.ibatis.annotations.*;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Mapper
public interface ComContentMapper {
    Com_Content findById(@Param("id") Integer id);
    List<Com_Content> findByAuthorId(@Param("authorId") Integer authorId);
    List<Com_Content> findPublic();
    List<Com_Content> findByType(@Param("contentType") String contentType);
    List<Com_Content> findAll();
    int insert(Com_Content content);
    int update(Com_Content content);
    int incrementViewCount(@Param("id") Integer id);
    int incrementUseCount(@Param("id") Integer id);
    int incrementViewCountBy(@Param("id") Integer id, @Param("delta") long delta);
    int incrementUseCountBy(@Param("id") Integer id, @Param("delta") long delta);

    /** 点赞数冗余列增减（delta 可为负，下限保护到 0） */
    int incrementLikeCountBy(@Param("id") Integer id, @Param("delta") long delta);

    /** 收藏数冗余列增减（delta 可为负，下限保护到 0） */
    int incrementFavoriteCountBy(@Param("id") Integer id, @Param("delta") long delta);

    /**
     * 公开内容检索（功能11 支持动态排序）
     * @param orderClause ORDER BY 子句，由 ServiceImpl 按白名单枚举拼装，禁止透传用户输入
     * @param window      true 时叠加日/周/月窗口聚合子查询（com_interaction + com_like）
     * @param since       窗口起点（window=false 时忽略）
     */
    List<Com_Content> searchPublic(@Param("dto") ContentQueryDTO dto,
                                   @Param("orderClause") String orderClause,
                                   @Param("window") boolean window,
                                   @Param("since") LocalDateTime since);

    /**
     * 榜单候选聚合（功能11）：窗口内互动聚合 + 达标过滤 + 热度降序
     * 返回 map 键：id / like_cnt / fav_cnt / use_cnt / view_cnt
     */
    List<Map<String, Object>> selectRankCandidates(@Param("contentType") String contentType,
                                                   @Param("since") LocalDateTime since,
                                                   @Param("threshold") int threshold,
                                                   @Param("limit") int limit);

    List<Com_Content> findByAuthorAndStatus(@Param("authorId") Integer authorId, @Param("status") String status);
}
