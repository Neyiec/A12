package edu.zstu.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import edu.zstu.dto.AuditDTO;
import edu.zstu.dto.RecommendationDTO;
import edu.zstu.entity.Adm_Audit;
import edu.zstu.entity.Com_Content;
import edu.zstu.mapper.AdmAuditMapper;
import edu.zstu.mapper.ComContentMapper;
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
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Service
public class AdminModerationServiceImpl implements AdminModerationService {

    private final AdmAuditMapper auditMapper;
    private final ComContentMapper contentMapper;
    private final BusinessLogService businessLogService;
    private final RedisCacheUtil redisCacheUtil;

    public AdminModerationServiceImpl(AdmAuditMapper auditMapper, ComContentMapper contentMapper,
                                      BusinessLogService businessLogService, RedisCacheUtil redisCacheUtil) {
        this.auditMapper = auditMapper;
        this.contentMapper = contentMapper;
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
        log.info("getModerationTask called");
        Adm_Audit a = auditMapper.findById(id);
        if (a == null) throw new RuntimeException("审核任务不存在");
        return toAuditVO(a);
    }

    @Override
    @Transactional
    public void makeDecision(Integer id, AuditDTO dto, Integer adminId) {
        log.info("makeDecision called");
        Adm_Audit audit = auditMapper.findById(id);
        if (audit == null) throw new RuntimeException("审核任务不存在");

        audit.setHandler_id(adminId);
        audit.setAction(dto.getAction());
        audit.setComment(dto.getComment());
        audit.setStatus("processed");
        auditMapper.process(audit);

        // 同步更新投稿内容状态
        Com_Content content = contentMapper.findById(audit.getTarget_id());
        if (content == null) throw new RuntimeException("关联投稿内容不存在");

        String newStatus;
        switch (dto.getAction()) {
            case "approve": newStatus = "public"; break;
            case "reject":  newStatus = "offline"; break;
            case "rework":  newStatus = "draft"; break;
            default: throw new RuntimeException("无效审核动作: " + dto.getAction());
        }
        content.setStatus(newStatus);
        contentMapper.update(content);
        evictContentCache(content.getId());
        businessLogService.record("audit", "admin_moderation", "make_decision", "audit", id,
                Map.of("action", dto.getAction(), "content_id", content.getId(), "new_status", newStatus));
    }

    @Override
    @Transactional
    public ContentVO updateItemStatus(Integer id, String status) {
        log.info("updateItemStatus called");
        Com_Content c = contentMapper.findById(id);
        if (c == null) throw new RuntimeException("社区内容不存在");

        String dbStatus;
        switch (status) {
            case "published":   dbStatus = "public"; break;
            case "unpublished": dbStatus = "offline"; break;
            case "disabled":    dbStatus = "offline"; break;
            default: throw new RuntimeException("无效状态值: " + status);
        }
        c.setStatus(dbStatus);
        contentMapper.update(c);
        evictContentCache(id);
        businessLogService.record("operation", "admin_moderation", "update_item_status", "content", id,
                Map.of("status", status, "db_status", dbStatus));

        ContentVO vo = new ContentVO();
        BeanUtil.copyProperties(c, vo);
        return vo;
    }

    @Override
    @Transactional
    public ContentVO updateRecommendation(Integer id, RecommendationDTO dto) {
        log.info("updateRecommendation called");
        Com_Content c = contentMapper.findById(id);
        if (c == null) throw new RuntimeException("社区内容不存在");

        c.setIs_top(dto.getIs_top());
        contentMapper.update(c);
        evictContentCache(id);
        businessLogService.record("operation", "admin_moderation", "update_recommendation", "content", id,
                Map.of("is_top", dto.getIs_top()));

        ContentVO vo = new ContentVO();
        BeanUtil.copyProperties(c, vo);
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
        log.info("getReport called");
        Adm_Audit a = auditMapper.findById(id);
        if (a == null) throw new RuntimeException("举报不存在");
        return toAuditVO(a);
    }

    @Override
    @Transactional
    public void resolveReport(Integer id, AuditDTO dto, Integer adminId) {
        log.info("resolveReport called");
        Adm_Audit report = auditMapper.findById(id);
        if (report == null) throw new RuntimeException("举报不存在");

        report.setHandler_id(adminId);
        report.setAction(dto.getAction());
        report.setComment(dto.getComment());
        report.setStatus("processed");
        auditMapper.process(report);
        businessLogService.record("audit", "admin_moderation", "resolve_report", "report", id,
                Map.of("action", dto.getAction()));
    }

    // ==================== 内部辅助 ====================

    private AuditVO toAuditVO(Adm_Audit a) {
        AuditVO vo = new AuditVO();
        BeanUtil.copyProperties(a, vo);
        return vo;
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
