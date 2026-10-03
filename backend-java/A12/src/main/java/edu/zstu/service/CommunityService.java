package edu.zstu.service;

import edu.zstu.dto.*;
import edu.zstu.utils.PageResult;
import edu.zstu.vo.AuditVO;
import edu.zstu.vo.ContentVO;
import edu.zstu.vo.ProjectVO;
import edu.zstu.vo.RankItemVO;
import edu.zstu.vo.RecentViewVO;

import java.util.List;
import java.util.Map;

public interface CommunityService {
    /**
     * 公开内容检索（功能11 支持排序维度）
     * @param userId 当前用户（可空，用于注入 liked 点赞态）
     */
    PageResult<ContentVO> listItems(ContentQueryDTO dto, Integer userId);
    ContentVO getItem(Integer id, Integer userId);
    void favorite(Integer itemId, Integer userId);
    void unfavorite(Integer itemId, Integer userId);
    /** 功能11：点赞（幂等，唯一索引 + 限流防刷） */
    void like(Integer itemId, Integer userId);
    /** 功能11：取消点赞（幂等） */
    void unlike(Integer itemId, Integer userId);
    /** 功能11：热门榜单（period=day/week/month，Redis ZSET 优先，DB 聚合降级） */
    List<RankItemVO> listRankings(String contentType, String period, int limit, Integer userId);
    void recordView(Integer itemId, Integer userId);
    PageResult<ContentVO> listFavorites(int page, int size, Integer userId);
    PageResult<RecentViewVO> listRecentViews(int page, int size, Integer userId);
    void removeRecentView(Integer itemId, Integer userId);
    ProjectVO reuseItem(Integer id, InteractionDTO dto, Integer userId);
    ContentVO createSubmission(ContentDTO dto, Integer userId);
    PageResult<ContentVO> listSubmissions(ContentQueryDTO dto, Integer userId);
    ContentVO getSubmission(Integer id, Integer userId);
    ContentVO updateSubmission(Integer id, ContentDTO dto, Integer userId);
    Map<String, Object> saveSubmissionVersion(Integer id, String description, Integer userId);
    void submitForReview(Integer id, ReviewSubmissionDTO dto, Integer userId);
    int createReport(AuditDTO dto, Integer userId);
    PageResult<AuditVO> listReports(String status, int page, int size, Integer userId);
    AuditVO getReport(Integer id, Integer userId);
}
