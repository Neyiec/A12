package edu.zstu.filter;

import edu.zstu.entity.Sys_User;
import edu.zstu.mapper.SysUserMapper;
import edu.zstu.utils.CurrentHolder;
import edu.zstu.utils.RedisCacheUtil;
import jakarta.servlet.*;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.util.AntPathMatcher;
import lombok.extern.slf4j.Slf4j;

import java.io.IOException;
import java.time.Duration;

/**
 * 后台管理员权限过滤器
 * 拦截 /api/v1/admin/** 路径，校验当前用户是否为 admin 类型
 * 在校验 JWT Token 之后执行（@Order 高于 JwtAuthenticationFilter 的数字表示在其之后执行）
 */
@Slf4j
@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 20)
public class AdminAuthFilter implements Filter {

    private static final AntPathMatcher PATH_MATCHER = new AntPathMatcher();
    private static final String ADMIN_PATH_PATTERN = "/api/v1/admin/**";

    private final SysUserMapper userMapper;
    private final RedisCacheUtil redisCacheUtil;

    public AdminAuthFilter(SysUserMapper userMapper, RedisCacheUtil redisCacheUtil) {
        this.userMapper = userMapper;
        this.redisCacheUtil = redisCacheUtil;
    }

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
            throws IOException, ServletException {

        HttpServletRequest req = (HttpServletRequest) request;
        HttpServletResponse res = (HttpServletResponse) response;

        // 跳过 OPTIONS 预检请求
        if ("OPTIONS".equals(req.getMethod())) {
            chain.doFilter(request, response);
            return;
        }

        String uri = req.getRequestURI();
        if (!PATH_MATCHER.match(ADMIN_PATH_PATTERN, uri)) {
            chain.doFilter(request, response);
            return;
        }

        // 从 CurrentHolder 获取当前用户 ID（由 JwtAuthenticationFilter 设置）
        Integer userId = CurrentHolder.getCurrentId();
        if (userId == null) {
            log.warn("admin auth missing current user path={}, method={}", req.getRequestURI(), req.getMethod());
            writeForbidden(res, "未登录");
            return;
        }

        // 查询用户类型
        String userType = redisCacheUtil.getOrLoad("user:auth:" + userId, String.class, Duration.ofMinutes(10), () -> {
            Sys_User user = userMapper.findById(userId);
            return user == null ? "" : user.getUser_type();
        });
        if (!"admin".equals(userType)) {
            log.warn("admin auth forbidden userId={}, userType={}, path={}, method={}", userId, userType, req.getRequestURI(), req.getMethod());
            writeForbidden(res, "无管理员权限");
            return;
        }

        log.debug("admin auth success userId={}, path={}, method={}", userId, req.getRequestURI(), req.getMethod());
        chain.doFilter(request, response);
    }

    private void writeForbidden(HttpServletResponse res, String msg) throws IOException {
        res.setStatus(403);
        res.setContentType("application/json;charset=UTF-8");
        res.getWriter().write("{\"code\":403,\"message\":\"" + msg + "\",\"data\":null}");
    }
}

