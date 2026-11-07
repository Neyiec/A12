package edu.zstu.service;

import edu.zstu.dto.AuditDTO;
import edu.zstu.dto.AiReviewResultDTO;
import edu.zstu.dto.RecommendationDTO;
import edu.zstu.utils.PageResult;
import edu.zstu.vo.AuditVO;
import edu.zstu.vo.ContentVO;

import java.util.Map;

public interface AdminModerationService {
    Map<String, Object> getModerationMetrics();
    PageResult<AuditVO> listModerationTasks(String status, String targetType, Integer handlerId, String aiVerdict, String aiDomain, int page, int size);
    AuditVO getModerationTask(Integer id);
    ContentVO getModerationContent(Integer id);
    Map<String, Object> getAiReviewPayload(Integer auditId);
    void acceptAiReview(Integer auditId, AiReviewResultDTO result);
    Map<String, Object> rebuildCommunityIndex(Integer afterId, Integer limit);
    Map<String, Object> rebuildCommunityItemIndex(Integer id);
    void makeDecision(Integer id, AuditDTO dto, Integer adminId);
    ContentVO updateItemStatus(Integer id, String status);
    ContentVO updateRecommendation(Integer id, RecommendationDTO dto);
    PageResult<AuditVO> listReports(String status, int page, int size);
    AuditVO getReport(Integer id);
    void resolveReport(Integer id, AuditDTO dto, Integer adminId);
}
