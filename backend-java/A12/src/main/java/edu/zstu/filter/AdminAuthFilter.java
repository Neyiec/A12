package edu.zstu.filter;

import com.fasterxml.jackson.core.type.TypeReference;
import edu.zstu.mapper.SysRoleMapper;
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
import java.util.List;

/**
 * 后台接口权限过滤器
 * 登录不限制角色；/api/v1/admin/** 下的每个接口按权限码鉴权：
 * 用户的有效角色（sys_user_role JOIN sys_role）→ 角色权限（sys_role_permission）→ 权限编码（sys_permission.perm_code）
 * 接口与权限码的对应关系见 PERM_RULES；请求未命中任何规则时默认拒绝。
 * 在校验 JWT Token 之后执行（@Order 高于 JwtAuthenticationFilter 的数字表示在其之后执行）
 */
@Slf4j
@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 20)
public class AdminAuthFilter implements Filter {

    private static final AntPathMatcher PATH_MATCHER = new AntPathMatcher();
    private static final String ADMIN_PATH_PATTERN = "/api/v1/admin/**";

    /**
     * 接口权限规则：HTTP 方法 + 路径模式 + 所需权限编码
     * 一个请求命中多条规则时，满足其中任意一条即放行
     */
    private record PermRule(String method, String pattern, String permCode) {}

    private static final List<PermRule> PERM_RULES = List.of(
            // 用户管理
            new PermRule("GET", "/api/v1/admin/users", "users:view"),
            new PermRule("GET", "/api/v1/admin/users/{id}", "users:view"),
            new PermRule("POST", "/api/v1/admin/users", "users:create"),
            new PermRule("POST", "/api/v1/admin/users/batch", "users:create"),
            new PermRule("PUT", "/api/v1/admin/users/{id}", "users:edit"),
            new PermRule("PATCH", "/api/v1/admin/users/{id}/status", "users:edit"),
            new PermRule("DELETE", "/api/v1/admin/users/{id}", "users:delete"),
            // 角色管理
            new PermRule("GET", "/api/v1/admin/roles", "roles:view"),
            new PermRule("POST", "/api/v1/admin/roles", "roles:create"),
            new PermRule("PUT", "/api/v1/admin/roles/{id}", "roles:edit"),
            new PermRule("DELETE", "/api/v1/admin/roles/{id}", "roles:delete"),
            new PermRule("PUT", "/api/v1/admin/users/{id}/roles", "roles:edit"),
            new PermRule("PUT", "/api/v1/admin/roles/{id}/permissions", "roles:configPerm"),
            // 内容审核与社区治理
            new PermRule("GET", "/api/v1/admin/questions", "audit:view"),
            new PermRule("GET", "/api/v1/admin/questions/{id}", "audit:view"),
            new PermRule("POST", "/api/v1/admin/questions", "resources:edit"),
            new PermRule("POST", "/api/v1/admin/questions/{id}/review", "audit:audit"),
            new PermRule("GET", "/api/v1/admin/moderation/tasks", "audit:view"),
            new PermRule("GET", "/api/v1/admin/moderation/tasks/{id}", "audit:view"),
            new PermRule("GET", "/api/v1/admin/moderation/content/{id}", "audit:view"),
            new PermRule("POST", "/api/v1/admin/moderation/tasks/{id}/decisions", "audit:audit"),
            new PermRule("PUT", "/api/v1/admin/community-items/{id}/status", "audit:audit"),
            new PermRule("PUT", "/api/v1/admin/community-items/{id}/recommendation", "audit:audit"),
            new PermRule("POST", "/api/v1/admin/community-items/reindex", "resources:edit"),
            new PermRule("POST", "/api/v1/admin/community-items/{id}/reindex", "resources:edit"),
            new PermRule("GET", "/api/v1/admin/reports", "audit:view"),
            new PermRule("GET", "/api/v1/admin/reports/{id}", "audit:view"),
            new PermRule("POST", "/api/v1/admin/reports/{id}/resolution", "audit:audit"),
            // 公共资源与知识库
            new PermRule("GET", "/api/v1/admin/public-resources", "resources:view"),
            new PermRule("GET", "/api/v1/admin/public-resources/{id}", "resources:view"),
            new PermRule("GET", "/api/v1/admin/public-resources/{id}/processing-status", "resources:view"),
            new PermRule("POST", "/api/v1/admin/public-resources/uploads", "resources:edit"),
            new PermRule("POST", "/api/v1/admin/public-resources/uploads/{id}/complete", "resources:edit"),
            new PermRule("POST", "/api/v1/admin/public-resources/ai-index/bootstrap", "resources:edit"),
            new PermRule("POST", "/api/v1/admin/public-resources/ai-index/{sourceType}/{resourceId}/reparse", "resources:edit"),
            new PermRule("PATCH", "/api/v1/admin/public-resources/{id}", "resources:edit"),
            new PermRule("PUT", "/api/v1/admin/public-resources/{id}/status", "resources:edit"),
            new PermRule("DELETE", "/api/v1/admin/public-resources/{id}", "resources:edit"),
            new PermRule("POST", "/api/v1/admin/public-resources/{id}/reparse", "resources:edit"),
            new PermRule("GET", "/api/v1/admin/public-resources/{id}/download-url", "resources:view"),
            // 数据看板与告警（告警的确认/处理暂归入 dashboard:stats，可按需调整）
            new PermRule("GET", "/api/v1/admin/dashboard", "dashboard:view"),
            new PermRule("GET", "/api/v1/admin/alerts", "dashboard:view"),
            new PermRule("GET", "/api/v1/admin/alerts/{id}", "dashboard:view"),
            new PermRule("POST", "/api/v1/admin/alerts/{id}/acknowledge", "dashboard:stats"),
            new PermRule("POST", "/api/v1/admin/alerts/{id}/resolve", "dashboard:stats"),
            // 系统配置与日志
            new PermRule("GET", "/api/v1/admin/ai-configs", "settings:view"),
            new PermRule("POST", "/api/v1/admin/ai-configs", "settings:modify"),
            new PermRule("POST", "/api/v1/admin/ai-configs/{id}/publish", "settings:modify"),
            new PermRule("POST", "/api/v1/admin/ai-configs/{id}/rollback", "settings:modify"),
            new PermRule("GET", "/api/v1/admin/security-policies", "settings:view"),
            new PermRule("PUT", "/api/v1/admin/security-policies/{id}", "settings:modify"),
            new PermRule("POST", "/api/v1/admin/security-policies/{id}/publish", "settings:modify"),
            new PermRule("GET", "/api/v1/admin/audit-logs", "settings:view"),
            new PermRule("GET", "/api/v1/admin/system-logs", "settings:view"),
            // 导出模板（属后台配置，归入 settings；如需单独权限可在 sys_permission 加码后调整此处）
            new PermRule("GET", "/api/v1/admin/export-templates", "settings:view"),
            new PermRule("GET", "/api/v1/admin/export-templates/{id}/download", "settings:view"),
            new PermRule("POST", "/api/v1/admin/export-templates", "settings:modify"),
            new PermRule("PATCH", "/api/v1/admin/export-templates/{id}", "settings:modify"),
            new PermRule("DELETE", "/api/v1/admin/export-templates/{id}", "settings:modify"),
            new PermRule("PUT", "/api/v1/admin/export-templates/{id}/status", "settings:modify")
    );

    private final SysRoleMapper roleMapper;
    private final RedisCacheUtil redisCacheUtil;

    public AdminAuthFilter(SysRoleMapper roleMapper, RedisCacheUtil redisCacheUtil) {
        this.roleMapper = roleMapper;
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

        // 收集该请求命中的权限规则
        List<String> requiredPerms = PERM_RULES.stream()
                .filter(rule -> rule.method().equals(req.getMethod())
                        && PATH_MATCHER.match(rule.pattern(), uri))
                .map(PermRule::permCode)
                .toList();
        if (requiredPerms.isEmpty()) {
            // 未登记的后台接口默认拒绝，避免新增接口被匿名放行
            log.warn("admin auth no permission rule userId={}, path={}, method={}", userId, req.getRequestURI(), req.getMethod());
            writeForbidden(res, "无访问权限");
            return;
        }

        // 用户的有效权限编码（Redis 缓存 10 分钟，值为权限编码数组 JSON）
        List<String> userPerms = redisCacheUtil.getOrLoad("user:auth:" + userId,
                new TypeReference<List<String>>() {},
                Duration.ofMinutes(10),
                () -> roleMapper.findPermCodesByUserId(userId));

        if (requiredPerms.stream().noneMatch(userPerms::contains)) {
            log.warn("admin auth forbidden userId={}, perms={}, required={}, path={}, method={}",
                    userId, userPerms, requiredPerms, req.getRequestURI(), req.getMethod());
            writeForbidden(res, "缺少权限: " + String.join(", ", requiredPerms));
            return;
        }

        log.debug("admin auth success userId={}, required={}, path={}, method={}",
                userId, requiredPerms, req.getRequestURI(), req.getMethod());
        chain.doFilter(request, response);
    }

    private void writeForbidden(HttpServletResponse res, String msg) throws IOException {
        res.setStatus(403);
        res.setContentType("application/json;charset=UTF-8");
        res.getWriter().write("{\"code\":403,\"message\":\"" + msg + "\",\"data\":null}");
    }
}
