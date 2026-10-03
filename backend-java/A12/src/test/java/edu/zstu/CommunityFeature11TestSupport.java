package edu.zstu;

import com.github.pagehelper.PageInterceptor;
import edu.zstu.mapper.ComContentMapper;
import edu.zstu.mapper.ComInteractionMapper;
import edu.zstu.mapper.ComLikeMapper;
import org.apache.ibatis.plugin.Interceptor;
import org.mybatis.spring.SqlSessionFactoryBean;
import org.mybatis.spring.SqlSessionTemplate;
import org.springframework.core.io.ClassPathResource;
import org.springframework.core.io.support.PathMatchingResourcePatternResolver;
import org.springframework.jdbc.datasource.init.ResourceDatabasePopulator;

import javax.sql.DataSource;
import java.sql.Driver;
import java.util.Properties;

/**
 * 功能11 测试公共支撑：H2 内存库（MySQL 兼容模式）+ 生产 MyBatis XML（真实 SQL）+ PageHelper 拦截器。
 * 仅测试使用，替代外部 MySQL，保证 mvn test 离线可重复执行。
 *
 * [数据交互说明] - CommunityFeature11MapperTest / CommunityFeature11ApiTest: 构建 DataSource、Mapper、H2 schema
 */
final class CommunityFeature11TestSupport {

    private CommunityFeature11TestSupport() {
    }

    /** 建独立 H2 内存库并执行功能11 测试 schema（唯一索引与生产一致）。 */
    static DataSource buildDataSource(String dbName) throws Exception {
        String url = "jdbc:h2:mem:" + dbName
                + ";MODE=MySQL;DATABASE_TO_LOWER=TRUE;CASE_INSENSITIVE_IDENTIFIERS=TRUE;DB_CLOSE_DELAY=-1";
        org.springframework.jdbc.datasource.SimpleDriverDataSource ds = new org.springframework.jdbc.datasource.SimpleDriverDataSource();
        ds.setDriverClass((Class<? extends Driver>) Class.forName("org.h2.Driver"));
        ds.setUrl(url);
        ds.setUsername("sa");
        ds.setPassword("");
        new ResourceDatabasePopulator(new ClassPathResource("sql/feature11-h2-schema.sql")).execute(ds);
        return ds;
    }

    /** 基于生产 mapper XML 构建 SqlSessionTemplate（注册 PageInterceptor 使 PageHelper.startPage 正常消费）。 */
    static SqlSessionTemplate buildSession(DataSource dataSource) throws Exception {
        SqlSessionFactoryBean factoryBean = new SqlSessionFactoryBean();
        factoryBean.setDataSource(dataSource);
        factoryBean.setMapperLocations(new PathMatchingResourcePatternResolver().getResources(
                "classpath*:edu/zstu/mapper/Com*Mapper.xml"));
        PageInterceptor pageInterceptor = new PageInterceptor();
        pageInterceptor.setProperties(new Properties());
        factoryBean.setPlugins(new Interceptor[]{pageInterceptor});
        return new SqlSessionTemplate(factoryBean.getObject());
    }

    static ComContentMapper contentMapper(SqlSessionTemplate session) {
        return session.getMapper(ComContentMapper.class);
    }

    static ComInteractionMapper interactionMapper(SqlSessionTemplate session) {
        return session.getMapper(ComInteractionMapper.class);
    }

    static ComLikeMapper likeMapper(SqlSessionTemplate session) {
        return session.getMapper(ComLikeMapper.class);
    }
}
