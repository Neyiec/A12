package edu.zstu.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import edu.zstu.dto.AuditDTO;
import edu.zstu.dto.RecommendationDTO;
import edu.zstu.entity.Adm_Audit;
import edu.zstu.entity.Com_Content;
import edu.zstu.entity.Sys_User;
import edu.zstu.mapper.AdmAuditMapper;
import edu.zstu.mapper.ComContentMapper;
import edu.zstu.mapper.SysUserMapper;
import edu.zstu.service.AdminModerationService;
import edu.zstu.service.BusinessLogService;
import edu.zstu.utils.PageResult;
import edu.zstu.utils.RedisCacheUtil;
import edu.zstu.vo.AuditVO;
import edu.zstu.vo.ContentVO;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Map;
import java.util.Objects;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Service
public class AdminModerationServiceImpl implements AdminModerationService {

    private final AdmAuditMapper auditMapper;
    private final ComContentMapper contentMapper;
    private final SysUserMapper userMapper;
    private final BusinessLogService businessLogService;
    private final RedisCacheUtil redisCacheUtil;

    public AdminModerationServiceImpl(AdmAuditMapper auditMapper, ComContentMapper contentMapper,
                                      SysUserMapper userMapper, BusinessLogService businessLogService,
                                      RedisCacheUtil redisCacheUtil) {
        this.auditMapper = auditMapper;
        this.contentMapper = contentMapper;
        this.userMapper = userMapper;
        this.businessLogService = businessLogService;
        this.redisCacheUtil = redisCacheUtil;
    }

    @Override
    public PageResult<AuditVO> listModerationTasks(String status, String targetType, Integer handlerId, int page, int size) {
        log.info("listModerationTasks called");
        PageHelper.startPage(page, size);
        List<Adm_Audit> list = auditMapper.searchAudits("audit", status, targetType, handlerId);
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
    @Transactional
    public void makeDecision(Integer id, AuditDTO dto, Integer adminId) {
        log.info("makeDecision id={}, action={}", id, dto == null ? null : dto.getAction());
        Adm_Audit audit = auditMapper.findById(id);
        if (audit == null || !"audit".equals(audit.getAudit_type())) {
            throw new RuntimeException("Review task not found");
        }
        if (!"pending".equals(audit.getStatus())) {
            throw new RuntimeException("Review task has already been processed");
        }
        String action = normalizeReviewAction(dto == null ? null : dto.getAction());
        Com_Content content = contentMapper.findById(audit.getTarget_id());
        if (content == null) throw new RuntimeException("Related submission content not found");
        if (!Objects.equals(content.getContent_type(), audit.getTarget_type())) {
            throw new RuntimeException("Review task target does not match content type");
        }

        String newStatus = switch (action) {
            case "approve" -> "public";
            case "reject" -> "offline";
            case "rework" -> "draft";
            default -> throw new RuntimeException("Unsupported review action: " + action);
        };
        content.setStatus(newStatus);
        contentMapper.update(content);

        audit.setHandler_id(adminId);
        audit.setAction(action);
        audit.setComment(dto == null ? null : dto.getComment());
        audit.setStatus("processed");
        auditMapper.process(audit);
        evictContentCache(content.getId());
        businessLogService.record("audit", "admin_moderation", "make_decision", "audit", id,
                Map.of("action", action, "content_id", content.getId(), "new_status", newStatus));
    }

    /**
     * 管理员读取审核目标社区内容完整详情（含待审核/未公开稿件，不过滤状态），用于审核抽屉预览。
     */
    @Override
    public ContentVO getModerationContent(Integer id) {
        log.info("getModerationContent id={}", id);
        Com_Content content = contentMapper.findById(id);
        if (content == null) throw new RuntimeException("Community content not found");
        ContentVO vo = new ContentVO();
        BeanUtil.copyProperties(content, vo);
        return vo;
    }

    @Override
    @Transactional
    public ContentVO updateItemStatus(Integer id, String status) {
        log.info("updateItemStatus id={}, status={}", id, status);
        Com_Content content = contentMapper.findById(id);
        if (content == null) throw new RuntimeException("Community content not found");

        String dbStatus = normalizeContentStatus(status);
        content.setStatus(dbStatus);
        contentMapper.update(content);
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
        Com_Content content = contentMapper.findById(id);
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
        List<Adm_Audit> list = auditMapper.searchAudits("report", status, null, null);
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
        Adm_Audit report = auditMapper.findById(id);
        if (report == null || !"report".equals(report.getAudit_type())) {
            throw new RuntimeException("Report not found");
        }
        if (!"pending".equals(report.getStatus())) {
            throw new RuntimeException("Report has already been processed");
        }
        String action = normalizeReportAction(dto == null ? null : dto.getAction());
        Com_Content content = contentMapper.findById(report.getTarget_id());
        if (content == null) throw new RuntimeException("Reported content not found");

        if (List.of("approve", "offline").contains(action)) {
            content.setStatus("offline");
            contentMapper.update(content);
            evictContentCache(content.getId());
        } else if ("restore".equals(action)) {
            content.setStatus("public");
            contentMapper.update(content);
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
