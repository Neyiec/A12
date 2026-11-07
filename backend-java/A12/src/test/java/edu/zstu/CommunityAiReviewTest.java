package edu.zstu;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.zstu.dto.AiReviewResultDTO;
import edu.zstu.dto.AuditDTO;
import edu.zstu.controller.CommunityReviewInternalController;
import edu.zstu.entity.Adm_Audit;
import edu.zstu.entity.Com_Content;
import edu.zstu.mapper.AdmAuditMapper;
import edu.zstu.mapper.ComContentMapper;
import edu.zstu.mapper.SysUserMapper;
import edu.zstu.service.BusinessLogService;
import edu.zstu.service.CommunityReviewSampling;
import edu.zstu.service.ResourceIndexEventPublisher;
import edu.zstu.service.impl.AdminModerationServiceImpl;
import edu.zstu.utils.RedisCacheUtil;
import org.apache.ibatis.builder.xml.XMLMapperBuilder;
import org.apache.ibatis.session.Configuration;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;
import java.io.InputStream;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

class CommunityAiReviewTest {
    private final AdmAuditMapper audits = mock(AdmAuditMapper.class);
    private final ComContentMapper contents = mock(ComContentMapper.class);
    private final CommunityReviewSampling sampling = mock(CommunityReviewSampling.class);
    private final AdminModerationServiceImpl service = new AdminModerationServiceImpl(
            audits, contents, mock(SysUserMapper.class), mock(BusinessLogService.class),
            mock(RedisCacheUtil.class), new ObjectMapper(), mock(ResourceIndexEventPublisher.class), sampling);

    private List<Map<String, Object>> completeChecks() {
        return List.of("政治敏感", "广告导流", "侵权嫌疑", "内容质量").stream()
                .map(name -> Map.<String, Object>of("name", name, "status", "pass", "evidence", "原稿可核验")).toList();
    }

    private Adm_Audit pendingAudit() {
        Adm_Audit audit = new Adm_Audit();
        audit.setId(12);
        audit.setAudit_type("audit");
        audit.setTarget_type("ppt");
        audit.setTarget_id(34);
        audit.setStatus("pending");
        return audit;
    }

    private Com_Content reviewingPpt() {
        Com_Content content = new Com_Content();
        content.setId(34);
        content.setVersion(2);
        content.setContent_type("ppt");
        content.setStatus("reviewing");
        return content;
    }

    @Test
    void aiFailureNeverPublishesPpt() {
        Adm_Audit audit = pendingAudit();
        Com_Content content = reviewingPpt();
        when(audits.findByIdForUpdate(12)).thenReturn(audit);
        when(audits.saveAiReview(any())).thenReturn(1);
        when(contents.findByIdForUpdate(34)).thenReturn(content);
        service.acceptAiReview(12, new AiReviewResultDTO(2, "science", "fail", 20,
                "公式错误", "test-model", List.of(), List.of(Map.of("evidence", "公式错误"))));
        assertEquals("pending", audit.getStatus());
        assertEquals("fail", audit.getAi_verdict());
        verify(contents, never()).update(any());
    }

    @Test
    void staleVersionCannotOverwriteHumanQueue() {
        when(audits.findByIdForUpdate(12)).thenReturn(pendingAudit());
        when(contents.findByIdForUpdate(34)).thenReturn(reviewingPpt());
        assertThrows(RuntimeException.class, () -> service.acceptAiReview(12,
                new AiReviewResultDTO(1, "science", "pass", 100, "", "test", List.of(), List.of())));
        verify(audits, never()).saveAiReview(any());
    }

    @Test
    void humanCanRetractAutoApprovedPpt() {
        Adm_Audit audit = pendingAudit();
        audit.setStatus("processed");
        audit.setAction("ai_approve");
        Com_Content content = reviewingPpt();
        content.setStatus("public");
        when(audits.findByIdForUpdate(12)).thenReturn(audit);
        when(contents.findByIdForUpdate(34)).thenReturn(content);
        AuditDTO decision = new AuditDTO();
        decision.setAction("reject");
        decision.setComment("人工抽查发现内容错误");
        service.makeDecision(12, decision, 7);
        assertEquals("offline", content.getStatus());
        assertEquals("reject", audit.getAction());
        assertEquals(7, audit.getHandler_id());
        verify(audits).process(audit);
    }

    @Test
    void passingAtSixtyCanBeSelectedForSpotCheck() {
        Adm_Audit audit = pendingAudit();
        when(audits.findByIdForUpdate(12)).thenReturn(audit);
        when(audits.saveAiReview(any())).thenReturn(1);
        when(contents.findByIdForUpdate(34)).thenReturn(reviewingPpt());
        when(sampling.selected()).thenReturn(true);
        service.acceptAiReview(12, new AiReviewResultDTO(2, "science", "pass", 60,
                "通过", "test", completeChecks(), List.of()));
        assertEquals("pending", audit.getStatus());
        assertTrue(audit.getAi_report().contains("\"spot_check\":true"));
        verify(contents, never()).update(any());
    }

    @Test
    void completedLowScoreReviewIsRejectedAndCanBeOverturned() throws Exception {
        Adm_Audit audit = pendingAudit();
        Com_Content content = reviewingPpt();
        when(audits.findByIdForUpdate(12)).thenReturn(audit);
        when(audits.saveAiReview(any())).thenReturn(1);
        when(contents.findByIdForUpdate(34)).thenReturn(content);
        service.acceptAiReview(12, new AiReviewResultDTO(2, "science", "pass", 59,
                "内容质量不足", "test", completeChecks(), List.of()));
        assertEquals("ai_reject", audit.getAction());
        assertEquals("processed", audit.getStatus());
        assertEquals("offline", content.getStatus());
        verifyNoInteractions(sampling);
        AuditDTO decision = new AuditDTO();
        decision.setAction("approve");
        service.makeDecision(12, decision, 7);
        assertEquals("public", content.getStatus());
        assertFalse(new ObjectMapper().readTree(audit.getAi_report()).path("human_review").path("agrees_with_ai").asBoolean());
    }

    @Test
    void unsampledSkillCanPublishAtSixty() {
        Adm_Audit audit = pendingAudit();
        audit.setTarget_type("skill");
        Com_Content content = reviewingPpt();
        content.setContent_type("skill");
        when(audits.findByIdForUpdate(12)).thenReturn(audit);
        when(audits.saveAiReview(any())).thenReturn(1);
        when(contents.findByIdForUpdate(34)).thenReturn(content);
        when(sampling.selected()).thenReturn(false);
        service.acceptAiReview(12, new AiReviewResultDTO(2, "arts", "pass", 60,
                "通过", "test", completeChecks(), List.of()));
        assertEquals("ai_approve", audit.getAction());
        assertEquals("public", content.getStatus());
    }

    @Test
    void modelErrorNeverTriggersScoreBasedRejection() {
        Adm_Audit audit = pendingAudit();
        when(audits.findByIdForUpdate(12)).thenReturn(audit);
        when(audits.saveAiReview(any())).thenReturn(1);
        when(contents.findByIdForUpdate(34)).thenReturn(reviewingPpt());
        service.acceptAiReview(12, new AiReviewResultDTO(2, "science", "error", 0,
                "服务异常", "test", completeChecks(), List.of()));
        assertEquals("pending", audit.getStatus());
        assertNull(audit.getAction());
        verify(contents, never()).update(any());
    }

    @Test
    void humanCannotDecideForAnOlderVersion() {
        Adm_Audit audit = pendingAudit();
        audit.setAi_report("{\"content_version\":1}");
        when(audits.findByIdForUpdate(12)).thenReturn(audit);
        when(contents.findByIdForUpdate(34)).thenReturn(reviewingPpt());
        AuditDTO decision = new AuditDTO();
        decision.setAction("approve");
        assertThrows(IllegalStateException.class, () -> service.makeDecision(12, decision, 7));
        verify(contents, never()).update(any());
    }

    @Test
    void oldAutoApprovalCannotRetractNewSubmissionWithSameVersionNumber() {
        Adm_Audit old = pendingAudit();
        old.setStatus("processed");
        old.setAction("ai_approve");
        old.setAi_report("{\"content_version\":2}");
        Adm_Audit latest = pendingAudit();
        latest.setId(13);
        Com_Content content = reviewingPpt();
        content.setStatus("public");
        when(audits.findByIdForUpdate(12)).thenReturn(old);
        when(audits.findLatestSubmissionAudit(34)).thenReturn(latest);
        when(contents.findByIdForUpdate(34)).thenReturn(content);
        AuditDTO decision = new AuditDTO();
        decision.setAction("reject");
        decision.setComment("旧稿问题");
        assertThrows(IllegalStateException.class, () -> service.makeDecision(12, decision, 7));
        verify(contents, never()).update(any());
    }

    @Test
    void moderationMapperSupportsAiFilterAndReportWrite() throws Exception {
        String resource = "edu/zstu/mapper/AdmAuditMapper.xml";
        Configuration configuration = new Configuration();
        try (InputStream input = getClass().getClassLoader().getResourceAsStream(resource)) {
            assertNotNull(input);
            new XMLMapperBuilder(input, configuration, resource, configuration.getSqlFragments()).parse();
        }
        Map<String, Object> params = Map.of("auditType", "audit", "aiVerdict", "pass");
        String sql = configuration.getMappedStatement("edu.zstu.mapper.AdmAuditMapper.searchAudits")
                .getBoundSql(params).getSql();
        assertTrue(sql.contains("ai_verdict = ?"));
        assertTrue(configuration.getMappedStatement("edu.zstu.mapper.AdmAuditMapper.saveAiReview")
                .getBoundSql(pendingAudit()).getSql().contains("ai_report = ?"));
    }

    @Test
    void internalApiOnlyTreatsStaleTaskAsConflict() {
        var moderation = mock(edu.zstu.service.AdminModerationService.class);
        var controller = new CommunityReviewInternalController(moderation);
        when(moderation.getAiReviewPayload(12)).thenThrow(new IllegalStateException("任务已过期"));
        assertEquals(409, controller.payload(12).getCode());
        when(moderation.getAiReviewPayload(13)).thenThrow(new RuntimeException("数据库不可用"));
        assertThrows(RuntimeException.class, () -> controller.payload(13));
    }
}
