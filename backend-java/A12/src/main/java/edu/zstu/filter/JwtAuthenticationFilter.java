package edu.zstu.filter;

import edu.zstu.utils.CurrentHolder;
import io.jsonwebtoken.Claims;
import edu.zstu.utils.JwtUtil;
import jakarta.servlet.*;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;
import org.springframework.util.AntPathMatcher;
import lombok.extern.slf4j.Slf4j;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import org.springframework.beans.factory.annotation.Value;
/**
 * JWT 认证过滤器
 * 拦截非 /api/v1/auth/** 的请求：
 * ① 校验 JWT 签名
 * ② 检查 Redis 中是否存在该令牌
 * ③ 将 userId 放入请求属性，供 Controller 使用
 */
@Slf4j
@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 10)
public class JwtAuthenticationFilter implements Filter {

    private static final AntPathMatcher PATH_MATCHER = new AntPathMatcher();
    private static final String[] AUTH_PATHS = {"/api/v1/auth/**"};

    private final JwtUtil jwtUtil;
    private final StringRedisTemplate redisTemplate;
    @Value("${a12.python.internal-key:}")
    private String internalKey;

    public JwtAuthenticationFilter(JwtUtil jwtUtil, StringRedisTemplate redisTemplate) {
        this.jwtUtil = jwtUtil;
        this.redisTemplate = redisTemplate;
    }

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
            throws IOException, ServletException {

        HttpServletRequest req = (HttpServletRequest) request;
        HttpServletResponse res = (HttpServletResponse) response;

        // 此唯一文件端点由 Controller 校验绑定方法、对象路径及有效期的签名。
        if ("/api/v1/storage/local-object".equals(req.getRequestURI())) {
            chain.doFilter(request, response);
            return;
        }

        if (req.getRequestURI().startsWith("/api/v1/internal/")) {
            String supplied = req.getHeader("X-A12-Internal-Key");
            if (internalKey == null || internalKey.isBlank() || supplied == null ||
                    !MessageDigest.isEqual(internalKey.getBytes(StandardCharsets.UTF_8), supplied.getBytes(StandardCharsets.UTF_8))) {
                writeUnauthorized(res, "内部服务凭据无效");
                return;
            }
            chain.doFilter(request, response);
            return;
        }

        // 跳过 OPTIONS 预检和认证相关路径
        if ("OPTIONS".equals(req.getMethod()) || isAuthPath(req.getRequestURI())) {
            chain.doFilter(request, response);
            return;
        }

        // 提取令牌
        String authHeader = req.getHeader("Authorization");
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            log.warn("jwt auth missing Authorization path={}, method={}", req.getRequestURI(), req.getMethod());
            writeUnauthorized(res, "请先登录");
            return;
        }
        String token = authHeader.substring(7);

        // 校验 JWT 签名
        Claims claims = jwtUtil.parseToken(token);
        if (claims == null) {
            log.warn("jwt auth invalid token path={}, method={}", req.getRequestURI(), req.getMethod());
            writeUnauthorized(res, "令牌无效");
            return;
        }
        Integer userId = claims.get("user_id", Integer.class);
        if (userId == null) {
            log.warn("jwt auth missing userId path={}, method={}", req.getRequestURI(), req.getMethod());
            writeUnauthorized(res, "令牌无效");
            return;
        }

        // 按用户 ID 查询存储的令牌，并比对是否一致
        String redisKey = "token:user:" + userId;
        String storedToken = redisTemplate.opsForValue().get(redisKey);
        if (storedToken == null || !storedToken.equals(token)) {
            log.warn("jwt auth token expired or replaced userId={}, path={}, method={}", userId, req.getRequestURI(), req.getMethod());
            writeUnauthorized(res, "令牌已过期或已被替换");
            return;
        }

        CurrentHolder.setCurrentId(userId);
        log.debug("jwt auth success userId={}, path={}, method={}", userId, req.getRequestURI(), req.getMethod());

        chain.doFilter(request, response);
        CurrentHolder.remove();
    }

    private boolean isAuthPath(String uri) {
        for (String pattern : AUTH_PATHS) {
            if (PATH_MATCHER.match(pattern, uri)) {
                return true;
            }
        }
        return false;
    }

    private void writeUnauthorized(HttpServletResponse res, String msg) throws IOException {
        res.setStatus(401);
        res.setContentType("application/json;charset=UTF-8");
        res.getWriter().write("{\"code\":401,\"message\":\"" + msg + "\",\"data\":null}");
    }
}

