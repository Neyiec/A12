package edu.zstu.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import edu.zstu.dto.AuditDTO;
import edu.zstu.dto.AiReviewResultDTO;
import edu.zstu.dto.RecommendationDTO;
import edu.zstu.entity.Adm_Audit;
import edu.zstu.entity.Com_Content;
import edu.zstu.entity.Sys_User;
import edu.zstu.mapper.AdmAuditMapper;
import edu.zstu.mapper.ComContentMapper;
import edu.zstu.mapper.SysUserMapper;
import edu.zstu.service.AdminModerationService;
import edu.zstu.service.BusinessLogService;
import edu.zstu.service.CommunityReviewSampling;
import edu.zstu.service.ResourceIndexEventPublisher;
import edu.zstu.utils.PageResult;
import edu.zstu.utils.RedisCacheUtil;
import edu.zstu.vo.AuditVO;
import edu.zstu.vo.ContentVO;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.time.LocalDateTime;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Service
public class AdminModerationServiceImpl implements AdminModerationService {
    private static final Set<String> REVIEW_CHECKS = Set.of(
            "政治敏感", "广告导流", "侵权嫌疑", "内容质量");

    private final AdmAuditMapper auditMapper;
    private final ComContentMapper contentMapper;
    private final SysUserMapper userMapper;
    private final BusinessLogService businessLogService;
    private final RedisCacheUtil redisCacheUtil;
    private final ObjectMapper objectMapper;
    private final ResourceIndexEventPublisher indexEvents;
    private final CommunityReviewSampling reviewSampling;

    public AdminModerationServiceImpl(AdmAuditMapper auditMapper, ComContentMapper contentMapper,
                                      SysUserMapper userMapper, BusinessLogService businessLogService,
                                      RedisCacheUtil redisCacheUtil, ObjectMapper objectMapper,
                                      ResourceIndexEventPublisher indexEvents, CommunityReviewSampling reviewSampling) {
        this.auditMapper = auditMapper;
        this.contentMapper = contentMapper;
        this.userMapper = userMapper;
        this.businessLogService = businessLogService;
        this.redisCacheUtil = redisCacheUtil;
        this.objectMapper = objectMapper;
        this.indexEvents = indexEvents;
        this.reviewSampling = reviewSampling;
    }

    @Override
    public PageResult<AuditVO> listModerationTasks(String status, String targetType, Integer handlerId, String aiVerdict, String aiDomain, int page, int size) {
        log.info("listModerationTasks called");
        PageHelper.startPage(page, size);
        List<Adm_Audit> list = auditMapper.searchAudits("audit", status, targetType, handlerId, aiVerdict, aiDomain);
        PageInfo<Adm_Audit> info = new PageInfo<>(list);
        return toAuditPageResult(info, page, size);
    }

    @Override
    public AuditVO getModerationTask(Integer id) {
        log.info("getModerationTask id={}", id);
        Adm_Audit audit = auditMapper.findById(id);
        if (audit == null || !"audit".equals(audit.getAudit_type())) {
            throw new RuntimeException("Review task not found");
        }
        return toAuditVO(audit);
    }

    @Override
    public Map<String, Object> getModerationMetrics() {
        Map<String, Object> metrics = new LinkedHashMap<>(auditMapper.moderationMetrics());
        long comparable = ((Number) metrics.getOrDefault("comparable", 0)).longValue();
        long agreements = ((Number) metrics.getOrDefault("agreements", 0)).longValue();
        metrics.put("agreement_rate", comparable == 0 ? null : (double) agreements / comparable);
        metrics.put("sample_rate", 0.10);
        metrics.put("score_threshold", 60);
        return metrics;
    }

    @Override
    public ContentVO getModerationContent(Integer id) {
        Com_Content content = contentMapper.findById(id);
        if (content == null) throw new RuntimeException("投稿内容不存在");
        if (auditMapper.findByTarget(content.getContent_type(), id).stream()
                .noneMatch(audit -> "audit".equals(audit.getAudit_type()))) {
            throw new RuntimeException("该内容没有投稿审核任务");
        }
        ContentVO vo = new ContentVO();
        BeanUtil.copyProperties(content, vo);
        return vo;
    }

    @Override
    public Map<String, Object> getAiReviewPayload(Integer auditId) {
        Adm_Audit audit = auditMapper.findById(auditId);
        if (audit == null || !"audit".equals(audit.getAudit_type()) || !"pending".equals(audit.getStatus())
                || audit.getAi_verdict() != null) {
            throw new IllegalStateException("审核任务已失效");
        }
        Com_Content content = contentMapper.findById(audit.getTarget_id());
        if (content == null || !"reviewing".equals(content.getStatus())
                || !Objects.equals(content.getContent_type(), audit.getTarget_type())) {
            throw new IllegalStateException("课件已不是待审核状态");
        }
        requireReviewedVersion(audit, content);
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("audit_id", auditId);
        payload.put("content_version", content.getVersion());
        payload.put("content_type", content.getContent_type());
        payload.put("input_variables", content.getInput_variables());
        payload.put("title", content.getTitle());
        payload.put("description", content.getDescription());
        payload.put("subject", content.getSubject());
        payload.put("grade", content.getGrade());
        payload.put("lesson_type", content.getLesson_type());
        payload.put("license", content.getLicense());
        payload.put("content_data", content.getContent_data());
        return payload;
    }

    @Override
    @Transactional
    public void acceptAiReview(Integer auditId, AiReviewResultDTO result) {
        Adm_Audit audit = auditMapper.findByIdForUpdate(auditId);
        if (audit == null || !"audit".equals(audit.getAudit_type())) throw new RuntimeException("审核任务不存在");
        if (!"pending".equals(audit.getStatus()) || audit.getAi_verdict() != null) return;
        Com_Content content = contentMapper.findByIdForUpdate(audit.getTarget_id());
        if (content == null || !"reviewing".equals(content.getStatus())
                || !Objects.equals(content.getContent_type(), audit.getTarget_type())
                || result == null || !Objects.equals(result.content_version(), content.getVersion())) {
            throw new IllegalStateException("课件版本或审核状态已变化，忽略过期的 AI 结果");
        }
        requireReviewedVersion(audit, content);
        String domain = Set.of("arts", "science", "engineering").contains(String.valueOf(result.domain()))
                ? result.domain() : "unknown";
        String verdict = Set.of("pass", "review", "fail", "error").contains(String.valueOf(result.verdict()))
                ? result.verdict() : "review";
        int score = Math.max(0, Math.min(100, result.score() == null ? 0 : result.score()));
        boolean completeChecks = result.checks() != null && result.checks().size() == REVIEW_CHECKS.size()
                && result.checks().stream().allMatch(check -> check != null
                        && Set.of("pass", "review", "fail").contains(String.valueOf(check.get("status")))
                        && check.get("evidence") instanceof String evidence && !evidence.isBlank())
                && result.checks().stream().map(check -> check.get("name")).collect(java.util.stream.Collectors.toSet())
                        .equals(REVIEW_CHECKS);
        boolean validReport = completeChecks && result.score() != null && result.score() >= 0 && result.score() <= 100
                && !"error".equals(verdict) && result.summary() != null && !result.summary().isBlank();
        boolean checksPassed = completeChecks && result.checks().stream().allMatch(check -> "pass".equals(check.get("status")));
        boolean noFindings = result.findings() != null && result.findings().isEmpty();
        boolean autoReject = validReport && score < 60;
        if (autoReject) verdict = "fail";
        boolean autoEligible = validReport && "pass".equals(verdict) && score >= 60 && checksPassed && noFindings
                && !"unknown".equals(domain);
        if ("pass".equals(verdict) && !autoEligible) verdict = "review";
        boolean spotCheck = autoEligible && reviewSampling.selected();
        Map<String, Object> report = new LinkedHashMap<>();
        report.put("summary", result.summary() == null ? "" : result.summary());
        report.put("checks", result.checks() == null ? List.of() : result.checks());
        report.put("findings", result.findings() == null ? List.of() : result.findings());
        report.put("content_version", content.getVersion());
        report.put("spot_check", spotCheck);
        report.put("policy_version", "score60-sample10-v1");
        report.put("auto_reject", autoReject);
        report.put("sample_rate", 0.10);
        report.put("score_threshold", 60);
        try {
            String json = objectMapper.writeValueAsString(report);
            if (json.length() > 40000) throw new RuntimeException("AI 审核报告过长");
            audit.setAi_report(json);
        } catch (JsonProcessingException e) { throw new RuntimeException("AI 审核报告无法保存", e); }
        audit.setAi_domain(domain);
        audit.setAi_verdict(verdict);
        audit.setAi_score(score);
        audit.setAi_model(result.model() == null ? "" : result.model().substring(0, Math.min(100, result.model().length())));
        boolean autoPublish = autoEligible && !spotCheck;
        boolean automaticallyProcessed = autoPublish || autoReject;
        audit.setAction(autoPublish ? "ai_approve" : autoReject ? "ai_reject" : null);
        audit.setComment(autoReject ? "AI 评分 " + score + "/100，低于 60 分自动驳回。"
                + result.summary().substring(0, Math.min(350, result.summary().length()))
                + " 可联系审核员复核。" : null);
        audit.setStatus(automaticallyProcessed ? "processed" : "pending");
        audit.setProcessed_at(automaticallyProcessed ? LocalDateTime.now() : null);
        if (auditMapper.saveAiReview(audit) != 1) throw new RuntimeException("AI 审核结果保存冲突");
        if (automaticallyProcessed) {
            content.setStatus(autoPublish ? "public" : "offline");
            contentMapper.update(content);
            if ("ppt".equals(content.getContent_type())) {
                indexEvents.publish(autoPublish ? "sync" : "delete", "community", content.getId(), false);
            }
            evictContentCache(content.getId());
        }
        businessLogService.record("audit", "ai_moderation",
                autoPublish ? "auto_approve" : autoReject ? "auto_reject" : "human_review_required",
                "audit", auditId, Map.of("content_id", content.getId(), "domain", domain, "verdict", verdict,
                        "content_version", content.getVersion(), "spot_check", spotCheck));
    }

    @Override
    public Map<String, Object> rebuildCommunityIndex(Integer afterId, Integer limit) {
        int cursor = Math.max(0, afterId == null ? 0 : afterId);
        int batchSize = Math.max(1, Math.min(200, limit == null ? 100 : limit));
        List<Com_Content> batch = contentMapper.findPptIndexCandidates(cursor, batchSize);
        int published = 0;
        for (Com_Content content : batch) {
            boolean eligible = "public".equals(content.getStatus()) && content.getLicense() != null
                    && content.getLicense().startsWith("CC BY");
            indexEvents.publish(eligible ? "sync" : "delete", "community", content.getId(), false);
            cursor = content.getId();
            published++;
        }
        return Map.of("processed", published, "next_cursor", cursor, "has_more", batch.size() == batchSize);
    }

    @Override
    public Map<String, Object> rebuildCommunityItemIndex(Integer id) {
        Com_Content content = contentMapper.findById(id);
        if (content == null || !"ppt".equals(content.getContent_type())) {
            throw new RuntimeException("社区 PPT 不存在");
        }
        boolean eligible = "public".equals(content.getStatus()) && content.getLicense() != null
                && content.getLicense().startsWith("CC BY");
        String action = eligible ? "sync" : "delete";
        indexEvents.publish(action, "community", id, false);
        return Map.of("resource_id", id, "status", "queued", "action", action);
    }

    @Override
    @Transactional
    public void makeDecision(Integer id, AuditDTO dto, Integer adminId) {
        log.info("makeDecision id={}, action={}", id, dto == null ? null : dto.getAction());
        Adm_Audit audit = auditMapper.findByIdForUpdate(id);
        if (audit == null || !"audit".equals(audit.getAudit_type())) {
            throw new RuntimeException("Review task not found");
        }
        boolean automaticDecision = Set.of("ai_approve", "ai_reject").contains(Objects.toString(audit.getAction(), ""));
        if (!"pending".equals(audit.getStatus()) && !("processed".equals(audit.getStatus()) && automaticDecision)) {
            throw new RuntimeException("Review task has already been processed");
        }
        String action = normalizeReviewAction(dto == null ? null : dto.getAction());
        Com_Content content = contentMapper.findByIdForUpdate(audit.getTarget_id());
        if (content == null) throw new RuntimeException("Related submission content not found");
        boolean postPublishCheck = "ai_approve".equals(audit.getAction());
        String expectedStatus = postPublishCheck ? "public" : "ai_reject".equals(audit.getAction()) ? "offline" : "reviewing";
        if (!expectedStatus.equals(content.getStatus())) {
            throw new IllegalStateException("投稿状态已变化，请刷新审核列表");
        }
        if (!Objects.equals(content.getContent_type(), audit.getTarget_type())) {
            throw new RuntimeException("Review task target does not match content type");
        }
        requireReviewedVersion(audit, content);
        String comment = dto.getComment() == null ? "" : dto.getComment().strip();
        if (!"approve".equals(action) && comment.isBlank()) {
            throw new IllegalArgumentException("请填写驳回或退回修改的原因");
        }
        if (comment.length() > 500) throw new IllegalArgumentException("审核意见最多 500 字");

        String newStatus = switch (action) {
            case "approve" -> "public";
            case "reject" -> "offline";
            case "rework" -> "draft";
            default -> throw new RuntimeException("Unsupported review action: " + action);
        };
        content.setStatus(newStatus);
        contentMapper.update(content);
        if ("ppt".equals(content.getContent_type())) {
            indexEvents.publish("public".equals(newStatus) ? "sync" : "delete", "community", content.getId(), false);
        }

        audit.setHandler_id(adminId);
        recordHumanComparison(audit, action, adminId);
        audit.setAction(action);
        audit.setComment(comment);
        audit.setStatus("processed");
        auditMapper.process(audit);
        evictContentCache(content.getId());
        businessLogService.record("audit", "admin_moderation", "make_decision", "audit", id,
                Map.of("action", action, "content_id", content.getId(), "new_status", newStatus,
                        "content_version", content.getVersion(), "reviewer_id", adminId,
                        "ai_verdict", Objects.toString(audit.getAi_verdict(), ""),
                        "post_publish_check", postPublishCheck, "comment", comment));
    }

    @Override
    @Transactional
    public ContentVO updateItemStatus(Integer id, String status) {
        log.info("updateItemStatus id={}, status={}", id, status);
        Com_Content content = contentMapper.findByIdForUpdate(id);
        if (content == null) throw new RuntimeException("Community content not found");

        String dbStatus = normalizeContentStatus(status);
        content.setStatus(dbStatus);
        contentMapper.update(content);
        if ("ppt".equals(content.getContent_type())) {
            indexEvents.publish("public".equals(dbStatus) ? "sync" : "delete", "community", content.getId(), false);
        }
        evictContentCache(id);
        businessLogService.record("operation", "admin_moderation", "update_item_status", "content", id,
                Map.of("status", status, "db_status", dbStatus));

        ContentVO vo = new ContentVO();
        BeanUtil.copyProperties(content, vo);
        return vo;
    }

    @Override
    @Transactional
    public ContentVO updateRecommendation(Integer id, RecommendationDTO dto) {
        log.info("updateRecommendation id={}", id);
        Com_Content content = contentMapper.findByIdForUpdate(id);
        if (content == null) throw new RuntimeException("Community content not found");
        int isTop = dto == null ? 0 : dto.getIs_top();
        if (isTop != 0 && isTop != 1) {
            throw new RuntimeException("is_top must be 0 or 1");
        }
        content.setIs_top(isTop);
        contentMapper.update(content);
        evictContentCache(id);
        businessLogService.record("operation", "admin_moderation", "update_recommendation", "content", id,
                Map.of("is_top", isTop));

        ContentVO vo = new ContentVO();
        BeanUtil.copyProperties(content, vo);
        return vo;
    }

    @Override
    public PageResult<AuditVO> listReports(String status, int page, int size) {
        log.info("listReports called");
        PageHelper.startPage(page, size);
        List<Adm_Audit> list = auditMapper.searchAudits("report", status, null, null, null, null);
        PageInfo<Adm_Audit> info = new PageInfo<>(list);
        return toAuditPageResult(info, page, size);
    }

    @Override
    public AuditVO getReport(Integer id) {
        log.info("getReport id={}", id);
        Adm_Audit report = auditMapper.findById(id);
        if (report == null || !"report".equals(report.getAudit_type())) {
            throw new RuntimeException("Report not found");
        }
        return toAuditVO(report);
    }

    @Override
    @Transactional
    public void resolveReport(Integer id, AuditDTO dto, Integer adminId) {
        log.info("resolveReport id={}, action={}", id, dto == null ? null : dto.getAction());
        Adm_Audit report = auditMapper.findByIdForUpdate(id);
        if (report == null || !"report".equals(report.getAudit_type())) {
            throw new RuntimeException("Report not found");
        }
        if (!"pending".equals(report.getStatus())) {
            throw new RuntimeException("Report has already been processed");
        }
        String action = normalizeReportAction(dto == null ? null : dto.getAction());
        Com_Content content = contentMapper.findByIdForUpdate(report.getTarget_id());
        if (content == null) throw new RuntimeException("Reported content not found");

        if (List.of("approve", "offline").contains(action)) {
            content.setStatus("offline");
            contentMapper.update(content);
            if ("ppt".equals(content.getContent_type())) indexEvents.publish("delete", "community", content.getId(), false);
            evictContentCache(content.getId());
        } else if ("restore".equals(action)) {
            content.setStatus("public");
            contentMapper.update(content);
            if ("ppt".equals(content.getContent_type())) indexEvents.publish("sync", "community", content.getId(), false);
            evictContentCache(content.getId());
        }

        report.setHandler_id(adminId);
        report.setAction(action);
        report.setComment(dto == null ? null : dto.getComment());
        report.setStatus("processed");
        auditMapper.process(report);
        businessLogService.record("audit", "admin_moderation", "resolve_report", "report", id,
                Map.of("action", action, "content_id", content.getId(), "content_status", content.getStatus()));
    }

    // ==================== 内部辅助 ====================


    private void recordHumanComparison(Adm_Audit audit, String action, int reviewerId) {
        try {
            var report = audit.getAi_report() == null
                    ? objectMapper.createObjectNode() : objectMapper.readTree(audit.getAi_report());
            if (!(report instanceof com.fasterxml.jackson.databind.node.ObjectNode object)) {
                throw new IllegalStateException("审核报告格式无效");
            }
            var human = object.putObject("human_review");
            human.put("action", action);
            human.put("reviewer_id", reviewerId);
            human.put("reviewed_at", LocalDateTime.now().toString());
            boolean comparable = Set.of("pass", "fail").contains(Objects.toString(audit.getAi_verdict(), ""))
                    && Set.of("approve", "reject").contains(action);
            if (comparable) {
                human.put("agrees_with_ai", ("pass".equals(audit.getAi_verdict()) && "approve".equals(action))
                        || ("fail".equals(audit.getAi_verdict()) && "reject".equals(action)));
            }
            audit.setAi_report(objectMapper.writeValueAsString(object));
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("人工复核记录无法保存", e);
        }
    }

    private void requireReviewedVersion(Adm_Audit audit, Com_Content content) {
        Adm_Audit latest = auditMapper.findLatestSubmissionAudit(content.getId());
        if (latest != null && !Objects.equals(latest.getId(), audit.getId())) {
            throw new IllegalStateException("已有更新的投稿审核单，请刷新审核列表");
        }
        if (audit.getAi_report() == null) return; // 历史人工待审记录没有版本字段。
        try {
            var version = objectMapper.readTree(audit.getAi_report()).path("content_version");
            if (!version.isMissingNode() && (!version.isIntegralNumber() || version.asInt() != content.getVersion())) {
                throw new IllegalStateException("投稿版本已变化，请刷新审核列表");
            }
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("审核记录版本无法读取", e);
        }
    }

    private String normalizeReviewAction(String action) {
        if (action == null || action.isBlank()) {
            throw new RuntimeException("action is required");
        }
        if (!List.of("approve", "reject", "rework").contains(action)) {
            throw new RuntimeException("Unsupported review action: " + action);
        }
        return action;
    }

    private String normalizeReportAction(String action) {
        if (action == null || action.isBlank()) {
            throw new RuntimeException("action is required");
        }
        if (!List.of("approve", "offline", "ignore", "reject", "restore").contains(action)) {
            throw new RuntimeException("Unsupported report action: " + action);
        }
        return action;
    }

    private String normalizeContentStatus(String status) {
        if (status == null || status.isBlank()) {
            throw new RuntimeException("status is required");
        }
        return switch (status) {
            case "published", "public" -> "public";
            case "unpublished", "disabled", "offline" -> "offline";
            case "reviewing" -> "reviewing";
            case "draft" -> "draft";
            default -> throw new RuntimeException("Unsupported status: " + status);
        };
    }

    /**
     * 实体转 VO 并富化关联信息（关联内容标题 + 提交者），供列表与详情共用
     */
    private AuditVO toAuditVO(Adm_Audit a) {
        AuditVO vo = new AuditVO();
        BeanUtil.copyProperties(a, vo);
        enrichAuditTarget(a, vo);
        return vo;
    }

    /**
     * 富化审核 VO：补齐关联内容标题与提交者显示名，解决列表只显示裸 target_id 的缺口
     * 内容或用户已删除时对应字段保持为空，不阻断列表返回
     */
    private void enrichAuditTarget(Adm_Audit audit, AuditVO vo) {
        Com_Content content = contentMapper.findById(audit.getTarget_id());
        if (content == null) {
            return;
        }
        vo.setContent_title(content.getTitle());
        vo.setSubmitter_id(content.getAuthor_id());
        Sys_User author = userMapper.findById(content.getAuthor_id());
        if (author != null) {
            boolean hasRealName = author.getReal_name() != null && !author.getReal_name().isBlank();
            vo.setSubmitter_name(hasRealName ? author.getReal_name() : author.getUsername());
        }
    }

    private PageResult<AuditVO> toAuditPageResult(PageInfo<Adm_Audit> info, int page, int size) {
        List<AuditVO> records = info.getList().stream().map(this::toAuditVO).toList();
        PageResult<AuditVO> r = new PageResult<>();
        r.setTotal(info.getTotal()); r.setPage(page); r.setSize(size); r.setRecords(records);
        return r;
    }

    private void evictContentCache(Integer id) {
        redisCacheUtil.delete("community:item:" + id);
        redisCacheUtil.deleteByPattern("community:public:*");
        redisCacheUtil.deleteByPattern("community:favorites:*");
        redisCacheUtil.deleteByPattern("community:recent:*");
    }
}
