package edu.zstu;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.zstu.dto.ContentQueryDTO;
import edu.zstu.entity.Com_Content;
import edu.zstu.mapper.AdmAuditMapper;
import edu.zstu.mapper.ComContentMapper;
import edu.zstu.mapper.ComInteractionMapper;
import edu.zstu.mapper.ComLikeMapper;
import edu.zstu.service.BusinessLogService;
import edu.zstu.service.impl.CommunityServiceImpl;
import edu.zstu.service.ProjectService;
import edu.zstu.utils.PageResult;
import edu.zstu.utils.RedisCacheUtil;
import edu.zstu.utils.RedisRateLimiter;
import edu.zstu.vo.ContentVO;
import edu.zstu.vo.RankItemVO;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import org.springframework.data.redis.core.ZSetOperations;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.function.Supplier;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * 功能11 L1 单元测试：CommunityServiceImpl 点赞/排序解析/榜单读取/聚合任务逻辑（全 Mock）。
 * 用例编号见 doc/tests/feature11-test-plan.md §4 L1。
 */
class CommunityFeature11ServiceTest {

    private ComContentMapper contentMapper;
    private ComInteractionMapper interactionMapper;
    private ComLikeMapper comLikeMapper;
    private AdmAuditMapper auditMapper;
    private ProjectService projectService;
    private BusinessLogService businessLogService;
    private RedisCacheUtil redisCacheUtil;
    private StringRedisTemplate redisTemplate;
    private ValueOperations<String, String> valueOps;
    private ZSetOperations<String, String> zSetOps;
    private CommunityServiceImpl service;

    @BeforeEach
    @SuppressWarnings("unchecked")
    void setUp() {
        contentMapper = mock(ComContentMapper.class);
        interactionMapper = mock(ComInteractionMapper.class);
        comLikeMapper = mock(ComLikeMapper.class);
        auditMapper = mock(AdmAuditMapper.class);
        projectService = mock(ProjectService.class);
        businessLogService = mock(BusinessLogService.class);
        redisCacheUtil = mock(RedisCacheUtil.class);
        redisTemplate = mock(StringRedisTemplate.class);
        valueOps = mock(ValueOperations.class);
        zSetOps = mock(ZSetOperations.class);
        when(redisTemplate.opsForValue()).thenReturn(valueOps);
        when(redisTemplate.opsForZSet()).thenReturn(zSetOps);
        when(valueOps.get(anyString())).thenReturn(null);
        //限流器基础行为：计数 1 次、冷却锁获取成功、过期成功
        lenient().when(valueOps.increment(anyString())).thenReturn(1L);
        lenient().when(valueOps.setIfAbsent(anyString(), anyString(), any(Duration.class))).thenReturn(true);
        lenient().when(redisTemplate.expire(anyString(), any(Duration.class))).thenReturn(true);
        //缓存 getOrLoad 直通 loader（不读写真实 Redis）
        lenient().doAnswer(inv -> ((Supplier<?>) inv.getArgument(3)).get())
                .when(redisCacheUtil).getOrLoad(anyString(), any(com.fasterxml.jackson.core.type.TypeReference.class), any(Duration.class), any(Supplier.class));
        lenient().doAnswer(inv -> ((Supplier<?>) inv.getArgument(3)).get())
                .when(redisCacheUtil).getOrLoad(anyString(), any(Class.class), any(Duration.class), any(Supplier.class));

        service = new CommunityServiceImpl(contentMapper, interactionMapper, comLikeMapper, auditMapper,
                projectService, businessLogService, redisCacheUtil,
                new RedisRateLimiter(redisTemplate), redisTemplate, new ObjectMapper());
    }

    private Com_Content content(int id, String contentType, String status) {
        Com_Content c = new Com_Content();
        c.setId(id);
        c.setContent_type(contentType);
        c.setAuthor_id(1);
        c.setTitle("内容 " + id);
        c.setStatus(status);
        c.setVersion(1);
        c.setLike_count(0);
        c.setFavorite_count(0);
        c.setView_count(0);
        c.setUse_count(0);
        return c;
    }

    @SuppressWarnings("unchecked")
    private ZSetOperations.TypedTuple<String> tuple(String value, double score) {
        ZSetOperations.TypedTuple<String> t = mock(ZSetOperations.TypedTuple.class);
        when(t.getValue()).thenReturn(value);
        when(t.getScore()).thenReturn(score);
        return t;
    }

    private Map<String, Object> statRow(int id, int like, int fav, int use, int view) {
        Map<String, Object> row = new HashMap<>();
        row.put("id", id);
        row.put("like_cnt", like);
        row.put("fav_cnt", fav);
        row.put("use_cnt", use);
        row.put("view_cnt", view);
        return row;
    }

    private ContentQueryDTO queryDto(String sortBy, String period) {
        ContentQueryDTO dto = new ContentQueryDTO();
        dto.setSort_by(sortBy);
        dto.setPeriod(period);
        return dto;
    }

    // ---------- 点赞 ----------

    @Test
    void U01_likeSuccessInsertsIncrementsEvictsAndLogs() {
        when(contentMapper.findById(101)).thenReturn(content(101, "skill", "public"));

        service.like(101, 9);

        ArgumentCaptor<edu.zstu.entity.Com_Like> captor = ArgumentCaptor.forClass(edu.zstu.entity.Com_Like.class);
        verify(comLikeMapper).insert(captor.capture());
        assertEquals(9, captor.getValue().getUser_id());
        assertEquals("skill", captor.getValue().getTarget_type());
        assertEquals(101, captor.getValue().getTarget_id());
        verify(contentMapper).incrementLikeCountBy(101, 1);
        verify(redisCacheUtil).delete("community:item:101");
        verify(redisCacheUtil).deleteByPattern("community:public:*");
        verify(businessLogService).record(eq("operation"), eq("community"), eq("like"), eq("content"), eq(101));
    }

    @Test
    void U02_duplicateLikeIsIdempotentWithoutDoubleCount() {
        when(contentMapper.findById(101)).thenReturn(content(101, "skill", "public"));
        when(comLikeMapper.insert(any())).thenThrow(new DuplicateKeyException("uk_user_target"));

        assertDoesNotThrow(() -> service.like(101, 9));

        verify(contentMapper, never()).incrementLikeCountBy(anyInt(), anyLong());
    }

    @Test
    void U03_likeNonPublicContentRejectedBeforeRateLimitAndInsert() {
        when(contentMapper.findById(101)).thenReturn(content(101, "skill", "reviewing"));

        RuntimeException ex = assertThrows(RuntimeException.class, () -> service.like(101, 9));
        assertTrue(ex.getMessage().contains("Public content not found"));
        verify(comLikeMapper, never()).insert(any());
        verify(contentMapper, never()).incrementLikeCountBy(anyInt(), anyLong());
    }

    @Test
    void U04_likeRateLimitedWhenUserExceedsPerMinuteCap() {
        when(contentMapper.findById(101)).thenReturn(content(101, "skill", "public"));
        //第 21 次点击触发 RedisRateLimiter 阈值
        when(valueOps.increment(startsWith("community:rl:like:"))).thenReturn(21L);

        RuntimeException ex = assertThrows(RuntimeException.class, () -> service.like(101, 9));
        assertTrue(ex.getMessage().contains("点赞过于频繁"));
        verify(comLikeMapper, never()).insert(any());
    }

    @Test
    void U05_unlikeExistingDecrementsAndEvicts() {
        when(contentMapper.findById(101)).thenReturn(content(101, "skill", "public"));
        when(comLikeMapper.deleteByUserAndTarget(9, "skill", 101)).thenReturn(1);

        service.unlike(101, 9);

        verify(contentMapper).incrementLikeCountBy(101, -1);
        verify(redisCacheUtil).deleteByPattern("community:public:*");
        verify(businessLogService).record(eq("operation"), eq("community"), eq("unlike"), eq("content"), eq(101));
    }

    @Test
    void U06_unlikeMissingKeepsCountUntouched() {
        when(contentMapper.findById(101)).thenReturn(content(101, "skill", "public"));
        when(comLikeMapper.deleteByUserAndTarget(9, "skill", 101)).thenReturn(0);

        service.unlike(101, 9);

        verify(contentMapper, never()).incrementLikeCountBy(anyInt(), anyLong());
        verify(businessLogService, never()).record(anyString(), anyString(), anyString(), anyString(), anyInt());
    }

    // ---------- 列表排序解析 ----------

    @Test
    void U07_windowSortAddsAggregationJoinAndSince() {
        when(contentMapper.searchPublic(any(), anyString(), anyBoolean(), any())).thenReturn(List.of());

        service.listItems(queryDto("like", "week"), null);

        ArgumentCaptor<String> orderClause = ArgumentCaptor.forClass(String.class);
        ArgumentCaptor<Boolean> window = ArgumentCaptor.forClass(Boolean.class);
        ArgumentCaptor<LocalDateTime> since = ArgumentCaptor.forClass(LocalDateTime.class);
        verify(contentMapper).searchPublic(any(ContentQueryDTO.class), orderClause.capture(), window.capture(), since.capture());
        assertTrue(window.getValue());
        assertTrue(orderClause.getValue().contains("lik.like_cnt"));
        assertTrue(since.getValue().isAfter(LocalDateTime.now().minusDays(8)));
        assertTrue(since.getValue().isBefore(LocalDateTime.now().minusDays(6)));
    }

    @Test
    void U08_allPeriodSortUsesDenormalizedColumnWithoutWindow() {
        when(contentMapper.searchPublic(any(), anyString(), anyBoolean(), any())).thenReturn(List.of());

        service.listItems(queryDto("favorite", "all"), null);

        ArgumentCaptor<String> orderClause = ArgumentCaptor.forClass(String.class);
        ArgumentCaptor<Boolean> window = ArgumentCaptor.forClass(Boolean.class);
        verify(contentMapper).searchPublic(any(ContentQueryDTO.class), orderClause.capture(), window.capture(), isNull());
        assertFalse(window.getValue());
        assertTrue(orderClause.getValue().contains("favorite_count"));
    }

    @Test
    void U09_defaultSortKeepsLegacyBehaviour() {
        when(contentMapper.searchPublic(any(), anyString(), anyBoolean(), any())).thenReturn(List.of());

        service.listItems(queryDto(null, null), null);

        ArgumentCaptor<String> orderClause = ArgumentCaptor.forClass(String.class);
        ArgumentCaptor<Boolean> window = ArgumentCaptor.forClass(Boolean.class);
        verify(contentMapper).searchPublic(any(ContentQueryDTO.class), orderClause.capture(), window.capture(), isNull());
        assertFalse(window.getValue());
        assertEquals("is_top DESC, updated_at DESC", orderClause.getValue());
    }

    @Test
    void U10_illegalSortParamsRejected() {
        assertThrows(RuntimeException.class, () -> service.listItems(queryDto("bogus", "week"), null));
        assertThrows(RuntimeException.class, () -> service.listItems(queryDto("like", "bogus"), null));
        verify(contentMapper, never()).searchPublic(any(), anyString(), anyBoolean(), any());
    }

    @Test
    void U11_likedInjectedByUserAndFalseForAnonymous() {
        Com_Content c101 = content(101, "skill", "public");
        Com_Content c102 = content(102, "lesson_case", "public");
        when(contentMapper.searchPublic(any(), anyString(), anyBoolean(), any())).thenReturn(List.of(c101, c102));
        when(comLikeMapper.findLikedTargetIds(eq(9), eq("skill"), anyList())).thenReturn(List.of(101));
        when(comLikeMapper.findLikedTargetIds(eq(9), eq("lesson_case"), anyList())).thenReturn(List.of());

        PageResult<ContentVO> loggedIn = service.listItems(queryDto(null, null), 9);
        assertTrue(loggedIn.getRecords().get(0).isLiked());
        assertFalse(loggedIn.getRecords().get(1).isLiked());

        PageResult<ContentVO> anonymous = service.listItems(queryDto(null, null), null);
        assertFalse(anonymous.getRecords().get(0).isLiked());
        assertFalse(anonymous.getRecords().get(1).isLiked());
        verify(comLikeMapper, times(2)).findLikedTargetIds(anyInt(), anyString(), anyList()); //仅登录那次调用（每类型 1 次）
    }

    // ---------- 热门榜单 ----------

    @Test
    void U12_rankingsReadFromZsetInScoreOrder() {
        //先构造 tuple 再进入 when() 参数，避免嵌套 stubbing；LinkedHashSet 模拟 ZREVRANGE 的 score 降序
        ZSetOperations.TypedTuple<String> first = tuple("101", 12.4);
        ZSetOperations.TypedTuple<String> second = tuple("103", 9.8);
        when(zSetOps.reverseRangeWithScores(eq("community:rank:skill:week"), eq(0L), eq(9L)))
                .thenReturn(new LinkedHashSet<>(List.of(first, second)));
        when(contentMapper.findById(101)).thenReturn(content(101, "skill", "public"));
        when(contentMapper.findById(103)).thenReturn(content(103, "skill", "public"));
        when(comLikeMapper.countByUserAndTarget(9, "skill", 101)).thenReturn(1);
        when(comLikeMapper.countByUserAndTarget(9, "skill", 103)).thenReturn(0);

        List<RankItemVO> result = service.listRankings("skill", "week", 10, 9);

        assertEquals(2, result.size());
        assertEquals(1, result.get(0).getRank());
        assertEquals(12.4, result.get(0).getHot_score());
        assertEquals(101, result.get(0).getContent().getId());
        assertTrue(result.get(0).getContent().isLiked());
        assertEquals(2, result.get(1).getRank());
        assertFalse(result.get(1).getContent().isLiked());
    }

    @Test
    void U13_offlineContentFilteredFromRankingWithoutOccupyingRank() {
        ZSetOperations.TypedTuple<String> offline = tuple("102", 9.8);
        ZSetOperations.TypedTuple<String> online = tuple("101", 5.0);
        when(zSetOps.reverseRangeWithScores(anyString(), anyLong(), anyLong()))
                .thenReturn(new LinkedHashSet<>(List.of(offline, online)));
        when(contentMapper.findById(102)).thenReturn(content(102, "skill", "offline"));
        when(contentMapper.findById(101)).thenReturn(content(101, "skill", "public"));

        List<RankItemVO> result = service.listRankings("skill", "week", 10, null);

        assertEquals(1, result.size());
        assertEquals(1, result.get(0).getRank());
        assertEquals(101, result.get(0).getContent().getId());
    }

    @Test
    void U14_rankingsFallbackToDbAggregationWithWeightedScore() {
        when(zSetOps.reverseRangeWithScores(anyString(), anyLong(), anyLong())).thenReturn(null);
        when(contentMapper.selectRankCandidates(eq("skill"), any(LocalDateTime.class), anyInt(), anyInt()))
                .thenReturn(List.of(statRow(101, 2, 1, 1, 5), statRow(102, 0, 3, 0, 0)));
        when(contentMapper.findById(101)).thenReturn(content(101, "skill", "public"));
        when(contentMapper.findById(102)).thenReturn(content(102, "skill", "public"));

        List<RankItemVO> result = service.listRankings("skill", "week", 10, null);

        //score = like×3 + fav×2 + use×4 + view×0.2 → 6+2+4+1 = 13.0 / 6.0
        assertEquals(2, result.size());
        assertEquals(1, result.get(0).getRank());
        assertEquals(13.0, result.get(0).getHot_score(), 1e-9);
        assertEquals(6.0, result.get(1).getHot_score(), 1e-9);
    }

    @Test
    void U15_rankingParamsValidatedTypeNormalizedAndLimitCapped() {
        assertThrows(RuntimeException.class, () -> service.listRankings("skill", "bogus", 10, null));
        assertThrows(RuntimeException.class, () -> service.listRankings(null, "week", 10, null));
        when(zSetOps.reverseRangeWithScores(anyString(), anyLong(), anyLong())).thenReturn(null);
        when(contentMapper.selectRankCandidates(anyString(), any(), anyInt(), anyInt())).thenReturn(List.of());

        service.listRankings("case", "week", 99, null);

        ArgumentCaptor<String> key = ArgumentCaptor.forClass(String.class);
        ArgumentCaptor<Long> end = ArgumentCaptor.forClass(Long.class);
        verify(zSetOps).reverseRangeWithScores(key.capture(), eq(0L), end.capture());
        assertEquals("community:rank:lesson_case:week", key.getValue());
        assertEquals(49L, end.getValue());
    }

    @Test
    void U16_rebuildRankingsWritesZsetAndSurvivesPartialFailure() {
        when(contentMapper.selectRankCandidates(anyString(), any(), anyInt(), anyInt())).thenAnswer(inv -> {
            if ("skill".equals(inv.getArgument(0))) return List.of(statRow(7, 1, 0, 1, 0));
            if ("lesson_case".equals(inv.getArgument(0))) throw new RuntimeException("boom");
            return List.of();
        });

        assertDoesNotThrow(() -> service.rebuildRankings());

        //skill 三档全部重建（score = 1×3 + 0 + 1×4 + 0 = 7.0），lesson_case 失败被吞掉不影响 skill
        verify(zSetOps).add("community:rank:skill:day", "7", 7.0);
        verify(zSetOps).add("community:rank:skill:week", "7", 7.0);
        verify(zSetOps).add("community:rank:skill:month", "7", 7.0);
        verify(redisTemplate).delete("community:rank:skill:day");
        verify(redisTemplate, never()).delete(contains("lesson_case"));
        verify(zSetOps, never()).add(contains("lesson_case"), anyString(), anyDouble());
    }
}
