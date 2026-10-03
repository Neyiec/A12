package edu.zstu;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.zstu.controller.CommunityController;
import edu.zstu.mapper.AdmAuditMapper;
import edu.zstu.mapper.ComContentMapper;
import edu.zstu.mapper.ComInteractionMapper;
import edu.zstu.mapper.ComLikeMapper;
import edu.zstu.service.BusinessLogService;
import edu.zstu.service.impl.CommunityServiceImpl;
import edu.zstu.service.ProjectService;
import edu.zstu.utils.CurrentHolder;
import edu.zstu.utils.RedisCacheUtil;
import edu.zstu.utils.RedisRateLimiter;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mybatis.spring.SqlSessionTemplate;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import org.springframework.data.redis.core.ZSetOperations;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import javax.sql.DataSource;
import java.util.function.Supplier;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * 功能11 L3 功能测试：MockMvc（standalone）→ 真实 CommunityServiceImpl → H2 真实 SQL 的全旅程验证。
 * Redis 相关组件以 Mock 替代（榜单走 DB 降级路径）；登录态经 CurrentHolder 模拟。
 * 用例编号见 doc/tests/feature11-test-plan.md §4 L3。
 */
class CommunityFeature11ApiTest {

    private JdbcTemplate jdbc;
    private SqlSessionTemplate session;
    private MockMvc mockMvc;

    @BeforeEach
    @SuppressWarnings("unchecked")
    void setUp() throws Exception {
        DataSource dataSource = CommunityFeature11TestSupport.buildDataSource(getClass().getSimpleName() + "-" + System.nanoTime());
        jdbc = new JdbcTemplate(dataSource);
        session = CommunityFeature11TestSupport.buildSession(dataSource);

        //Redis 依赖全部 Mock：缓存直通、榜单 ZSET 置空（走 DB 降级）、计数无存量
        RedisCacheUtil redisCacheUtil = mock(RedisCacheUtil.class);
        doAnswer(inv -> ((Supplier<?>) inv.getArgument(3)).get())
                .when(redisCacheUtil).getOrLoad(anyString(), any(com.fasterxml.jackson.core.type.TypeReference.class), any(), any(Supplier.class));
        doAnswer(inv -> ((Supplier<?>) inv.getArgument(3)).get())
                .when(redisCacheUtil).getOrLoad(anyString(), any(Class.class), any(), any(Supplier.class));
        doNothing().when(redisCacheUtil).delete(anyString());
        doNothing().when(redisCacheUtil).deleteByPattern(anyString());
        doNothing().when(redisCacheUtil).put(anyString(), any(), any());

        StringRedisTemplate redisTemplate = mock(StringRedisTemplate.class);
        ValueOperations<String, String> valueOps = mock(ValueOperations.class);
        ZSetOperations<String, String> zSetOps = mock(ZSetOperations.class);
        when(redisTemplate.opsForValue()).thenReturn(valueOps);
        when(redisTemplate.opsForZSet()).thenReturn(zSetOps);
        when(valueOps.get(anyString())).thenReturn(null);
        when(valueOps.increment(anyString())).thenReturn(1L);
        when(valueOps.setIfAbsent(anyString(), anyString(), any())).thenReturn(true);
        when(redisTemplate.expire(anyString(), any())).thenReturn(true);
        when(zSetOps.reverseRangeWithScores(anyString(), anyLong(), anyLong())).thenReturn(null);

        CommunityServiceImpl service = new CommunityServiceImpl(
                CommunityFeature11TestSupport.contentMapper(session),
                CommunityFeature11TestSupport.interactionMapper(session),
                CommunityFeature11TestSupport.likeMapper(session),
                mock(AdmAuditMapper.class),
                mock(ProjectService.class),
                mock(BusinessLogService.class),
                redisCacheUtil,
                new RedisRateLimiter(redisTemplate),
                redisTemplate,
                new ObjectMapper(), mock(edu.zstu.service.CommunityReviewEventPublisher.class));

        mockMvc = MockMvcBuilders.standaloneSetup(new CommunityController(service)).build();
    }

    @AfterEach
    void tearDown() {
        CurrentHolder.remove();
        jdbc.execute("DROP ALL OBJECTS");
    }

    /** 公开内容 + 6 个窗口内点赞（互动总数达标），冗余列与 com_like 同步维护，返回内容 id。 */
    private int seedQualifiedContent(String status) {
        jdbc.update("""
                INSERT INTO com_content(content_type, author_id, title, status, is_top, like_count)
                VALUES('skill', 1, '热门内容', ?, 0, 6)
                """, status);
        int id = jdbc.queryForObject("SELECT MAX(id) FROM com_content", Integer.class);
        for (int i = 1; i <= 6; i++) {
            jdbc.update("INSERT INTO com_like(user_id, target_type, target_id) VALUES(?, 'skill', ?)", 900 + i, id);
        }
        return id;
    }

    @Test
    void F01_likeWithoutLoginReturns401() throws Exception {
        mockMvc.perform(put("/api/v1/community/items/1/like"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(401));
        assertEquals(0, (int) jdbc.queryForObject("SELECT COUNT(*) FROM com_like", Integer.class));
    }

    @Test
    void F02_likeLifecycleIdempotentAndCountConsistent() throws Exception {
        int id = seedQualifiedContent("public");
        CurrentHolder.setCurrentId(9);

        //首次点赞：200，com_like 1 行，like_count 6(种子)+1=7
        mockMvc.perform(put("/api/v1/community/items/" + id + "/like"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200));
        assertEquals(1, (int) jdbc.queryForObject("SELECT COUNT(*) FROM com_like WHERE user_id = 9 AND target_id = " + id, Integer.class));
        assertEquals(7, (int) jdbc.queryForObject("SELECT like_count FROM com_content WHERE id = " + id, Integer.class));

        //重复点赞：幂等 200，计数不变（唯一索引兜底）
        mockMvc.perform(put("/api/v1/community/items/" + id + "/like"))
                .andExpect(jsonPath("$.code").value(200));
        assertEquals(7, (int) jdbc.queryForObject("SELECT like_count FROM com_content WHERE id = " + id, Integer.class));

        //取消：计数回落到种子值 6
        mockMvc.perform(delete("/api/v1/community/items/" + id + "/like"))
                .andExpect(jsonPath("$.code").value(200));
        assertEquals(6, (int) jdbc.queryForObject("SELECT like_count FROM com_content WHERE id = " + id, Integer.class));
        assertEquals(0, (int) jdbc.queryForObject("SELECT COUNT(*) FROM com_like WHERE user_id = 9 AND target_id = " + id, Integer.class));

        //再次取消：幂等 200，计数仍为 6
        mockMvc.perform(delete("/api/v1/community/items/" + id + "/like"))
                .andExpect(jsonPath("$.code").value(200));
        assertEquals(6, (int) jdbc.queryForObject("SELECT like_count FROM com_content WHERE id = " + id, Integer.class));
    }

    @Test
    void F03_likeNonPublicOrMissingContentReturns400() throws Exception {
        seedQualifiedContent("reviewing");
        CurrentHolder.setCurrentId(9);

        mockMvc.perform(put("/api/v1/community/items/1/like"))
                .andExpect(jsonPath("$.code").value(400));
        mockMvc.perform(delete("/api/v1/community/items/9999/like"))
                .andExpect(jsonPath("$.code").value(400));
    }

    @Test
    void F04_listItemsWithSortParamsReturnsEnhancedFields() throws Exception {
        seedQualifiedContent("public");

        mockMvc.perform(get("/api/v1/community/items").param("sort_by", "like").param("period", "week"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.total").value(1))
                .andExpect(jsonPath("$.data.records[0].like_count").value(6))
                .andExpect(jsonPath("$.data.records[0].favorite_count").exists())
                .andExpect(jsonPath("$.data.records[0].liked").value(false));
    }

    @Test
    void F05_illegalSortParamReturns400() throws Exception {
        mockMvc.perform(get("/api/v1/community/items").param("sort_by", "bogus"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(400));
    }

    @Test
    void F06_rankingsFallbackPathReturnsContinuousRanks() throws Exception {
        int id = seedQualifiedContent("public");
        jdbc.update("""
                INSERT INTO com_content(content_type, author_id, title, status, is_top, like_count)
                VALUES('skill', 1, '未达标内容', 'public', 0, 0)
                """);
        int weakId = jdbc.queryForObject("SELECT MAX(id) FROM com_content", Integer.class);
        jdbc.update("INSERT INTO com_like(user_id, target_type, target_id) VALUES(999, 'skill', ?)", weakId);

        mockMvc.perform(get("/api/v1/community/rankings").param("content_type", "skill").param("period", "week"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.length()").value(1))
                .andExpect(jsonPath("$.data[0].rank").value(1))
                .andExpect(jsonPath("$.data[0].hot_score").value(18.0))
                .andExpect(jsonPath("$.data[0].content.id").value(id))
                .andExpect(jsonPath("$.data[0].content.liked").value(false));
    }

    @Test
    void F07_rankingParamValidationReturns400() throws Exception {
        mockMvc.perform(get("/api/v1/community/rankings").param("period", "week"))
                .andExpect(status().isBadRequest()); //content_type 为必填参数，Spring 直接 400
        CurrentHolder.setCurrentId(9);
        mockMvc.perform(get("/api/v1/community/rankings").param("content_type", "skill").param("period", "bogus"))
                .andExpect(jsonPath("$.code").value(400));
    }

    @Test
    void F08_readEndpointsAnonymousAccessible() throws Exception {
        seedQualifiedContent("public");

        mockMvc.perform(get("/api/v1/community/items"))
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.records[0].liked").value(false));
        mockMvc.perform(get("/api/v1/community/rankings").param("content_type", "skill"))
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data[0].content.like_count").value(6));
    }
}
