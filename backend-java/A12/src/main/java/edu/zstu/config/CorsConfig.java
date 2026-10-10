package edu.zstu.config;

import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.Ordered;
import org.springframework.http.HttpHeaders;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;
import org.springframework.web.filter.CorsFilter;

import java.util.List;

/**
 * 全局 CORS 配置
 * [数据交互说明]
 * - 输入: 接收来自浏览器/WebView 的跨源请求（含 OPTIONS 预检）
 * - 输出: 预检返回 204 并携带 Access-Control-* 响应头，实际请求放行
 * - 说明: Capacitor App 的 WebView origin 为 https://localhost / capacitor://localhost，
 *         直连本网关属于跨源；以 CorsFilter Bean 挂在最高优先级，
 *         先于 JwtAuthenticationFilter(+10)/AdminAuthFilter(+20) 处理预检，
 *         两个认证过滤器自身也已放行 OPTIONS，双保险
 */
@Configuration
public class CorsConfig {

    /** 允许的来源：Capacitor Android/iOS WebView origin + 本地两个前端 dev 端口 */
    private static final List<String> ALLOWED_ORIGINS = List.of(
            "https://localhost",
            "http://localhost",
            "capacitor://localhost",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8888"
    );

    @Bean
    public FilterRegistrationBean<CorsFilter> corsFilterRegistration() {
        CorsConfiguration config = new CorsConfiguration();
        config.setAllowedOrigins(ALLOWED_ORIGINS);
        // 覆盖流式请求（SSE fetch 带 Authorization 头）与常规 CRUD
        config.setAllowedMethods(List.of("GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"));
        config.setAllowedHeaders(List.of("*"));
        // 放行前端需要读取的响应头：导出文件名 / OSS 直传 ETag 与请求 ID
        config.setExposedHeaders(List.of(HttpHeaders.CONTENT_DISPOSITION, "ETag", "x-oss-request-id"));
        config.setAllowCredentials(true);
        // 预检结果缓存 1 小时，减少 OPTIONS 往返
        config.setMaxAge(3600L);

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", config);

        FilterRegistrationBean<CorsFilter> bean = new FilterRegistrationBean<>(new CorsFilter(source));
        // 必须早于 JwtAuthenticationFilter（HIGHEST_PRECEDENCE + 10）
        bean.setOrder(Ordered.HIGHEST_PRECEDENCE);
        return bean;
    }
}
