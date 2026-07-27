package edu.zstu.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import edu.zstu.dto.*;
import edu.zstu.entity.Adm_Audit;
import edu.zstu.entity.Com_Content;
import edu.zstu.entity.Com_Interaction;
import edu.zstu.mapper.AdmAuditMapper;
import edu.zstu.mapper.ComContentMapper;
import edu.zstu.mapper.ComInteractionMapper;
import edu.zstu.service.CommunityService;
import edu.zstu.service.ProjectService;
import edu.zstu.utils.PageResult;
import edu.zstu.vo.AuditVO;
import edu.zstu.vo.ContentVO;
import edu.zstu.vo.ProjectVO;
import edu.zstu.vo.RecentViewVO;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;

@Service
public class CommunityServiceImpl implements CommunityService {

    private final ComContentMapper contentMapper;
    private final ComInteractionMapper interactionMapper;
    private final AdmAuditMapper auditMapper;
    private final ProjectService projectService;

    public CommunityServiceImpl(ComContentMapper contentMapper, ComInteractionMapper interactionMapper,
                                AdmAuditMapper auditMapper, ProjectService projectService) {
        this.contentMapper = contentMapper;
        this.interactionMapper = interactionMapper;
        this.auditMapper = auditMapper;
        this.projectService = projectService;
    }

    // ==================== API-53 搜索公开内容 ====================

    @Override
    public PageResult<ContentVO> listItems(ContentQueryDTO dto) {
        PageHelper.startPage(dto.getPage(), dto.getSize());
        List<Com_Content> list = contentMapper.searchPublic(dto);
        PageInfo<Com_Content> info = new PageInfo<>(list);
        return toContentPageResult(info, dto.getPage(), dto.getSize());
    }

    // ==================== API-54 获取内容详情 ====================

    @Override
    public ContentVO getItem(Integer id) {
        Com_Content c = contentMapper.findById(id);
        if (c == null) throw new RuntimeException("内容不存在");
        return toContentVO(c);
    }

    // ==================== API-55/56/58 收藏 ====================

    @Override
    public void favorite(Integer itemId, Integer userId) {
        Com_Content c = contentMapper.findById(itemId);
        if (c == null) throw new RuntimeException("内容不存在");
        Com_Interaction exist = interactionMapper.findByUserAndTarget(userId, "favorite", c.getContent_type(), itemId);
        if (exist != null) return;
        Com_Interaction inter = new Com_Interaction();
        inter.setUser_id(userId);
        inter.setAction_type("favorite");
        inter.setTarget_type(c.getContent_type());
        inter.setTarget_id(itemId);
        interactionMapper.insert(inter);
    }

    @Override
    public void unfavorite(Integer itemId, Integer userId) {
        Com_Content c = contentMapper.findById(itemId);
        if (c == null) throw new RuntimeException("内容不存在");
        interactionMapper.deleteByUserAndTarget(userId, c.getContent_type(), itemId, "favorite");
    }

    @Override
    public PageResult<ContentVO> listFavorites(int page, int size, Integer userId) {
        PageHelper.startPage(page, size);
        List<Com_Interaction> interactions = interactionMapper.findByUserAndAction(userId, "favorite");
        PageInfo<Com_Interaction> info = new PageInfo<>(interactions);
        if (interactions == null || interactions.isEmpty()) {
            PageResult<ContentVO> r = new PageResult<>();
            r.setTotal(0); r.setPage(page); r.setSize(size); r.setRecords(List.of()); return r;
        }
        List<ContentVO> records = interactions.stream()
                .map(i -> contentMapper.findById(i.getTarget_id()))
                .filter(Objects::nonNull)
                .map(this::toContentVO)
                .toList();
        PageResult<ContentVO> r = new PageResult<>();
        r.setTotal(info.getTotal()); r.setPage(page); r.setSize(size); r.setRecords(records);
        return r;
    }

    // ==================== API-57/59/60 浏览记录 ====================

    @Override
    public void recordView(Integer itemId, Integer userId) {
        Com_Content c = contentMapper.findById(itemId);
        if (c == null) throw new RuntimeException("内容不存在");
        interactionMapper.deleteByUserAndTarget(userId, c.getContent_type(), itemId, "view");
        Com_Interaction inter = new Com_Interaction();
        inter.setUser_id(userId);
        inter.setAction_type("view");
        inter.setTarget_type(c.getContent_type());
        inter.setTarget_id(itemId);
        interactionMapper.insert(inter);
        contentMapper.incrementViewCount(itemId);
    }

    @Override
    public PageResult<RecentViewVO> listRecentViews(int page, int size, Integer userId) {
        PageHelper.startPage(page, size);
        List<Com_Interaction> list = interactionMapper.findRecentViewsByUser(userId);
        PageInfo<Com_Interaction> info = new PageInfo<>(list);
        List<RecentViewVO> records = list.stream()
                .filter(v -> contentMapper.findById(v.getTarget_id()) != null)
                .map(v -> {
                    RecentViewVO vo = new RecentViewVO();
                    vo.setItem(toContentVO(contentMapper.findById(v.getTarget_id())));
                    vo.setViewed_at(v.getCreated_at());
                    return vo;
                })
                .toList();
        PageResult<RecentViewVO> r = new PageResult<>();
        r.setTotal(info.getTotal()); r.setPage(page); r.setSize(size); r.setRecords(records);
        return r;
    }

    @Override
    public void removeRecentView(Integer itemId, Integer userId) {
        // \u9996\u5148\u67e5\u627e\u6d4f\u89c8\u8bb0\u5f55\u83b7\u53d6 target_type
        java.util.List<Com_Interaction> views = interactionMapper.findRecentViewsByUser(userId);
        for (Com_Interaction v : views) {
            if (v.getTarget_id() == itemId && "view".equals(v.getAction_type())) {
                interactionMapper.deleteByUserAndTarget(userId, v.getTarget_type(), itemId, "view");
                break;
            }
        }
    }

    // ==================== API-61 复用 ====================

    @Override
    public ProjectVO reuseItem(Integer id, InteractionDTO dto, Integer userId) {
        Com_Content c = contentMapper.findById(id);
        if (c == null) throw new RuntimeException("内容不存在");
        if (!"public".equals(c.getStatus())) throw new RuntimeException("该内容不可复用");
        ProjectCreateDTO projectDTO = new ProjectCreateDTO();
        projectDTO.setProject_name(c.getTitle() + " - 复用");
        projectDTO.setProject_type("mixed");
        projectDTO.setStatus("draft");
        ProjectVO project = projectService.createProject(projectDTO, userId);
        Com_Interaction inter = new Com_Interaction();
        inter.setUser_id(userId);
        inter.setAction_type("derivation");
        inter.setTarget_type(c.getContent_type());
        inter.setTarget_id(id);
        inter.setTarget_version(dto.getTarget_version() != null ? dto.getTarget_version() : c.getVersion());
        inter.setTarget_project_id(project.getId());
        interactionMapper.insert(inter);
        contentMapper.incrementUseCount(id);
        return project;
    }

    // ==================== API-62~67 投稿 ====================

    @Override
    public ContentVO createSubmission(ContentDTO dto, Integer userId) {
        if (dto.getContent_type() == null || dto.getTitle() == null || dto.getLicense() == null)
            throw new RuntimeException("缺少必填字段: content_type, title, license");
        Com_Content c = new Com_Content();
        BeanUtil.copyProperties(dto, c);
        c.setAuthor_id(userId);
        c.setVersion(1);
        c.setStatus("draft");
        c.setView_count(0);
        c.setUse_count(0);
        c.setIs_top(0);
        contentMapper.insert(c);
        return toContentVO(c);
    }

    @Override
    public PageResult<ContentVO> listSubmissions(ContentQueryDTO dto, Integer userId) {
        PageHelper.startPage(dto.getPage(), dto.getSize());
        List<Com_Content> list = contentMapper.findByAuthorAndStatus(userId, dto.getStatus());
        PageInfo<Com_Content> info = new PageInfo<>(list);
        return toContentPageResult(info, dto.getPage(), dto.getSize());
    }

    @Override
    public ContentVO getSubmission(Integer id, Integer userId) {
        Com_Content c = contentMapper.findById(id);
        if (c == null) throw new RuntimeException("投稿不存在");
        if (c.getAuthor_id() != userId) throw new RuntimeException("无权查看");
        return toContentVO(c);
    }

    @Override
    public ContentVO updateSubmission(Integer id, ContentDTO dto, Integer userId) {
        Com_Content c = contentMapper.findById(id);
        if (c == null) throw new RuntimeException("投稿不存在");
        if (c.getAuthor_id() != userId) throw new RuntimeException("无权修改");
        if (!"draft".equals(c.getStatus())) throw new RuntimeException("只有草稿状态可以修改");
        if (dto.getTitle() != null) c.setTitle(dto.getTitle());
        if (dto.getDescription() != null) c.setDescription(dto.getDescription());
        if (dto.getSubject() != null) c.setSubject(dto.getSubject());
        if (dto.getGrade() != null) c.setGrade(dto.getGrade());
        if (dto.getLesson_type() != null) c.setLesson_type(dto.getLesson_type());
        if (dto.getContent_data() != null) c.setContent_data(dto.getContent_data());
        if (dto.getInput_variables() != null) c.setInput_variables(dto.getInput_variables());
        if (dto.getExample_effect() != null) c.setExample_effect(dto.getExample_effect());
        if (dto.getLicense() != null) c.setLicense(dto.getLicense());
        contentMapper.update(c);
        return toContentVO(c);
    }

    @Override
    public Map<String, Object> saveSubmissionVersion(Integer id, String description, Integer userId) {
        Com_Content c = contentMapper.findById(id);
        if (c == null) throw new RuntimeException("投稿不存在");
        if (c.getAuthor_id() != userId) throw new RuntimeException("无权操作");
        int newVersion = c.getVersion() + 1;
        c.setVersion(newVersion);
        contentMapper.update(c);
        Map<String, Object> r = new HashMap<>();
        r.put("version_id", newVersion);
        r.put("version_number", newVersion);
        return r;
    }

    @Override
    public void submitForReview(Integer id, ReviewSubmissionDTO dto, Integer userId) {
        Com_Content c = contentMapper.findById(id);
        if (c == null) throw new RuntimeException("投稿不存在");
        if (c.getAuthor_id() != userId) throw new RuntimeException("无权操作");
        if (!"draft".equals(c.getStatus())) throw new RuntimeException("只有草稿状态可以提交审核");
        c.setStatus("reviewing");
        contentMapper.update(c);
        Adm_Audit audit = new Adm_Audit();
        audit.setAudit_type("audit");
        audit.setTarget_type(c.getContent_type());
        audit.setTarget_id(id);
        audit.setReporter_id(userId);
        audit.setReason(dto.getNotes());
        audit.setStatus("pending");
        auditMapper.insert(audit);
    }

    // ==================== API-68~70 举报 ====================

    @Override
    public int createReport(AuditDTO dto, Integer userId) {
        Adm_Audit audit = new Adm_Audit();
        audit.setAudit_type("report");
        audit.setTarget_type(dto.getTarget_type());
        audit.setTarget_id(dto.getTarget_id());
        audit.setReporter_id(userId);
        audit.setReason(dto.getReason());
        audit.setComment(dto.getComment());
        audit.setStatus("pending");
        auditMapper.insert(audit);
        return audit.getId();
    }

    @Override
    public PageResult<AuditVO> listReports(String status, int page, int size, Integer userId) {
        PageHelper.startPage(page, size);
        List<Adm_Audit> list;
        if (status != null && !status.isBlank())
            list = auditMapper.findByReporterAndStatus(userId, status);
        else
            list = auditMapper.findByReporter(userId);
        PageInfo<Adm_Audit> info = new PageInfo<>(list);
        List<AuditVO> records = info.getList().stream().map(a -> {
            AuditVO vo = new AuditVO(); BeanUtil.copyProperties(a, vo); return vo;
        }).toList();
        PageResult<AuditVO> r = new PageResult<>();
        r.setTotal(info.getTotal()); r.setPage(page); r.setSize(size); r.setRecords(records);
        return r;
    }

    @Override
    public AuditVO getReport(Integer id, Integer userId) {
        Adm_Audit a = auditMapper.findById(id);
        if (a == null) throw new RuntimeException("举报不存在");
        if (a.getReporter_id() != userId) throw new RuntimeException("无权查看");
        AuditVO vo = new AuditVO();
        BeanUtil.copyProperties(a, vo);
        return vo;
    }

    // ==================== 内部辅助 ====================

    private ContentVO toContentVO(Com_Content c) {
        ContentVO vo = new ContentVO();
        BeanUtil.copyProperties(c, vo);
        return vo;
    }

    private PageResult<ContentVO> toContentPageResult(PageInfo<Com_Content> info, int page, int size) {
        List<ContentVO> records = info.getList().stream().map(this::toContentVO).toList();
        PageResult<ContentVO> r = new PageResult<>();
        r.setTotal(info.getTotal()); r.setPage(page); r.setSize(size); r.setRecords(records);
        return r;
    }
}
