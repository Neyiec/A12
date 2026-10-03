package edu.zstu;

import edu.zstu.dto.ContentQueryDTO;
import edu.zstu.entity.Com_Content;
import edu.zstu.mapper.ComContentMapper;
import edu.zstu.mapper.ComInteractionMapper;
import edu.zstu.mapper.ComLikeMapper;
import edu.zstu.entity.Com_Interaction;
import edu.zstu.entity.Com_Like;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mybatis.spring.SqlSessionTemplate;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.jdbc.core.JdbcTemplate;

import javax.sql.DataSource;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * 功能11 L2 集成测试：生产 mapper XML 跑在 H2（MySQL 兼容模式）上，验证真实 SQL。
 * 用例编号见 doc/tests/feature11-test-plan.md §4 L2。
 */
class CommunityFeature11MapperTest {

    private DataSource dataSource;
    private JdbcTemplate jdbc;
    private SqlSessionTemplate session;
    private ComContentMapper contentMapper;
    private ComLikeMapper likeMapper;
    private ComInteractionMapper interactionMapper;

    @BeforeEach
    void setUp() throws Exception {
        dataSource = CommunityFeature11TestSupport.buildDataSource(getClass().getSimpleName() + "-" + System.nanoTime());
        jdbc = new JdbcTemplate(dataSource);
        session = CommunityFeature11TestSupport.buildSession(dataSource);
        contentMapper = CommunityFeature11TestSupport.contentMapper(session);
        likeMapper = CommunityFeature11TestSupport.likeMapper(session);
        interactionMapper = CommunityFeature11TestSupport.interactionMapper(session);
    }

    @AfterEach
    void tearDown() {
        jdbc.execute("DROP ALL OBJECTS");
    }

    /** 插入内容并精确控制排序相关字段，返回 id。 */
    private int seedContent(String type, String status, int isTop, int likeCount, int favoriteCount, int useCount, int minutesAgo) {
        jdbc.update("""
                INSERT INTO com_content(content_type, author_id, title, description, subject, grade, lesson_type,
                                        status, is_top, view_count, use_count, like_count, favorite_count, updated_at)
                VALUES(?, 1, ?, '描述', '数学', '初中', '探究课', ?, ?, 0, ?, ?, ?, ?)
                """, type, "内容-" + minutesAgo, status, isTop, useCount, likeCount, favoriteCount,
                LocalDateTime.now().minusMinutes(minutesAgo));
        return jdbc.queryForObject("SELECT MAX(id) FROM com_content", Integer.class);
    }

    private void seedLike(int userId, int targetId, int minutesAgo) {
        jdbc.update("INSERT INTO com_like(user_id, target_type, target_id, created_at) VALUES(?, 'skill', ?, ?)",
                userId, targetId, LocalDateTime.now().minusMinutes(minutesAgo));
    }

    private void seedInteraction(String action, int userId, int targetId, int minutesAgo) {
        jdbc.update("INSERT INTO com_interaction(user_id, action_type, target_type, target_id, created_at) VALUES(?, ?, 'skill', ?, ?)",
                userId, action, targetId, LocalDateTime.now().minusMinutes(minutesAgo));
    }

    private List<Integer> searchIds(String sortBy, String period) {
        ContentQueryDTO dto = new ContentQueryDTO();
        dto.setSort_by(sortBy);
        dto.setPeriod(period);
        LocalDateTime since = "day".equals(period) ? LocalDateTime.now().minusDays(1)
                : "week".equals(period) ? LocalDateTime.now().minusDays(7)
                : "month".equals(period) ? LocalDateTime.now().minusDays(30)
                : null;
        boolean window = sortBy != null && !"all".equals(period);
        return contentMapper.searchPublic(dto,
                sortBy == null || "all".equals(period) ? (sortBy == null ? "is_top DESC, updated_at DESC"
                        : "is_top DESC, " + switch (sortBy) {
                            case "like" -> "like_count";
                            case "favorite" -> "favorite_count";
                            default -> "use_count";
                        } + " DESC, updated_at DESC")
                        : "is_top DESC, " + switch (sortBy) {
                            case "like" -> "COALESCE(lik.like_cnt, 0)";
                            case "favorite" -> "COALESCE(stat.fav_cnt, 0)";
                            default -> "COALESCE(stat.use_cnt, 0)";
                        } + " DESC, updated_at DESC",
                window, since).stream().map(Com_Content::getId).toList();
    }

    @Test
    void I01_defaultOrderMatchesLegacyBehaviour() {
        int top = seedContent("skill", "public", 1, 0, 0, 0, 300);
        int newest = seedContent("skill", "public", 0, 0, 0, 0, 10);
        int middle = seedContent("skill", "public", 0, 0, 0, 0, 60);

        assertEquals(List.of(top, newest, middle), searchIds(null, null));
    }

    @Test
    void I02_totalPeriodSortOrdersByDenormalizedColumn() {
        int low = seedContent("skill", "public", 0, 1, 0, 0, 30);
        int high = seedContent("skill", "public", 1, 9, 0, 0, 300);

        assertEquals(List.of(high, low), searchIds("like", "all"));

        int favLow = seedContent("lesson_case", "public", 0, 0, 1, 0, 30);
        int favHigh = seedContent("lesson_case", "public", 0, 0, 8, 0, 60);
        ContentQueryDTO dto = new ContentQueryDTO();
        dto.setSort_by("favorite");
        dto.setPeriod("all");
        List<Com_Content> result = contentMapper.searchPublic(dto, "is_top DESC, favorite_count DESC, updated_at DESC", false, null);
        //high(is_top=1) 置顶优先，其后按 favorite_count 降序
        assertEquals(List.of(high, favHigh, favLow, low), result.stream().map(Com_Content::getId).toList());
    }

    @Test
    void I03_windowSortOnlyCountsInteractionsInsideWindow() {
        //窗口内：A 2 赞、B 1 赞；C 冗余列 like_count 很高但窗口内无互动
        int a = seedContent("skill", "public", 0, 0, 0, 0, 500);
        int b = seedContent("skill", "public", 0, 0, 0, 0, 400);
        int c = seedContent("skill", "public", 0, 50, 0, 0, 300);
        seedLike(1, a, 60);
        seedLike(2, a, 70);
        seedLike(3, b, 80);

        assertEquals(List.of(a, b, c), searchIds("like", "week"));
        //全期排序走冗余列：C 的存量 like_count 使其居首；a/b 均为 0 时按 updated_at 降序（b 更新更晚）
        assertEquals(List.of(c, b, a), searchIds("like", "all"));
    }

    @Test
    void I04_rankCandidatesAggregateFilterAndOrder() {
        int a = seedContent("skill", "public", 0, 0, 0, 0, 100);
        int b = seedContent("skill", "public", 0, 0, 0, 0, 90);
        seedContent("skill", "public", 0, 0, 0, 0, 80);   //c：无互动，不达标
        seedContent("skill", "offline", 0, 0, 0, 0, 70);  //d：已下线
        seedLike(1, a, 10);
        seedLike(2, a, 11);
        seedLike(3, a, 12);
        seedInteraction("favorite", 4, a, 13);
        seedInteraction("derivation", 5, a, 14);
        for (int i = 1; i <= 10; i++) seedInteraction("view", 100 + i, a, 15);
        for (int i = 1; i <= 4; i++) seedLike(20 + i, b, 20);
        seedInteraction("derivation", 6, b, 21);

        List<Map<String, Object>> rows = contentMapper.selectRankCandidates("skill", LocalDateTime.now().minusDays(7), 5, 50);

        //a: like3×3+fav1×2+use1×4+view10×0.2 = 17.0（互动总数 5 达标）；b: like4×3+use1×4 = 16.0
        assertEquals(2, rows.size());
        assertEquals(a, ((Number) rows.get(0).get("id")).intValue());
        assertEquals(17.0, ((Number) rows.get(0).get("like_cnt")).doubleValue() * 3
                + ((Number) rows.get(0).get("fav_cnt")).doubleValue() * 2
                + ((Number) rows.get(0).get("use_cnt")).doubleValue() * 4
                + ((Number) rows.get(0).get("view_cnt")).doubleValue() * 0.2, 1e-9);
        assertEquals(b, ((Number) rows.get(1).get("id")).intValue());
        assertEquals(16.0, ((Number) rows.get(1).get("like_cnt")).doubleValue() * 3
                + ((Number) rows.get(1).get("fav_cnt")).doubleValue() * 2
                + ((Number) rows.get(1).get("use_cnt")).doubleValue() * 4
                + ((Number) rows.get(1).get("view_cnt")).doubleValue() * 0.2, 1e-9);
    }

    @Test
    void I05_uniqueIndexRejectsDuplicateLike() {
        likeMapper.insert(new Com_Like(null, 9, "skill", 101, null));

        assertThrows(RuntimeException.class, () -> likeMapper.insert(new Com_Like(null, 9, "skill", 101, null)));
        assertEquals(1, (int) jdbc.queryForObject("SELECT COUNT(*) FROM com_like WHERE user_id = 9 AND target_id = 101", Integer.class));
    }

    @Test
    void I06_incrementLikeCountClampedAtZero() {
        int id = seedContent("skill", "public", 0, 0, 0, 0, 10);

        contentMapper.incrementLikeCountBy(id, 3);
        assertEquals(3, (int) jdbc.queryForObject("SELECT like_count FROM com_content WHERE id = " + id, Integer.class));

        contentMapper.incrementLikeCountBy(id, -5);
        assertEquals(0, (int) jdbc.queryForObject("SELECT like_count FROM com_content WHERE id = " + id, Integer.class));
    }

    @Test
    void I07_findLikedTargetIdsReturnsExactHits() {
        int a = seedContent("skill", "public", 0, 0, 0, 0, 10);
        seedLike(9, a, 5);
        seedLike(9, 999, 5);
        seedLike(8, 999, 5);

        List<Integer> liked = likeMapper.findLikedTargetIds(9, "skill", List.of(a, 999, 888));

        assertEquals(List.of(a, 999), liked);
    }
}
