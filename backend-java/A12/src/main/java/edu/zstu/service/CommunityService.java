package edu.zstu.service;

import edu.zstu.dto.*;
import edu.zstu.utils.PageResult;
import edu.zstu.vo.AuditVO;
import edu.zstu.vo.ContentVO;
import edu.zstu.vo.ProjectVO;
import edu.zstu.vo.RecentViewVO;

import java.util.Map;

public interface CommunityService {
    PageResult<ContentVO> listItems(ContentQueryDTO dto);
    ContentVO getItem(Integer id);
    void favorite(Integer itemId, Integer userId);
    void unfavorite(Integer itemId, Integer userId);
    void like(Integer itemId, Integer userId);
    void unlike(Integer itemId, Integer userId);
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
