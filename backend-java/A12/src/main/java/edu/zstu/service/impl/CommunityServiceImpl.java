package edu.zstu.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import edu.zstu.dto.*;
import edu.zstu.entity.Adm_Audit;
import edu.zstu.entity.Com_Content;
import edu.zstu.entity.Com_Interaction;
import edu.zstu.entity.Com_Like;
import edu.zstu.mapper.AdmAuditMapper;
import edu.zstu.mapper.ComContentMapper;
import edu.zstu.mapper.ComInteractionMapper;
import edu.zstu.mapper.ComLikeMapper;
import edu.zstu.service.BusinessLogService;
import edu.zstu.service.CommunityService;
import edu.zstu.service.CommunityReviewEventPublisher;
import edu.zstu.service.ProjectService;
import edu.zstu.utils.PageResult;
import edu.zstu.utils.RedisCacheUtil;
import edu.zstu.utils.RedisRateLimiter;
import edu.zstu.vo.AuditVO;
import edu.zstu.vo.ContentVO;
import edu.zstu.vo.ProjectVO;
import edu.zstu.vo.RankItemVO;
import edu.zstu.vo.RecentViewVO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.dao.DuplicateKeyException;
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

    // ---------- 功能11：点赞/排序/榜单常量 ----------
    /** 榜单热度权重：like×3 + favorite×2 + reuse×4 + view×0.2（复用成本最高权重最大） */
    private static final double WEIGHT_LIKE = 3.0;
    private static final double WEIGHT_FAVORITE = 2.0;
    private static final double WEIGHT_REUSE = 4.0;
    private static final double WEIGHT_VIEW = 0.2;
    /** 榜单入选门槛：窗口内点赞+收藏+复用总数 */
    private static final int HOT_THRESHOLD = 5;
    /** 榜单候选上限（ZSET 成员规模） */
    private static final int RANK_CANDIDATE_LIMIT = 100;
    /** 榜单返回条数上限 */
    private static final int RANK_LIMIT_CAP = 50;
    /** 点赞防刷：用户每分钟点赞上限 + 单内容操作冷却 */
    private static final int LIKE_PER_MINUTE_LIMIT = 20;
    private static final Duration LIKE_COOLDOWN = Duration.ofSeconds(2);
    /** 榜单聚合覆盖的内容类型与时间窗口 */
    private static final List<String> RANK_CONTENT_TYPES = List.of("skill", "lesson_case");
    private static final List<String> RANK_PERIODS = List.of("day", "week", "month");
    /** 排序白名单：sort_by 与 period 的合法取值 */
    private static final List<String> SORT_BY_WHITELIST = List.of("like", "favorite", "use");
    private static final List<String> PERIOD_WHITELIST = List.of("day", "week", "month", "all");

    private final ComContentMapper contentMapper;
    private final ComInteractionMapper interactionMapper;
    private final ComLikeMapper comLikeMapper;
    private final AdmAuditMapper auditMapper;
    private final ProjectService projectService;
    private final BusinessLogService businessLogService;
    private final RedisCacheUtil redisCacheUtil;
    private final RedisRateLimiter rateLimiter;
    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper;
    private final CommunityReviewEventPublisher reviewEvents;

    public CommunityServiceImpl(ComContentMapper contentMapper, ComInteractionMapper interactionMapper,
                                ComLikeMapper comLikeMapper, AdmAuditMapper auditMapper,
                                ProjectService projectService,
                                BusinessLogService businessLogService, RedisCacheUtil redisCacheUtil,
                                RedisRateLimiter rateLimiter,
                                StringRedisTemplate redisTemplate,
                                ObjectMapper objectMapper, CommunityReviewEventPublisher reviewEvents) {
        this.contentMapper = contentMapper;
        this.interactionMapper = interactionMapper;
        this.comLikeMapper = comLikeMapper;
        this.auditMapper = auditMapper;
        this.projectService = projectService;
        this.businessLogService = businessLogService;
        this.redisCacheUtil = redisCacheUtil;
        this.rateLimiter = rateLimiter;
        this.redisTemplate = redisTemplate;
        this.objectMapper = objectMapper;
        this.reviewEvents = reviewEvents;
    }

    /**
     * 功能11：公开内容检索（缓存整体分页结果；liked 点赞态按用户在缓存外注入，避免污染共享缓存）
     */
    @Override
    public PageResult<ContentVO> listItems(ContentQueryDTO dto, Integer userId) {
        if (dto == null) throw new RuntimeException("查询条件不能为空");
        log.info("listItems contentType={}, subject={}, grade={}, status={}, keyword={}, sortBy={}, period={}, page={}, size={}",
                dto.getContent_type(), dto.getSubject(), dto.getGrade(), dto.getStatus(), dto.getKeyword(),
                dto.getSort_by(), dto.getPeriod(), dto.getPage(), dto.getSize());
        SortSpec spec = resolveSortSpec(dto);
        PageResult<ContentVO> page = redisCacheUtil.getOrLoad(publicListKey(dto),
                new com.fasterxml.jackson.core.type.TypeReference<PageResult<ContentVO>>() {},
                spec.window() ? Duration.ofMinutes(1) : Duration.ofMinutes(3), () -> {
                    PageHelper.startPage(dto.getPage(), dto.getSize());
                    List<Com_Content> list = contentMapper.searchPublic(dto, spec.orderClause(), spec.window(), spec.since());
                    PageInfo<Com_Content> info = new PageInfo<>(list);
                    return toContentPageResult(info, dto.getPage(), dto.getSize());
                });
        injectLikeState(page.getRecords(), userId);
        return page;
    }

    @Override
    public ContentVO getItem(Integer id, Integer userId) {
        log.info("getItem itemId={}, userId={}", id, userId);
        Com_Content content = requirePublicContent(id);
        ContentVO vo = toContentVO(content);
        vo.setView_count(vo.getView_count() + pendingCounter(id, "view"));
        vo.setUse_count(vo.getUse_count() + pendingCounter(id, "use"));
        vo.setLiked(userId != null && comLikeMapper.countByUserAndTarget(userId, content.getContent_type(), id) > 0);
        return vo;
    }

    @Override
    @Transactional
    public void favorite(Integer itemId, Integer userId) {
        log.info("favorite userId={}, itemId={}", userId, itemId);
        Com_Content c = requirePublicContent(itemId);
        String lockKey = "lock:community:favorite:" + userId + ":" + itemId;
        Boolean locked = redisTemplate.opsForValue().setIfAbsent(lockKey, "1", Duration.ofSeconds(5));
        if (!Boolean.TRUE.equals(locked)) {
            log.info("favorite skipped by concurrent lock userId={}, itemId={}", userId, itemId);
            return;
        }
        try {
            Com_Interaction exist = interactionMapper.findByUserAndTarget(userId, "favorite", c.getContent_type(), itemId);
            if (exist != null) return;
            Com_Interaction inter = new Com_Interaction();
            inter.setUser_id(userId);
            inter.setAction_type("favorite");
            inter.setTarget_type(c.getContent_type());
            inter.setTarget_id(itemId);
            interactionMapper.insert(inter);
            //功能11：维护收藏数冗余列并失效列表/详情缓存（列表需展示 favorite_count）
            contentMapper.incrementFavoriteCountBy(itemId, 1);
            evictContentCache(itemId);
            redisCacheUtil.deleteByPattern("community:favorites:" + userId + ":*");
            redisCacheUtil.deleteByPattern("community:public:*");
            log.info("favorite success userId={}, itemId={}", userId, itemId);
            businessLogService.record("operation", "community", "favorite", "content", itemId);
        } finally {
            redisTemplate.delete(lockKey);
        }
    }

    @Override
    @Transactional
    public void unfavorite(Integer itemId, Integer userId) {
        log.info("unfavorite userId={}, itemId={}", userId, itemId);
        Com_Content c = contentMapper.findById(itemId);
        if (c == null) throw new RuntimeException("内容不存在");
        int removed = interactionMapper.deleteByUserAndTarget(userId, c.getContent_type(), itemId, "favorite");
        //功能11：仅真实删除时递减冗余列，避免并发重复取消导致负数
        if (removed > 0) {
            contentMapper.incrementFavoriteCountBy(itemId, -1);
            evictContentCache(itemId);
        }
        redisCacheUtil.deleteByPattern("community:favorites:" + userId + ":*");
        redisCacheUtil.deleteByPattern("community:public:*");
        businessLogService.record("operation", "community", "unfavorite", "content", itemId);
    }

    /**
     * 功能11：点赞。唯一索引 uk_user_target 兜底幂等（替代 Redis 防重锁）；
     * 用户级每分钟上限 + 单内容冷却双层限流防刷；同步维护 like_count 冗余列并失效缓存。
     */
    @Override
    @Transactional
    public void like(Integer itemId, Integer userId) {
        log.info("like userId={}, itemId={}", userId, itemId);
        Com_Content c = requirePublicContent(itemId);
        rateLimiter.assertWithinLimit("community:rl:like:" + userId, LIKE_PER_MINUTE_LIMIT,
                Duration.ofMinutes(1), "点赞过于频繁，请稍后再试");
        rateLimiter.assertCooldown("community:rl:like:" + userId + ":" + itemId, LIKE_COOLDOWN,
                "操作太快啦，请稍后再试");
        Com_Like like = new Com_Like();
        like.setUser_id(userId);
        like.setTarget_type(c.getContent_type());
        like.setTarget_id(itemId);
        try {
            comLikeMapper.insert(like);
        } catch (DuplicateKeyException e) {
            //重复点赞：唯一索引拦截，幂等返回成功
            log.info("like idempotent hit, userId={}, itemId={}", userId, itemId);
            return;
        }
        contentMapper.incrementLikeCountBy(itemId, 1);
        evictContentCache(itemId);
        log.info("like success userId={}, itemId={}", userId, itemId);
        businessLogService.record("operation", "community", "like", "content", itemId);
    }

    /**
     * 功能11：取消点赞（幂等）。删除行数 &gt; 0 才递减计数，防并发重复取消减为负。
     */
    @Override
    @Transactional
    public void unlike(Integer itemId, Integer userId) {
        log.info("unlike userId={}, itemId={}", userId, itemId);
        Com_Content c = contentMapper.findById(itemId);
        if (c == null) throw new RuntimeException("内容不存在");
        rateLimiter.assertCooldown("community:rl:like:" + userId + ":" + itemId, LIKE_COOLDOWN,
                "操作太快啦，请稍后再试");
        int removed = comLikeMapper.deleteByUserAndTarget(userId, c.getContent_type(), itemId);
        if (removed > 0) {
            contentMapper.incrementLikeCountBy(itemId, -1);
            evictContentCache(itemId);
            log.info("unlike success userId={}, itemId={}", userId, itemId);
            businessLogService.record("operation", "community", "unlike", "content", itemId);
        }
    }

    /**
     * 功能11：热门榜单读取。优先 Redis ZSET（community:rank:{type}:{period}），
     * ZSET 缺失/为空时降级为 DB 窗口聚合；下线内容读时过滤，不占名次。
     */
    @Override
    public List<RankItemVO> listRankings(String contentType, String period, int limit, Integer userId) {
        String type = normalizeContentType(contentType);
        String p = isBlank(period) ? "week" : period.trim().toLowerCase();
        if (!RANK_PERIODS.contains(p)) {
            throw new RuntimeException("Unsupported period: " + period);
        }
        int capped = Math.min(Math.max(limit, 1), RANK_LIMIT_CAP);
        log.info("listRankings type={}, period={}, limit={}", type, p, capped);
        Set<ZSetOperations.TypedTuple<String>> tuples =
                redisTemplate.opsForZSet().reverseRangeWithScores(rankKey(type, p), 0, capped - 1L);
        List<Map.Entry<Integer, Double>> entries = (tuples == null || tuples.isEmpty())
                ? rankFallback(type, windowStart(p), capped)
                : tuples.stream()
                        .<Map.Entry<Integer, Double>>map(t -> new AbstractMap.SimpleEntry<>(Integer.valueOf(t.getValue()),
                                t.getScore() == null ? 0.0 : t.getScore()))
                        .toList();
        return buildRankItems(entries, userId);
    }

    @Override
    public PageResult<ContentVO> listFavorites(int page, int size, Integer userId) {
        log.info("listFavorites userId={}, page={}, size={}", userId, page, size);
        PageResult<ContentVO> result = redisCacheUtil.getOrLoad("community:favorites:" + userId + ":p" + page + ":s" + size,
                new com.fasterxml.jackson.core.type.TypeReference<PageResult<ContentVO>>() {},
                Duration.ofMinutes(3), () -> {
                    PageHelper.startPage(page, size);
                    List<Com_Interaction> interactions = interactionMapper.findByUserAndAction(userId, "favorite");
                    PageInfo<Com_Interaction> info = new PageInfo<>(interactions);
                    List<ContentVO> records = interactions == null ? List.of() : interactions.stream()
                            .map(i -> cachedContent(i.getTarget_id()))
                            .filter(item -> item == null || "public".equals(item.getStatus()))
                            .filter(Objects::nonNull)
                            .toList();
                    return new PageResult<>(info.getTotal(), page, size, records);
                });
        //功能11：收藏列表也注入当前用户点赞态
        injectLikeState(result.getRecords(), userId);
        return result;
    }

    @Override
    @Transactional
    public void recordView(Integer itemId, Integer userId) {
        log.info("recordView userId={}, itemId={}", userId, itemId);
        Com_Content c = requirePublicContent(itemId);
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
        log.info("recordView success userId={}, itemId={}", userId, itemId);
        businessLogService.record("browse", "community", "view", "content", itemId);
    }

    @Override
    public PageResult<RecentViewVO> listRecentViews(int page, int size, Integer userId) {
        log.info("listRecentViews userId={}, page={}, size={}", userId, page, size);
        return redisCacheUtil.getOrLoad("community:recent:" + userId + ":p" + page + ":s" + size,
                new com.fasterxml.jackson.core.type.TypeReference<PageResult<RecentViewVO>>() {},
                Duration.ofMinutes(3), () -> loadRecentViews(page, size, userId));
    }

    @Override
    @Transactional
    public void removeRecentView(Integer itemId, Integer userId) {
        log.info("removeRecentView userId={}, itemId={}", userId, itemId);
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
        log.info("reuseItem userId={}, itemId={}, targetVersion={}", userId, id, dto == null ? null : dto.getTarget_version());
        Com_Content c = requirePublicContent(id);
        int selectedVersion = dto != null && dto.getTarget_version() != null ? dto.getTarget_version() : c.getVersion();
        Map<String, Object> selectedContent = contentAtVersion(c, selectedVersion);
        ProjectCreateDTO projectDTO = new ProjectCreateDTO();
        projectDTO.setProject_name(c.getTitle() + " - reuse");
        projectDTO.setProject_type("mixed");
        projectDTO.setStatus("draft");
        Map<String, Object> community = new LinkedHashMap<>(selectedContent);
        community.put("id", c.getId());
        community.put("type", "ppt".equals(c.getContent_type()) ? "PPT" : c.getContent_type());
        community.put("version", selectedVersion);
        projectDTO.setEdit_history(toJson(Map.of("workspace_context", Map.of("community", community))));
        ProjectVO project = projectService.createProject(projectDTO, userId);
        Com_Interaction inter = new Com_Interaction();
        inter.setUser_id(userId);
        inter.setAction_type("derivation");
        inter.setTarget_type(c.getContent_type());
        inter.setTarget_id(id);
        inter.setTarget_version(selectedVersion);
        inter.setTarget_project_id(project.getId());
        interactionMapper.insert(inter);
        incrementCachedCounter(id, "use");
        log.info("reuseItem success userId={}, itemId={}, targetProjectId={}", userId, id, project.getId());
        businessLogService.record("operation", "community", "reuse", "content", id,
                Map.of("target_project_id", project.getId()));
        return project;
    }

    private Map<String, Object> contentAtVersion(Com_Content content, int version) {
        if (version < 1 || version > content.getVersion()) throw new RuntimeException("所选社区版本不存在");
        Map<String, Object> selected = new LinkedHashMap<>();
        selected.put("title", content.getTitle());
        selected.put("description", content.getDescription());
        selected.put("subject", content.getSubject());
        selected.put("grade", content.getGrade());
        selected.put("lesson_type", content.getLesson_type());
        selected.put("content_data", content.getContent_data());
        selected.put("input_variables", content.getInput_variables());
        selected.put("example_effect", content.getExample_effect());
        selected.put("license", content.getLicense());
        if (version == content.getVersion()) return selected;
        try {
            Object parsed = objectMapper.readValue(content.getVersion_history(), new TypeReference<Object>() {});
            if (parsed instanceof List<?> history) {
                for (Object entry : history) {
                    if (entry instanceof Map<?, ?> snapshot && Objects.equals("prior", snapshot.get("snapshot_semantics"))
                            && Objects.equals(Integer.valueOf(version), Integer.valueOf(String.valueOf(snapshot.get("version_number"))))) {
                        for (String key : selected.keySet()) {
                            String snapshotKey = "description".equals(key) ? "description_text" : key;
                            selected.put(key, snapshot.get(snapshotKey));
                        }
                        return selected;
                    }
                }
                // 旧数据曾把旧内容标成新版本号；兼容读取，但新快照始终优先。
                for (Object entry : history) {
                    if (entry instanceof Map<?, ?> snapshot && snapshot.get("snapshot_semantics") == null
                            && Objects.equals(Integer.valueOf(version + 1), Integer.valueOf(String.valueOf(snapshot.get("version_number"))))) {
                        for (String key : selected.keySet()) {
                            String snapshotKey = "description".equals(key) ? "description_text" : key;
                            selected.put(key, snapshot.get(snapshotKey));
                        }
                        return selected;
                    }
                }
            }
        } catch (Exception e) {
            throw new RuntimeException("所选社区版本快照不可用", e);
        }
        throw new RuntimeException("所选社区版本缺少可复用的快照");
    }

    @Override
    @Transactional
    public ContentVO createSubmission(ContentDTO dto, Integer userId) {
        log.info("createSubmission userId={}, title={}, contentType={}", userId, dto == null ? null : dto.getTitle(), dto == null ? null : dto.getContent_type());
        validateContentDto(dto, true);
        Com_Content c = new Com_Content();
        BeanUtil.copyProperties(dto, c);
        c.setContent_type(normalizeContentType(dto.getContent_type()));
        c.setAuthor_id(userId);
        c.setVersion(1);
        c.setVersion_history("[]");
        c.setStatus("draft");
        c.setView_count(0);
        c.setUse_count(0);
        c.setLike_count(0);
        c.setFavorite_count(0);
        c.setIs_top(0);
        contentMapper.insert(c);
        evictContentCache(c.getId());
        log.info("createSubmission success userId={}, contentId={}", userId, c.getId());
        businessLogService.record("operation", "community", "create_submission", "content", c.getId(),
                Map.of("title", c.getTitle(), "content_type", c.getContent_type()));
        return toContentVO(c);
    }

    @Override
    public PageResult<ContentVO> listSubmissions(ContentQueryDTO dto, Integer userId) {
        log.info("listSubmissions userId={}, status={}, page={}, size={}", userId, dto.getStatus(), dto.getPage(), dto.getSize());
        PageHelper.startPage(dto.getPage(), dto.getSize());
        List<Com_Content> list = contentMapper.findByAuthorAndStatus(userId, dto.getStatus());
        PageInfo<Com_Content> info = new PageInfo<>(list);
        return toContentPageResult(info, dto.getPage(), dto.getSize());
    }

    @Override
    public ContentVO getSubmission(Integer id, Integer userId) {
        log.info("getSubmission userId={}, contentId={}", userId, id);
        Com_Content c = contentMapper.findById(id);
        if (c == null) throw new RuntimeException("投稿不存在");
        if (!Objects.equals(c.getAuthor_id(), userId)) throw new RuntimeException("无权查看");
        return toContentVO(c);
    }

    @Override
    @Transactional
    public ContentVO updateSubmission(Integer id, ContentDTO dto, Integer userId) {
        log.info("updateSubmission userId={}, contentId={}", userId, id);
        Com_Content c = contentMapper.findById(id);
        if (c == null) throw new RuntimeException("Submission not found");
        if (!Objects.equals(c.getAuthor_id(), userId)) throw new RuntimeException("No permission to edit this submission");
        if (!"draft".equals(c.getStatus())) throw new RuntimeException("Only draft submissions can be edited");
        validateContentDto(dto, false);
        if (dto.getContent_type() != null) c.setContent_type(normalizeContentType(dto.getContent_type()));
        if (dto.getTitle() != null) c.setTitle(dto.getTitle());
        if (dto.getDescription() != null) c.setDescription(dto.getDescription());
        if (dto.getSubject() != null) c.setSubject(dto.getSubject());
        if (dto.getGrade() != null) c.setGrade(dto.getGrade());
        if (dto.getLesson_type() != null) c.setLesson_type(dto.getLesson_type());
        if (dto.getKeywords() != null) c.setKeywords(dto.getKeywords());
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
        log.info("saveSubmissionVersion userId={}, contentId={}, hasDescription={}", userId, id, description != null && !description.isBlank());
        Com_Content c = contentMapper.findById(id);
        if (c == null) throw new RuntimeException("Submission not found");
        if (!Objects.equals(c.getAuthor_id(), userId)) throw new RuntimeException("No permission to save this submission version");
        int newVersion = c.getVersion() + 1;
        c.setVersion_history(appendVersionHistory(c, c.getVersion(), description));
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
        log.info("submitForReview userId={}, contentId={}", userId, id);
        Com_Content c = contentMapper.findById(id);
        if (c == null) throw new RuntimeException("Submission not found");
        if (!Objects.equals(c.getAuthor_id(), userId)) throw new RuntimeException("No permission to submit this content");
        if (!"draft".equals(c.getStatus())) throw new RuntimeException("Only draft submissions can be submitted for review");
        if ("ppt".equals(c.getContent_type())) {
            if (isBlank(c.getContent_data())) throw new RuntimeException("PPT 课件至少需要一页，请从课件工作台发布");
            try {
                var slides = objectMapper.readTree(c.getContent_data()).path("slides");
                if (!slides.isArray() || slides.isEmpty()) throw new RuntimeException("PPT 课件至少需要一页，请从课件工作台发布");
            } catch (com.fasterxml.jackson.core.JsonProcessingException e) {
                throw new RuntimeException("PPT 课件内容格式无效", e);
            }
        }
        if (hasPendingAudit("audit", c.getContent_type(), id, null)) {
            throw new RuntimeException("Submission already has a pending review task");
        }
        c.setStatus("reviewing");
        contentMapper.update(c);
        evictContentCache(id);
        Adm_Audit audit = new Adm_Audit();
        audit.setAudit_type("audit");
        audit.setTarget_type(c.getContent_type());
        audit.setTarget_id(id);
        audit.setReporter_id(userId);
        audit.setReason(dto == null ? null : dto.getNotes());
        audit.setStatus("pending");
        auditMapper.insert(audit);
        if ("ppt".equals(c.getContent_type())) reviewEvents.publish(audit.getId(), c.getVersion());
        businessLogService.record("audit", "community", "submit_for_review", "content", id,
                Map.of("audit_id", audit.getId()));
    }

    @Override
    @Transactional
    public int createReport(AuditDTO dto, Integer userId) {
        log.info("createReport userId={}, targetType={}, targetId={}", userId, dto == null ? null : dto.getTarget_type(), dto == null ? null : dto.getTarget_id());
        if (dto == null || dto.getTarget_id() <= 0) throw new RuntimeException("target_id is required");
        Com_Content target = requirePublicContent(dto.getTarget_id());
        String targetType = dto.getTarget_type() == null || dto.getTarget_type().isBlank()
                ? target.getContent_type()
                : normalizeContentType(dto.getTarget_type());
        if (!Objects.equals(target.getContent_type(), targetType)) {
            throw new RuntimeException("target_type does not match content type");
        }
        if (hasPendingAudit("report", targetType, dto.getTarget_id(), userId)) {
            throw new RuntimeException("You already have a pending report for this content");
        }
        Adm_Audit audit = new Adm_Audit();
        audit.setAudit_type("report");
        audit.setTarget_type(targetType);
        audit.setTarget_id(dto.getTarget_id());
        audit.setReporter_id(userId);
        audit.setReason(dto.getReason());
        audit.setComment(dto.getComment());
        audit.setStatus("pending");
        auditMapper.insert(audit);
        businessLogService.record("audit", "community", "create_report", targetType, dto.getTarget_id(),
                Map.of("report_id", audit.getId(), "reason", dto.getReason() == null ? "" : dto.getReason()));
        return audit.getId();
    }

    @Override
    public PageResult<AuditVO> listReports(String status, int page, int size, Integer userId) {
        log.info("listReports userId={}, status={}, page={}, size={}", userId, status, page, size);
        PageHelper.startPage(page, size);
        List<Adm_Audit> list = status != null && !status.isBlank()
                ? auditMapper.findByReporterTypeAndStatus(userId, "report", status)
                : auditMapper.findByReporterAndType(userId, "report");
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
        log.info("getReport userId={}, reportId={}", userId, id);
        Adm_Audit a = auditMapper.findById(id);
        if (a == null || !"report".equals(a.getAudit_type())) throw new RuntimeException("Report not found");
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
                .filter(v -> v.getItem() != null && "public".equals(v.getItem().getStatus()))
                .toList();
        redisTemplate.expire(recentViewsKey(userId), Duration.ofDays(30));
        //功能11：最近浏览条目也注入当前用户点赞态
        injectLikeState(records.stream().map(RecentViewVO::getItem).filter(Objects::nonNull).toList(), userId);
        return new PageResult<>(info.getTotal(), page, size, records);
    }

    private RecentViewVO toRecentView(String rawId, Double score) {
        if (rawId == null) return null;
        ContentVO content = cachedContent(Integer.valueOf(rawId));
        if (content == null || !"public".equals(content.getStatus())) return null;
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

    // ==================== 功能11：排序/榜单/点赞态辅助 ====================

    /** 排序规格：orderClause（白名单拼装结果）+ 是否叠加窗口聚合 + 窗口起点 */
    private record SortSpec(String orderClause, boolean window, LocalDateTime since) {}

    /**
     * 解析排序参数为 SQL 排序规格。sort_by/period 均做白名单校验，
     * orderClause 只允许固定字面量与聚合别名，禁止任何用户输入直拼。
     * 语义：无 sort_by=默认排序；sort_by+all=按冗余总量列；sort_by+day/week/month=窗口聚合排序。
     */
    private SortSpec resolveSortSpec(ContentQueryDTO dto) {
        String sortBy = isBlank(dto.getSort_by()) ? "" : dto.getSort_by().trim().toLowerCase();
        String period = isBlank(dto.getPeriod()) ? "all" : dto.getPeriod().trim().toLowerCase();
        if (!sortBy.isEmpty() && !SORT_BY_WHITELIST.contains(sortBy)) {
            throw new RuntimeException("Unsupported sort_by: " + dto.getSort_by());
        }
        if (!PERIOD_WHITELIST.contains(period)) {
            throw new RuntimeException("Unsupported period: " + dto.getPeriod());
        }
        //未选择排序维度：保持原有默认排序（回归保障）
        if (sortBy.isEmpty()) {
            return new SortSpec("is_top DESC, updated_at DESC", false, null);
        }
        String totalColumn = switch (sortBy) {
            case "like" -> "like_count";
            case "favorite" -> "favorite_count";
            default -> "use_count"; //use
        };
        //全部时间段：按冗余总量列排序，无窗口聚合
        if ("all".equals(period)) {
            return new SortSpec("is_top DESC, " + totalColumn + " DESC, updated_at DESC", false, null);
        }
        //日/周/月：叠加窗口聚合子查询，按窗口内计数排序
        String aggColumn = switch (sortBy) {
            case "like" -> "COALESCE(lik.like_cnt, 0)";
            case "favorite" -> "COALESCE(stat.fav_cnt, 0)";
            default -> "COALESCE(stat.use_cnt, 0)"; //use
        };
        return new SortSpec("is_top DESC, " + aggColumn + " DESC, updated_at DESC", true, windowStart(period));
    }

    /**
     * 批量注入当前用户点赞态：先按内容类型分组，再逐类型批量查询，避免循环单查。
     * 共享缓存中 liked 恒为 false，本方法在缓存读取后调用。
     */
    private void injectLikeState(List<ContentVO> records, Integer userId) {
        if (records == null || records.isEmpty()) return;
        if (userId == null) {
            records.forEach(v -> v.setLiked(false));
            return;
        }
        Map<String, List<Integer>> idsByType = new LinkedHashMap<>();
        for (ContentVO v : records) {
            idsByType.computeIfAbsent(v.getContent_type(), k -> new ArrayList<>()).add(v.getId());
        }
        Set<Integer> likedIds = new HashSet<>();
        for (Map.Entry<String, List<Integer>> entry : idsByType.entrySet()) {
            likedIds.addAll(comLikeMapper.findLikedTargetIds(userId, entry.getKey(), entry.getValue()));
        }
        for (ContentVO v : records) {
            v.setLiked(likedIds.contains(v.getId()));
        }
    }

    /**
     * 功能11：热门榜单定时聚合任务（每 10 分钟，错开 60s 计数 flush）。
     * 整体重建 ZSET（先删后加）防脏数据累积；单类型/窗口失败不影响其余榜单。
     */
    @Scheduled(cron = "0 2/10 * * * *")
    public void rebuildRankings() {
        for (String type : RANK_CONTENT_TYPES) {
            for (String period : RANK_PERIODS) {
                try {
                    rebuildRanking(type, period);
                } catch (Exception e) {
                    log.warn("rebuild community ranking failed, type={}, period={}", type, period, e);
                }
            }
        }
    }

    /** 重建单个榜单 ZSET：key=community:rank:{type}:{period}，member=content_id，score=热度分 */
    private void rebuildRanking(String type, String period) {
        LocalDateTime since = windowStart(period);
        List<Map<String, Object>> rows = contentMapper.selectRankCandidates(type, since, HOT_THRESHOLD, RANK_CANDIDATE_LIMIT);
        String key = rankKey(type, period);
        redisTemplate.delete(key);
        if (rows.isEmpty()) {
            //无达标内容：清掉旧榜，读接口走 DB 降级同样返回空
            return;
        }
        for (Map<String, Object> row : rows) {
            double score = hotScore(num(row, "like_cnt"), num(row, "fav_cnt"), num(row, "use_cnt"), num(row, "view_cnt"));
            redisTemplate.opsForZSet().add(key, String.valueOf(((Number) row.get("id")).intValue()), score);
        }
        redisTemplate.expire(key, rankTtl(period));
        log.info("rebuild community ranking done, key={}, members={}", key, rows.size());
    }

    /** ZSET 榜单读路径降级：直接 DB 窗口聚合（榜单键缺失/为空时） */
    private List<Map.Entry<Integer, Double>> rankFallback(String type, LocalDateTime since, int limit) {
        List<Map<String, Object>> rows = contentMapper.selectRankCandidates(type, since, HOT_THRESHOLD, limit);
        List<Map.Entry<Integer, Double>> entries = new ArrayList<>();
        for (Map<String, Object> row : rows) {
            double score = hotScore(num(row, "like_cnt"), num(row, "fav_cnt"), num(row, "use_cnt"), num(row, "view_cnt"));
            entries.add(new AbstractMap.SimpleEntry<>(((Number) row.get("id")).intValue(), score));
        }
        return entries;
    }

    /** 组装榜单 VO：逐条校验 status='public'（防下线内容经 ZSET 残留出榜） */
    private List<RankItemVO> buildRankItems(List<Map.Entry<Integer, Double>> entries, Integer userId) {
        List<RankItemVO> result = new ArrayList<>();
        int rank = 1;
        for (Map.Entry<Integer, Double> entry : entries) {
            Com_Content c = contentMapper.findById(entry.getKey());
            if (c == null || !"public".equals(c.getStatus())) continue;
            ContentVO vo = toContentVO(c);
            vo.setLiked(userId != null && comLikeMapper.countByUserAndTarget(userId, c.getContent_type(), entry.getKey()) > 0);
            result.add(new RankItemVO(rank++, entry.getValue() == null ? 0.0 : entry.getValue(), vo));
        }
        return result;
    }

    /** 热度分公式：须与 ComContentMapper.selectRankCandidates 的 ORDER BY 表达式保持一致 */
    private double hotScore(double likeCnt, double favCnt, double useCnt, double viewCnt) {
        return likeCnt * WEIGHT_LIKE + favCnt * WEIGHT_FAVORITE + useCnt * WEIGHT_REUSE + viewCnt * WEIGHT_VIEW;
    }

    /** map 取数兜底（不同数据源数值类型不一致） */
    private double num(Map<String, Object> row, String key) {
        Object v = row.get(key);
        return v instanceof Number n ? n.doubleValue() : 0.0;
    }

    /** 榜单 ZSET key */
    private String rankKey(String type, String period) {
        return "community:rank:" + type + ":" + period;
    }

    /** 榜单 TTL：窗口时长 + 1h 缓冲（重建任务每 10 分钟续期，TTL 仅兜底清理） */
    private Duration rankTtl(String period) {
        return switch (period) {
            case "day" -> Duration.ofHours(25);
            case "week" -> Duration.ofDays(8);
            default -> Duration.ofDays(32); //month
        };
    }

    /** 时间窗口起点：day/近1天、week/近7天、month/近30天，all 用于无窗口场景 */
    private LocalDateTime windowStart(String period) {
        return switch (period) {
            case "day" -> LocalDateTime.now().minusDays(1);
            case "week" -> LocalDateTime.now().minusDays(7);
            case "month" -> LocalDateTime.now().minusDays(30);
            default -> LocalDateTime.now().minusYears(10); //all：等效不设窗口
        };
    }

    private Com_Content requirePublicContent(Integer id) {
        Com_Content content = contentMapper.findById(id);
        if (content == null || !"public".equals(content.getStatus())) {
            throw new RuntimeException("Public content not found");
        }
        return content;
    }

    private void validateContentDto(ContentDTO dto, boolean creating) {
        if (dto == null) {
            throw new RuntimeException("Request body is required");
        }
        if (creating) {
            if (isBlank(dto.getContent_type()) || isBlank(dto.getTitle()) || isBlank(dto.getLicense())) {
                throw new RuntimeException("Missing required fields: content_type, title, license");
            }
        }
        if (dto.getContent_type() != null) {
            normalizeContentType(dto.getContent_type());
        }
        validateJsonObject(dto.getContent_data(), "content_data", false);
        validateJsonObject(dto.getInput_variables(), "input_variables", true);
    }

    private String normalizeContentType(String value) {
        if (isBlank(value)) {
            throw new RuntimeException("content_type is required");
        }
        String normalized = value.trim();
        if ("case".equals(normalized)) {
            normalized = "lesson_case";
        }
        if (!List.of("skill", "lesson_case", "ppt").contains(normalized)) {
            throw new RuntimeException("Unsupported content_type: " + value);
        }
        return normalized;
    }

    private void validateJsonObject(String raw, String field, boolean allowArray) {
        if (isBlank(raw)) {
            return;
        }
        try {
            Object parsed = objectMapper.readValue(raw, new TypeReference<Object>() {});
            if (parsed instanceof Map<?, ?> || (allowArray && parsed instanceof List<?>)) {
                return;
            }
        } catch (Exception e) {
            throw new RuntimeException(field + " must be valid JSON");
        }
        throw new RuntimeException(field + " must be a JSON object" + (allowArray ? " or array" : ""));
    }

    private String appendVersionHistory(Com_Content content, int version, String description) {
        List<Map<String, Object>> history = new ArrayList<>();
        if (!isBlank(content.getVersion_history())) {
            try {
                Object parsed = objectMapper.readValue(content.getVersion_history(), new TypeReference<Object>() {});
                if (parsed instanceof List<?> list) {
                    for (Object item : list) {
                        if (item instanceof Map<?, ?> map) {
                            history.add(new LinkedHashMap<>((Map<String, Object>) map));
                        }
                    }
                }
            } catch (Exception ignored) {
            }
        }
        Map<String, Object> snapshot = new LinkedHashMap<>();
        snapshot.put("version_number", version);
        snapshot.put("snapshot_semantics", "prior");
        snapshot.put("description", description == null ? "" : description);
        snapshot.put("title", content.getTitle());
        snapshot.put("description_text", content.getDescription());
        snapshot.put("subject", content.getSubject());
        snapshot.put("grade", content.getGrade());
        snapshot.put("lesson_type", content.getLesson_type());
        snapshot.put("content_data", content.getContent_data());
        snapshot.put("input_variables", content.getInput_variables());
        snapshot.put("example_effect", content.getExample_effect());
        snapshot.put("license", content.getLicense());
        snapshot.put("created_at", LocalDateTime.now().toString());
        history.add(snapshot);
        return toJson(history);
    }

    private boolean hasPendingAudit(String auditType, String targetType, Integer targetId, Integer reporterId) {
        return auditMapper.findByTarget(targetType, targetId).stream()
                .anyMatch(audit -> Objects.equals(audit.getAudit_type(), auditType)
                        && Objects.equals(audit.getStatus(), "pending")
                        && (reporterId == null || Objects.equals(audit.getReporter_id(), reporterId)));
    }

    private boolean isBlank(String value) {
        return value == null || value.isBlank();
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (Exception e) {
            return "[]";
        }
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
                blankToAll(dto.getKeyword()) + ":" +
                blankToAll(dto.getSort_by()) + ":" +
                blankToAll(dto.getPeriod()) + ":p" +
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

