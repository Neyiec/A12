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
import edu.zstu.service.BusinessLogService;
import edu.zstu.service.CommunityService;
import edu.zstu.service.ProjectService;
import edu.zstu.utils.PageResult;
import edu.zstu.utils.RedisCacheUtil;
import edu.zstu.vo.AuditVO;
import edu.zstu.vo.ContentVO;
import edu.zstu.vo.ProjectVO;
import edu.zstu.vo.RecentViewVO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ZSetOperations;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.*;

@Slf4j
@Service
public class CommunityServiceImpl implements CommunityService {

    private static final long COUNTER_FLUSH_THRESHOLD = 20;

    private final ComContentMapper contentMapper;
    private final ComInteractionMapper interactionMapper;
    private final AdmAuditMapper auditMapper;
    private final ProjectService projectService;
    private final BusinessLogService businessLogService;
    private final RedisCacheUtil redisCacheUtil;
    private final StringRedisTemplate redisTemplate;

    public CommunityServiceImpl(ComContentMapper contentMapper, ComInteractionMapper interactionMapper,
                                AdmAuditMapper auditMapper, ProjectService projectService,
                                BusinessLogService businessLogService, RedisCacheUtil redisCacheUtil,
                                StringRedisTemplate redisTemplate) {
        this.contentMapper = contentMapper;
        this.interactionMapper = interactionMapper;
        this.auditMapper = auditMapper;
        this.projectService = projectService;
        this.businessLogService = businessLogService;
        this.redisCacheUtil = redisCacheUtil;
        this.redisTemplate = redisTemplate;
    }

    @Override
    public PageResult<ContentVO> listItems(ContentQueryDTO dto) {
        log.info("listItems called");
        return redisCacheUtil.getOrLoad(publicListKey(dto),
                new com.fasterxml.jackson.core.type.TypeReference<PageResult<ContentVO>>() {},
                Duration.ofMinutes(3), () -> {
                    PageHelper.startPage(dto.getPage(), dto.getSize());
                    List<Com_Content> list = contentMapper.searchPublic(dto);
                    PageInfo<Com_Content> info = new PageInfo<>(list);
                    return toContentPageResult(info, dto.getPage(), dto.getSize());
                });
    }

    @Override
    public ContentVO getItem(Integer id) {
        log.info("getItem called");
        ContentVO vo = cachedContent(id);
        if (vo == null) throw new RuntimeException("内容不存在");
        return vo;
    }

    @Override
    @Transactional
    public void favorite(Integer itemId, Integer userId) {
        log.info("favorite called");
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
        redisCacheUtil.deleteByPattern("community:favorites:" + userId + ":*");
        businessLogService.record("operation", "community", "favorite", "content", itemId);
    }

    @Override
    @Transactional
    public void unfavorite(Integer itemId, Integer userId) {
        log.info("unfavorite called");
        Com_Content c = contentMapper.findById(itemId);
        if (c == null) throw new RuntimeException("内容不存在");
        interactionMapper.deleteByUserAndTarget(userId, c.getContent_type(), itemId, "favorite");
        redisCacheUtil.deleteByPattern("community:favorites:" + userId + ":*");
        businessLogService.record("operation", "community", "unfavorite", "content", itemId);
    }

    @Override
    public PageResult<ContentVO> listFavorites(int page, int size, Integer userId) {
        log.info("listFavorites called");
        return redisCacheUtil.getOrLoad("community:favorites:" + userId + ":p" + page + ":s" + size,
                new com.fasterxml.jackson.core.type.TypeReference<PageResult<ContentVO>>() {},
                Duration.ofMinutes(3), () -> {
                    PageHelper.startPage(page, size);
                    List<Com_Interaction> interactions = interactionMapper.findByUserAndAction(userId, "favorite");
                    PageInfo<Com_Interaction> info = new PageInfo<>(interactions);
                    List<ContentVO> records = interactions == null ? List.of() : interactions.stream()
                            .map(i -> cachedContent(i.getTarget_id()))
                            .filter(Objects::nonNull)
                            .toList();
                    return new PageResult<>(info.getTotal(), page, size, records);
                });
    }

    @Override
    @Transactional
    public void recordView(Integer itemId, Integer userId) {
        log.info("recordView called");
        Com_Content c = contentMapper.findById(itemId);
        if (c == null) throw new RuntimeException("内容不存在");
        interactionMapper.deleteByUserAndTarget(userId, c.getContent_type(), itemId, "view");
        Com_Interaction inter = new Com_Interaction();
        inter.setUser_id(userId);
        inter.setAction_type("view");
        inter.setTarget_type(c.getContent_type());
        inter.setTarget_id(itemId);
        interactionMapper.insert(inter);
        redisTemplate.opsForZSet().add(recentViewsKey(userId), String.valueOf(itemId), System.currentTimeMillis());
        redisTemplate.expire(recentViewsKey(userId), Duration.ofDays(30));
        incrementCachedCounter(itemId, "view");
        redisCacheUtil.deleteByPattern("community:recent:" + userId + ":*");
        businessLogService.record("browse", "community", "view", "content", itemId);
    }

    @Override
    public PageResult<RecentViewVO> listRecentViews(int page, int size, Integer userId) {
        log.info("listRecentViews called");
        return redisCacheUtil.getOrLoad("community:recent:" + userId + ":p" + page + ":s" + size,
                new com.fasterxml.jackson.core.type.TypeReference<PageResult<RecentViewVO>>() {},
                Duration.ofMinutes(3), () -> loadRecentViews(page, size, userId));
    }

    @Override
    @Transactional
    public void removeRecentView(Integer itemId, Integer userId) {
        log.info("removeRecentView called");
        List<Com_Interaction> views = interactionMapper.findRecentViewsByUser(userId);
        for (Com_Interaction v : views) {
            if (Objects.equals(v.getTarget_id(), itemId) && "view".equals(v.getAction_type())) {
                interactionMapper.deleteByUserAndTarget(userId, v.getTarget_type(), itemId, "view");
                redisTemplate.opsForZSet().remove(recentViewsKey(userId), String.valueOf(itemId));
                redisCacheUtil.deleteByPattern("community:recent:" + userId + ":*");
                businessLogService.record("operation", "community", "remove_recent_view", "content", itemId);
                break;
            }
        }
    }

    @Override
    @Transactional
    public ProjectVO reuseItem(Integer id, InteractionDTO dto, Integer userId) {
        log.info("reuseItem called");
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
        incrementCachedCounter(id, "use");
        businessLogService.record("operation", "community", "reuse", "content", id,
                Map.of("target_project_id", project.getId()));
        return project;
    }

    @Override
    @Transactional
    public ContentVO createSubmission(ContentDTO dto, Integer userId) {
        log.info("createSubmission called");
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
        evictContentCache(c.getId());
        businessLogService.record("operation", "community", "create_submission", "content", c.getId(),
                Map.of("title", c.getTitle(), "content_type", c.getContent_type()));
        return toContentVO(c);
    }

    @Override
    public PageResult<ContentVO> listSubmissions(ContentQueryDTO dto, Integer userId) {
        log.info("listSubmissions called");
        PageHelper.startPage(dto.getPage(), dto.getSize());
        List<Com_Content> list = contentMapper.findByAuthorAndStatus(userId, dto.getStatus());
        PageInfo<Com_Content> info = new PageInfo<>(list);
        return toContentPageResult(info, dto.getPage(), dto.getSize());
    }

    @Override
    public ContentVO getSubmission(Integer id, Integer userId) {
        log.info("getSubmission called");
        Com_Content c = contentMapper.findById(id);
        if (c == null) throw new RuntimeException("投稿不存在");
        if (!Objects.equals(c.getAuthor_id(), userId)) throw new RuntimeException("无权查看");
        return toContentVO(c);
    }

    @Override
    @Transactional
    public ContentVO updateSubmission(Integer id, ContentDTO dto, Integer userId) {
        log.info("updateSubmission called");
        Com_Content c = contentMapper.findById(id);
        if (c == null) throw new RuntimeException("投稿不存在");
        if (!Objects.equals(c.getAuthor_id(), userId)) throw new RuntimeException("无权修改");
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
        evictContentCache(id);
        businessLogService.record("operation", "community", "update_submission", "content", id);
        return toContentVO(c);
    }

    @Override
    @Transactional
    public Map<String, Object> saveSubmissionVersion(Integer id, String description, Integer userId) {
        Com_Content c = contentMapper.findById(id);
        if (c == null) throw new RuntimeException("投稿不存在");
        if (!Objects.equals(c.getAuthor_id(), userId)) throw new RuntimeException("无权操作");
        int newVersion = c.getVersion() + 1;
        c.setVersion(newVersion);
        contentMapper.update(c);
        evictContentCache(id);
        businessLogService.record("operation", "community", "save_submission_version", "content", id,
                Map.of("version_number", newVersion, "description", description == null ? "" : description));
        Map<String, Object> r = new HashMap<>();
        r.put("version_id", newVersion);
        r.put("version_number", newVersion);
        return r;
    }

    @Override
    @Transactional
    public void submitForReview(Integer id, ReviewSubmissionDTO dto, Integer userId) {
        log.info("submitForReview called");
        Com_Content c = contentMapper.findById(id);
        if (c == null) throw new RuntimeException("投稿不存在");
        if (!Objects.equals(c.getAuthor_id(), userId)) throw new RuntimeException("无权操作");
        if (!"draft".equals(c.getStatus())) throw new RuntimeException("只有草稿状态可以提交审核");
        c.setStatus("reviewing");
        contentMapper.update(c);
        evictContentCache(id);
        Adm_Audit audit = new Adm_Audit();
        audit.setAudit_type("audit");
        audit.setTarget_type(c.getContent_type());
        audit.setTarget_id(id);
        audit.setReporter_id(userId);
        audit.setReason(dto.getNotes());
        audit.setStatus("pending");
        auditMapper.insert(audit);
        businessLogService.record("audit", "community", "submit_for_review", "content", id,
                Map.of("audit_id", audit.getId()));
    }

    @Override
    @Transactional
    public int createReport(AuditDTO dto, Integer userId) {
        log.info("createReport called");
        Adm_Audit audit = new Adm_Audit();
        audit.setAudit_type("report");
        audit.setTarget_type(dto.getTarget_type());
        audit.setTarget_id(dto.getTarget_id());
        audit.setReporter_id(userId);
        audit.setReason(dto.getReason());
        audit.setComment(dto.getComment());
        audit.setStatus("pending");
        auditMapper.insert(audit);
        businessLogService.record("audit", "community", "create_report", dto.getTarget_type(), dto.getTarget_id(),
                Map.of("report_id", audit.getId(), "reason", dto.getReason()));
        return audit.getId();
    }

    @Override
    public PageResult<AuditVO> listReports(String status, int page, int size, Integer userId) {
        log.info("listReports called");
        PageHelper.startPage(page, size);
        List<Adm_Audit> list = status != null && !status.isBlank()
                ? auditMapper.findByReporterAndStatus(userId, status)
                : auditMapper.findByReporter(userId);
        PageInfo<Adm_Audit> info = new PageInfo<>(list);
        List<AuditVO> records = info.getList().stream().map(a -> {
            AuditVO vo = new AuditVO();
            BeanUtil.copyProperties(a, vo);
            return vo;
        }).toList();
        return new PageResult<>(info.getTotal(), page, size, records);
    }

    @Override
    public AuditVO getReport(Integer id, Integer userId) {
        log.info("getReport called");
        Adm_Audit a = auditMapper.findById(id);
        if (a == null) throw new RuntimeException("举报不存在");
        if (!Objects.equals(a.getReporter_id(), userId)) throw new RuntimeException("无权查看");
        AuditVO vo = new AuditVO();
        BeanUtil.copyProperties(a, vo);
        return vo;
    }

    private PageResult<RecentViewVO> loadRecentViews(int page, int size, Integer userId) {
        int from = Math.max((page - 1) * size, 0);
        int to = from + size - 1;
        Set<ZSetOperations.TypedTuple<String>> redisViews =
                redisTemplate.opsForZSet().reverseRangeWithScores(recentViewsKey(userId), from, to);
        if (redisViews != null && !redisViews.isEmpty()) {
            List<RecentViewVO> records = redisViews.stream()
                    .map(tuple -> toRecentView(tuple.getValue(), tuple.getScore()))
                    .filter(Objects::nonNull)
                    .toList();
            Long total = redisTemplate.opsForZSet().zCard(recentViewsKey(userId));
            return new PageResult<>(total == null ? records.size() : total, page, size, records);
        }

        PageHelper.startPage(page, size);
        List<Com_Interaction> list = interactionMapper.findRecentViewsByUser(userId);
        PageInfo<Com_Interaction> info = new PageInfo<>(list);
        List<RecentViewVO> records = list.stream()
                .map(v -> {
                    redisTemplate.opsForZSet().add(recentViewsKey(userId), String.valueOf(v.getTarget_id()),
                            v.getCreated_at() == null ? System.currentTimeMillis()
                                    : v.getCreated_at().atZone(ZoneId.systemDefault()).toInstant().toEpochMilli());
                    RecentViewVO vo = new RecentViewVO();
                    vo.setItem(cachedContent(v.getTarget_id()));
                    vo.setViewed_at(v.getCreated_at());
                    return vo;
                })
                .filter(v -> v.getItem() != null)
                .toList();
        redisTemplate.expire(recentViewsKey(userId), Duration.ofDays(30));
        return new PageResult<>(info.getTotal(), page, size, records);
    }

    private RecentViewVO toRecentView(String rawId, Double score) {
        if (rawId == null) return null;
        ContentVO content = cachedContent(Integer.valueOf(rawId));
        if (content == null) return null;
        RecentViewVO vo = new RecentViewVO();
        vo.setItem(content);
        long millis = score == null ? System.currentTimeMillis() : score.longValue();
        vo.setViewed_at(LocalDateTime.ofInstant(Instant.ofEpochMilli(millis), ZoneId.systemDefault()));
        return vo;
    }

    private ContentVO cachedContent(Integer id) {
        ContentVO vo = redisCacheUtil.getOrLoad("community:item:" + id, ContentVO.class,
                Duration.ofMinutes(10), () -> {
                    Com_Content c = contentMapper.findById(id);
                    return c == null ? null : toContentVO(c);
                });
        if (vo != null) {
            vo.setView_count(vo.getView_count() + pendingCounter(id, "view"));
            vo.setUse_count(vo.getUse_count() + pendingCounter(id, "use"));
        }
        return vo;
    }

    private void incrementCachedCounter(Integer id, String type) {
        String key = "community:counter:" + type + ":" + id;
        Long delta = redisTemplate.opsForValue().increment(key);
        redisTemplate.expire(key, Duration.ofDays(1));
        redisCacheUtil.delete("community:item:" + id);
        if (delta != null && delta >= COUNTER_FLUSH_THRESHOLD) {
            flushCounter(id, type, key);
        }
    }

    @Scheduled(fixedDelay = 60000)
    public void flushPendingCounters() {
        for (String key : redisCacheUtil.keysByPattern("community:counter:*")) {
            String[] parts = key.split(":");
            if (parts.length != 4) continue;
            try {
                flushCounter(Integer.valueOf(parts[3]), parts[2], key);
            } catch (Exception e) {
                log.warn("flush community counter failed, key={}", key, e);
            }
        }
    }

    private void flushCounter(Integer id, String type, String key) {
        String raw = redisTemplate.opsForValue().getAndDelete(key);
        long amount = raw == null ? 0 : Long.parseLong(raw);
        if (amount <= 0) return;
        if ("view".equals(type)) {
            contentMapper.incrementViewCountBy(id, amount);
        } else if ("use".equals(type)) {
            contentMapper.incrementUseCountBy(id, amount);
        }
        redisCacheUtil.delete("community:item:" + id);
    }

    private int pendingCounter(Integer id, String type) {
        String raw = redisTemplate.opsForValue().get("community:counter:" + type + ":" + id);
        return raw == null ? 0 : Integer.parseInt(raw);
    }

    private ContentVO toContentVO(Com_Content c) {
        ContentVO vo = new ContentVO();
        BeanUtil.copyProperties(c, vo);
        return vo;
    }

    private PageResult<ContentVO> toContentPageResult(PageInfo<Com_Content> info, int page, int size) {
        List<ContentVO> records = info.getList().stream().map(c -> {
            ContentVO vo = toContentVO(c);
            vo.setView_count(vo.getView_count() + pendingCounter(c.getId(), "view"));
            vo.setUse_count(vo.getUse_count() + pendingCounter(c.getId(), "use"));
            redisCacheUtil.put("community:item:" + c.getId(), vo, Duration.ofMinutes(10));
            return vo;
        }).toList();
        return new PageResult<>(info.getTotal(), page, size, records);
    }

    private String recentViewsKey(Integer userId) {
        return "user:recent_views:" + userId;
    }

    private String publicListKey(ContentQueryDTO dto) {
        return "community:public:" +
                blankToAll(dto.getContent_type()) + ":" +
                blankToAll(dto.getSubject()) + ":" +
                blankToAll(dto.getGrade()) + ":" +
                blankToAll(dto.getStatus()) + ":" +
                blankToAll(dto.getKeyword()) + ":p" +
                dto.getPage() + ":s" + dto.getSize();
    }

    private String blankToAll(String value) {
        return value == null || value.isBlank() ? "all" : value;
    }

    private void evictContentCache(Integer id) {
        redisCacheUtil.delete("community:item:" + id);
        redisCacheUtil.deleteByPattern("community:public:*");
        redisCacheUtil.deleteByPattern("community:favorites:*");
        redisCacheUtil.deleteByPattern("community:recent:*");
    }
}
