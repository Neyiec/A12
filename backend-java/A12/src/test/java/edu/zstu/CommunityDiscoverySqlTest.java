package edu.zstu;

import edu.zstu.dto.ContentQueryDTO;
import org.apache.ibatis.builder.xml.XMLMapperBuilder;
import org.apache.ibatis.mapping.BoundSql;
import org.apache.ibatis.session.Configuration;
import org.junit.jupiter.api.Test;

import java.io.InputStream;

import static org.junit.jupiter.api.Assertions.*;

class CommunityDiscoverySqlTest {
    private static final String RESOURCE = "edu/zstu/mapper/ComContentMapper.xml";

    private BoundSql searchSql(ContentQueryDTO query) throws Exception {
        Configuration configuration = new Configuration();
        try (InputStream input = getClass().getClassLoader().getResourceAsStream(RESOURCE)) {
            assertNotNull(input, "社区内容 Mapper 不存在");
            new XMLMapperBuilder(input, configuration, RESOURCE, configuration.getSqlFragments()).parse();
        }
        return configuration.getMappedStatement("edu.zstu.mapper.ComContentMapper.searchPublic")
                .getBoundSql(query);
    }

    @Test
    void pptSearchFiltersBeforeRankingAndUsesCurrentViewer() throws Exception {
        ContentQueryDTO query = new ContentQueryDTO();
        query.setContent_type("ppt");
        query.setKeyword("分数");
        query.setSort("recommended");
        query.setViewer_id(7);
        String sql = searchSql(query).getSql();
        assertTrue(sql.contains("c.content_type = ?"));
        assertTrue(sql.contains("c.keywords LIKE"));
        assertTrue(sql.contains("mine.user_id = ?"));
        assertTrue(sql.indexOf("WHERE c.status = 'public'") < sql.indexOf("ORDER BY"));
        assertTrue(sql.contains("c.is_top DESC"));
    }

    @Test
    void hotRankingUsesSelectedWindowAndStableTieBreak() throws Exception {
        ContentQueryDTO query = new ContentQueryDTO();
        query.setSort("hot");
        query.setPeriod("month");
        String sql = searchSql(query).getSql();
        assertTrue(sql.contains("s.month_uses"));
        assertFalse(sql.contains("ORDER BY (COALESCE(s.week_uses"));
        assertTrue(sql.contains("c.id DESC"));
    }
}
