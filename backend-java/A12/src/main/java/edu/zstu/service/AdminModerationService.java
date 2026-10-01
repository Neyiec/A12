package edu.zstu.service;

import edu.zstu.dto.AuditDTO;
import edu.zstu.dto.RecommendationDTO;
import edu.zstu.utils.PageResult;
import edu.zstu.vo.AuditVO;
import edu.zstu.vo.ContentVO;

import java.util.Map;

public interface AdminModerationService {
    PageResult<AuditVO> listModerationTasks(String status, String targetType, Integer handlerId, int page, int size);
    AuditVO getModerationTask(Integer id);
    ContentVO getModerationContent(Integer id);
    void makeDecision(Integer id, AuditDTO dto, Integer adminId);
    ContentVO updateItemStatus(Integer id, String status);
    ContentVO updateRecommendation(Integer id, RecommendationDTO dto);
    PageResult<AuditVO> listReports(String status, int page, int size);
    AuditVO getReport(Integer id);
    void resolveReport(Integer id, AuditDTO dto, Integer adminId);
}