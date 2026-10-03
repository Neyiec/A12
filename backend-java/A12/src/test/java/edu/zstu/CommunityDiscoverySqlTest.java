package edu.zstu;

import edu.zstu.dto.ContentQueryDTO;
import org.apache.ibatis.builder.xml.XMLMapperBuilder;
import org.apache.ibatis.mapping.BoundSql;
import org.apache.ibatis.session.Configuration;
import org.junit.jupiter.api.Test;

import java.io.InputStream;
import java.time.LocalDateTime;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class CommunityDiscoverySqlTest {
    private static final String RESOURCE = "edu/zstu/mapper/ComContentMapper.xml";

    private BoundSql searchSql(ContentQueryDTO query, String orderClause, boolean window) throws Exception {
        Configuration configuration = new Configuration();
        try (InputStream input = getClass().getClassLoader().getResourceAsStream(RESOURCE)) {
            assertNotNull(input, "社区内容 Mapper 不存在");
            new XMLMapperBuilder(input, configuration, RESOURCE, configuration.getSqlFragments()).parse();
        }
        return configuration.getMappedStatement("edu.zstu.mapper.ComContentMapper.searchPublic")
                .getBoundSql(Map.of("dto", query, "orderClause", orderClause,
                        "window", window, "since", LocalDateTime.now().minusDays(30)));
    }

    @Test
    void pptSearchFiltersBeforeRanking() throws Exception {
        ContentQueryDTO query = new ContentQueryDTO();
        query.setContent_type("ppt");
        query.setKeyword("分数");
        String sql = searchSql(query, "is_top DESC, updated_at DESC", false).getSql();
        assertTrue(sql.contains("c.content_type = ?"));
        assertTrue(sql.contains("c.keywords LIKE"));
        assertFalse(sql.contains("mine.user_id")); // 点赞态在列表缓存外按当前用户注入
        assertTrue(sql.indexOf("WHERE c.status = 'public'") < sql.indexOf("ORDER BY"));
        assertTrue(sql.contains("is_top DESC"));
    }

    @Test
    void monthlyUseRankingUsesWindowAggregation() throws Exception {
        ContentQueryDTO query = new ContentQueryDTO();
        query.setSort_by("use");
        query.setPeriod("month");
        String sql = searchSql(query,
                "is_top DESC, COALESCE(stat.use_cnt, 0) DESC, updated_at DESC",
                true).getSql();
        assertTrue(sql.contains("created_at >= ?"));
        assertTrue(sql.contains("COALESCE(stat.use_cnt, 0) DESC"));
    }
}
