package edu.zstu.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import edu.zstu.dto.*;
import edu.zstu.entity.Sys_Permission;
import edu.zstu.entity.Sys_Role;
import edu.zstu.entity.Sys_User;
import edu.zstu.mapper.SysRoleMapper;
import edu.zstu.mapper.SysUserMapper;
import edu.zstu.service.AdminUserService;
import edu.zstu.service.BusinessLogService;
import edu.zstu.utils.CurrentHolder;
import edu.zstu.utils.PageResult;
import edu.zstu.utils.PasswordUtil;
import edu.zstu.utils.RedisCacheUtil;
import edu.zstu.vo.UserVO;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;
import java.time.Duration;
import java.time.LocalDateTime;
import java.util.stream.Collectors;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Service
public class AdminUserServiceImpl implements AdminUserService {

    private final SysUserMapper userMapper;
    private final SysRoleMapper roleMapper;
    private final PasswordUtil passwordUtil;
    private final BusinessLogService businessLogService;
    private final RedisCacheUtil redisCacheUtil;
    private final ObjectMapper objectMapper;

    public AdminUserServiceImpl(SysUserMapper userMapper, SysRoleMapper roleMapper,
                                PasswordUtil passwordUtil, BusinessLogService businessLogService,
                                RedisCacheUtil redisCacheUtil, ObjectMapper objectMapper) {
        this.userMapper = userMapper;
        this.roleMapper = roleMapper;
        this.passwordUtil = passwordUtil;
        this.businessLogService = businessLogService;
        this.redisCacheUtil = redisCacheUtil;
        this.objectMapper = objectMapper;
    }

    // ==================== API-75 分页查询用户 ====================

    @Override
    public PageResult<UserVO> listUsers(UserQueryDTO dto) {
        log.info("listUsers keyword={}, roleCode={}, isActive={}, page={}, size={}", dto.getKeyword(), dto.getUser_type(), dto.getIs_active(), dto.getPage(), dto.getSize());
        PageHelper.startPage(dto.getPage(), dto.getSize());
        List<Sys_User> list = userMapper.findByQuery(dto);
        PageInfo<Sys_User> info = new PageInfo<>(list);

        List<UserVO> records = info.getList().stream().map(this::toUserVO).toList();
        fillUserRoles(records);
        PageResult<UserVO> r = new PageResult<>();
        r.setTotal(info.getTotal()); r.setPage(dto.getPage());
        r.setSize(dto.getSize()); r.setRecords(records);
        return r;
    }

    // ==================== API-76 获取用户详情 ====================

    @Override
    public UserVO getUser(Integer id) {
        log.info("getUser userId={}", id);
        Sys_User u = userMapper.findById(id);
        if (u == null) throw new RuntimeException("用户不存在");
        UserVO vo = toUserVO(u);
        fillUserRoles(List.of(vo));
        return vo;
    }

    // ==================== API-77 启用/停用/锁定用户 ====================

    @Override
    @Transactional
    public UserVO updateUserStatus(Integer id, UserStatusDTO dto) {
        log.info("updateUserStatus userId={}, isActive={}", id, dto.getIs_active());
        Sys_User u = userMapper.findById(id);
        if (u == null) throw new RuntimeException("用户不存在");
        userMapper.updateActiveStatus(id, dto.getIs_active());
        u.setIs_active(dto.getIs_active());
        evictUserCache(u);
        log.info("updateUserStatus success userId={}, isActive={}", id, dto.getIs_active());
        businessLogService.record("operation", "admin_user", "update_status", "user", id,
                Map.of("is_active", dto.getIs_active()));
        UserVO vo = toUserVO(u);
        fillUserRoles(List.of(vo));
        return vo;
    }

    // ==================== API-82A 更新用户信息 ====================

    @Override
    @Transactional
    public UserVO updateUser(Integer id, UserDTO dto) {
        log.info("updateUser userId={}, username={}, roles={}", id, dto.getUsername(), dto.getRoles());
        Sys_User u = userMapper.findById(id);
        if (u == null) throw new RuntimeException("用户不存在");

        // 用户名变更时查重（findByUsername 已排除软删除用户）
        if (dto.getUsername() != null && !dto.getUsername().isBlank()
                && !dto.getUsername().equals(u.getUsername())
                && userMapper.findByUsername(dto.getUsername()) != null) {
            throw new RuntimeException("用户名已存在");
        }

        // 只覆盖传入的字段；账号启停走 updateUserStatus，user_type 已废弃不落库
        if (dto.getUsername() != null) u.setUsername(dto.getUsername());
        if (dto.getReal_name() != null) u.setReal_name(dto.getReal_name());
        if (dto.getPhone() != null) u.setPhone(dto.getPhone());
        if (dto.getEmail() != null) u.setEmail(dto.getEmail());
        if (dto.getAvatar() != null) u.setAvatar(dto.getAvatar());

        // 传入明文 password 时重置密码，否则保持原密码
        if (dto.getPassword() != null && !dto.getPassword().isBlank()) {
            u.setPassword_hash(passwordUtil.hash(dto.getPassword()));
            u.setPassword_changed_at(LocalDateTime.now());
        }

        // 传入 roles 时整体重建用户-角色关联
        boolean rolesChanged = false;
        List<Sys_Role> newRoles = null;
        if (dto.getRoles() != null) {
            newRoles = parseRoleCodes(dto.getRoles());
            roleMapper.deleteUserRoles(id);
            assignRoles(u.getId(), newRoles);
            rolesChanged = true;
        }

        userMapper.update(u);
        evictUserCache(u);
        if (rolesChanged) redisCacheUtil.delete("admin:roles");
        log.info("updateUser success userId={}", id);
        Map<String, Object> logData = new HashMap<>();
        logData.put("username", u.getUsername());
        if (rolesChanged) logData.put("roles", newRoles.stream().map(Sys_Role::getRole_code).toList());
        businessLogService.record("operation", "admin_user", "update", "user", id, logData);
        UserVO vo = toUserVO(u);
        fillUserRoles(List.of(vo));
        return vo;
    }

    // ==================== API-82B 删除用户 ====================

    @Override
    @Transactional
    public void deleteUser(Integer id) {
        log.info("deleteUser userId={}", id);
        Sys_User u = userMapper.findById(id);
        if (u == null) throw new RuntimeException("用户不存在");
        if (id.equals(CurrentHolder.getCurrentId())) throw new RuntimeException("不能删除当前登录账号");

        userMapper.deleteById(id); // 软删除：置 deleted_at 并停用（sys_user_role 关联行由外键级联清理）
        evictUserCache(u);
        redisCacheUtil.delete("token:user:" + id); // 使该用户的登录态失效
        redisCacheUtil.delete("admin:roles");
        log.info("deleteUser success userId={}", id);
        businessLogService.record("operation", "admin_user", "delete", "user", id,
                Map.of("username", u.getUsername()));
    }

    // ==================== API-78 创建单个后台账号 ====================

    @Override
    @Transactional
    public UserVO createUser(UserDTO dto) {
        log.info("createUser username={}, roles={}", dto.getUsername(), dto.getRoles());
        if (dto.getUsername() == null || dto.getReal_name() == null || dto.getRoles() == null) {
            throw new RuntimeException("缺少必填字段: username, real_name, roles");
        }
        if (userMapper.findByUsername(dto.getUsername()) != null) {
            throw new RuntimeException("用户名已存在");
        }
        List<Sys_Role> roles = parseRoleCodes(dto.getRoles());
        if (roles.isEmpty()) throw new RuntimeException("请至少选择一个角色");

        String hashedPassword = passwordUtil.hash(dto.getPassword() != null ? dto.getPassword() : "123456");
        Sys_User user = new Sys_User();
        BeanUtil.copyProperties(dto, user);
        user.setPassword_hash(hashedPassword);
        user.setIs_active(1);
        userMapper.insert(user);
        assignRoles(user.getId(), roles);
        evictUserCache(user);
        redisCacheUtil.delete("admin:roles");
        log.info("createUser success userId={}, username={}", user.getId(), user.getUsername());
        businessLogService.record("operation", "admin_user", "create", "user", user.getId(),
                Map.of("username", user.getUsername(), "roles", dto.getRoles()));
        UserVO vo = toUserVO(user);
        fillUserRoles(List.of(vo));
        return vo;
    }

    // ==================== API-79 批量创建后台账号 ====================

    @Override
    @Transactional
    public Map<String, Object> batchCreateUsers(BatchCreateUsersDTO dto) {
        log.info("batchCreateUsers called");
        List<Map<String, Object>> results = new ArrayList<>();
        List<Map<String, Object>> userList;

        try {
            List<Map<String, Object>> parsed = objectMapper.readValue(
                    dto.getUsers(), new TypeReference<List<Map<String, Object>>>() {});
            userList = parsed;
        } catch (Exception e) {
            throw new RuntimeException("用户列表JSON解析失败");
        }

        for (Map<String, Object> item : userList) {
            Map<String, Object> result = new HashMap<>();
            String username = (String) item.get("username");
            result.put("username", username);
            try {
                UserDTO userDTO = new UserDTO();
                BeanUtil.copyProperties(item, userDTO);

                if (username == null || userDTO.getReal_name() == null) {
                    throw new RuntimeException("缺少必填字段");
                }
                if (userMapper.findByUsername(username) != null) {
                    throw new RuntimeException("用户名已存在");
                }

                String password = userDTO.getPassword() != null ? userDTO.getPassword() : "123456";
                String hashedPassword = passwordUtil.hash(password);
                Sys_User user = new Sys_User();
                BeanUtil.copyProperties(userDTO, user);
                user.setPassword_hash(hashedPassword);
                user.setIs_active(1);
                userMapper.insert(user);
                // 角色可选：传了 roles 就按角色编码挂到 sys_user_role
                if (userDTO.getRoles() != null && !userDTO.getRoles().isBlank()) {
                    assignRoles(user.getId(), parseRoleCodes(userDTO.getRoles()));
                }
                evictUserCache(user);
                redisCacheUtil.delete("admin:roles");
                businessLogService.record("operation", "admin_user", "batch_create", "user", user.getId(),
                        Map.of("username", username));

                result.put("success", true);
                result.put("initial_credentials", Map.of("username", username, "password", password));
            } catch (Exception e) {
                result.put("success", false);
                result.put("error", e.getMessage());
            }
            results.add(result);
        }

        return Map.of("results", results);
    }

    // ==================== API-80 查询角色列表 ====================

    @Override
    public List<Map<String, Object>> listRoles() {
        log.info("listRoles");
        return redisCacheUtil.getOrLoad("admin:roles",
                new TypeReference<List<Map<String, Object>>>() {},
                Duration.ofMinutes(10), this::loadRoles);
    }

    private List<Map<String, Object>> loadRoles() {
        List<Sys_Role> roles = roleMapper.findAllRoles();
        List<Sys_Permission> allPermissions = roleMapper.findAllPermissions();
        // 各角色有效成员数（role_code -> count），随角色列表一起缓存
        Map<String, Object> memberCounts = new HashMap<>();
        for (Map<String, Object> row : roleMapper.countUsersGroupByRole()) {
            memberCounts.put(String.valueOf(row.get("role_code")), row.get("user_count"));
        }
        List<Map<String, Object>> roleList = new ArrayList<>();
        for (Sys_Role role : roles) {
            Set<String> granted = roleMapper.findPermissionsByRoleId(role.getId()).stream()
                    .map(Sys_Permission::getPerm_code)
                    .collect(Collectors.toSet());
            Map<String, Object> entry = new LinkedHashMap<>();
            entry.put("role_id", role.getId());
            entry.put("role_code", role.getRole_code());
            entry.put("role_name", role.getRole_name());
            entry.put("description", role.getDescription());
            entry.put("permissions", buildPermissionMatrix(allPermissions, granted));
            entry.put("audit_scope", "");
            entry.put("status", role.getStatus());
            entry.put("member_count", memberCounts.getOrDefault(role.getRole_code(), 0));
            entry.put("created_at", role.getCreated_at());
            roleList.add(entry);
        }
        return roleList;
    }

    // ==================== API-80A 创建角色 ====================

    @Override
    @Transactional
    public Map<String, Object> createRole(RoleDTO dto) {
        log.info("createRole roleCode={}, roleName={}", dto.getRole_code(), dto.getRole_name());
        String roleCode = dto.getRole_code() == null ? "" : dto.getRole_code().trim();
        String roleName = dto.getRole_name() == null ? "" : dto.getRole_name().trim();
        String description = dto.getDescription();
        if (roleCode.isEmpty() || roleName.isEmpty()) {
            throw new RuntimeException("缺少必填字段: role_code, role_name");
        }
        if (!roleCode.matches("^[a-z][a-z0-9_]{1,49}$")) {
            throw new RuntimeException("role_code 仅允许小写字母开头，可包含小写字母/数字/下划线");
        }
        if (roleName.length() > 50) throw new RuntimeException("role_name 不能超过 50 个字符");
        if (description != null && description.length() > 255) throw new RuntimeException("description 不能超过 255 个字符");
        if (roleMapper.findRoleByCode(roleCode) != null) {
            throw new RuntimeException("角色编码已存在: " + roleCode);
        }
        // 名称查重 + 计算默认排序（追加到现有角色末尾）
        List<Sys_Role> existing = roleMapper.findAllRoles();
        if (existing.stream().anyMatch(r -> roleName.equals(r.getRole_name()))) {
            throw new RuntimeException("角色名称已存在: " + roleName);
        }
        int maxSort = existing.stream().mapToInt(Sys_Role::getSort_order).max().orElse(0);

        Sys_Role role = new Sys_Role();
        role.setRole_code(roleCode);
        role.setRole_name(roleName);
        role.setDescription(description);
        role.setSort_order(dto.getSort_order() != null ? dto.getSort_order() : maxSort + 1);
        role.setStatus(dto.getStatus() != null ? dto.getStatus() : 1);
        role.setCreated_at(LocalDateTime.now());
        roleMapper.insertRole(role);
        redisCacheUtil.delete("admin:roles");
        log.info("createRole success roleId={}, roleCode={}", role.getId(), role.getRole_code());
        businessLogService.record("operation", "admin_role", "create", "role", role.getId(),
                Map.of("role_code", role.getRole_code(), "role_name", role.getRole_name()));

        // 返回与 API-80 列表项一致的结构，便于前端直接插入列表
        return toRoleEntry(role, 0);
    }

    // ==================== API-80B 更新角色信息 ====================

    @Override
    @Transactional
    public Map<String, Object> updateRole(Integer id, RoleUpdateDTO dto) {
        log.info("updateRole roleId={}, roleName={}, status={}", id, dto.getRole_name(), dto.getStatus());
        Sys_Role role = roleMapper.findRoleById(id);
        if (role == null) throw new RuntimeException("角色不存在");

        boolean changed = false;
        boolean statusChanged = false;

        if (dto.getRole_name() != null) {
            String roleName = dto.getRole_name().trim();
            if (roleName.isEmpty()) throw new RuntimeException("role_name 不能为空");
            if (roleName.length() > 50) throw new RuntimeException("role_name 不能超过 50 个字符");
            if (!roleName.equals(role.getRole_name())) {
                boolean duplicated = roleMapper.findAllRoles().stream()
                        .anyMatch(r -> r.getId() != id && roleName.equals(r.getRole_name()));
                if (duplicated) throw new RuntimeException("角色名称已存在: " + roleName);
                role.setRole_name(roleName);
                changed = true;
            }
        }
        if (dto.getDescription() != null) {
            if (dto.getDescription().length() > 255) throw new RuntimeException("description 不能超过 255 个字符");
            role.setDescription(dto.getDescription());
            changed = true;
        }
        if (dto.getSort_order() != null) {
            role.setSort_order(dto.getSort_order());
            changed = true;
        }
        if (dto.getStatus() != null) {
            if (dto.getStatus() != 0 && dto.getStatus() != 1) throw new RuntimeException("status 仅允许 0 或 1");
            if (dto.getStatus() != role.getStatus()) {
                role.setStatus(dto.getStatus());
                changed = true;
                statusChanged = true;
            }
        }

        if (changed) {
            roleMapper.updateRole(role);
            redisCacheUtil.delete("admin:roles");
            // 启停角色会改变持有者的有效权限集合，需同步清除其鉴权缓存
            if (statusChanged) {
                for (Integer uid : roleMapper.findUserIdsByRoleId(id)) {
                    redisCacheUtil.delete("user:auth:" + uid);
                }
            }
            log.info("updateRole success roleId={}", id);
            Map<String, Object> logData = new HashMap<>();
            logData.put("role_code", role.getRole_code());
            if (dto.getRole_name() != null) logData.put("role_name", role.getRole_name());
            if (dto.getStatus() != null) logData.put("status", role.getStatus());
            businessLogService.record("operation", "admin_role", "update", "role", id, logData);
        }
        return toRoleEntry(role, getMemberCount(role.getRole_code()));
    }

    // ==================== API-80C 删除角色 ====================

    @Override
    @Transactional
    public void deleteRole(Integer id) {
        log.info("deleteRole roleId={}", id);
        Sys_Role role = roleMapper.findRoleById(id);
        if (role == null) throw new RuntimeException("角色不存在");

        // 必须在删除前取出持有者：删除后 sys_user_role 关联行被外键级联清理，将无从查询
        List<Integer> memberIds = roleMapper.findUserIdsByRoleId(id);

        roleMapper.deleteRoleById(id); // sys_user_role / sys_role_permission 级联清理
        redisCacheUtil.delete("admin:roles");
        // 持有该角色的用户有效权限集合发生变化，清除其鉴权缓存（下次请求重新计算，可能失去后台访问权）
        for (Integer uid : memberIds) {
            redisCacheUtil.delete("user:auth:" + uid);
        }
        log.info("deleteRole success roleId={}, roleCode={}, affectedMembers={}", id, role.getRole_code(), memberIds.size());
        businessLogService.record("operation", "admin_role", "delete", "role", id,
                Map.of("role_code", role.getRole_code(), "role_name", role.getRole_name(),
                        "affected_members", memberIds.size()));
    }

    // ==================== API-81 分配角色 ====================

    @Override
    @Transactional
    public UserVO assignRoles(Integer id, AssignRolesDTO dto) {
        log.info("assignRoles userId={}, roles={}", id, dto.getRoles());
        Sys_User u = userMapper.findById(id);
        if (u == null) throw new RuntimeException("用户不存在");
        List<Sys_Role> roles = parseRoleCodes(dto.getRoles());

        roleMapper.deleteUserRoles(id);
        assignRoles(u.getId(), roles);
        evictUserCache(u);
        redisCacheUtil.delete("admin:roles");
        log.info("assignRoles success userId={}", id);
        businessLogService.record("operation", "admin_user", "assign_roles", "user", id,
                Map.of("roles", dto.getRoles()));
        UserVO vo = toUserVO(u);
        fillUserRoles(List.of(vo));
        return vo;
    }

    // ==================== API-82 配置角色权限 ====================

    @Override
    @Transactional
    public void updateRolePermissions(Integer id, RolePermissionsDTO dto) {
        log.info("updateRolePermissions roleId={}", id);
        Sys_Role role = roleMapper.findRoleById(id);
        if (role == null) throw new RuntimeException("角色不存在");

        // 解析前端权限矩阵，收集被授权的权限编码
        Set<String> grantedCodes = parseGrantedPermCodes(dto.getPermissions());
        List<Sys_Permission> allPermissions = roleMapper.findAllPermissions();
        Map<String, Integer> permIdByCode = allPermissions.stream()
                .collect(Collectors.toMap(Sys_Permission::getPerm_code, Sys_Permission::getId));
        for (String code : grantedCodes) {
            if (!permIdByCode.containsKey(code)) throw new RuntimeException("未知权限: " + code);
        }

        roleMapper.deleteRolePermissions(id);
        for (String code : grantedCodes) {
            roleMapper.insertRolePermission(id, permIdByCode.get(code));
        }

        // 该角色的鉴权缓存（user:auth:*）与角色列表缓存一并失效
        for (Integer uid : roleMapper.findUserIdsByRoleId(id)) {
            redisCacheUtil.delete("user:auth:" + uid);
        }
        log.info("updateRolePermissions success roleId={}, granted={}", id, grantedCodes.size());
        businessLogService.record("operation", "admin_user", "update_role_permissions", "role", id,
                Map.of("permissions", dto.getPermissions()));
        redisCacheUtil.delete("admin:roles");
    }

    // ==================== 内部辅助 ====================

    private UserVO toUserVO(Sys_User u) {
        UserVO vo = new UserVO();
        BeanUtil.copyProperties(u, vo);
        return vo;
    }

    /**
     * 批量装配 VO 的角色字段：
     * roles = 角色编码数组 JSON（按 sort_order 排序），user_type = 首个角色编码（主角色，兼容前端展示）
     */
    private void fillUserRoles(List<UserVO> vos) {
        List<Integer> ids = vos.stream().map(UserVO::getId).filter(Objects::nonNull).toList();
        if (ids.isEmpty()) return;
        Map<Integer, List<Sys_Role>> rolesByUser = new LinkedHashMap<>();
        for (Map<String, Object> row : roleMapper.findUserRolesByUserIds(ids)) {
            int userId = ((Number) row.get("user_id")).intValue();
            Sys_Role role = new Sys_Role();
            role.setId(((Number) row.get("role_id")).intValue());
            role.setRole_code((String) row.get("role_code"));
            role.setRole_name((String) row.get("role_name"));
            role.setSort_order(((Number) row.get("sort_order")).intValue());
            rolesByUser.computeIfAbsent(userId, k -> new ArrayList<>()).add(role);
        }
        for (UserVO vo : vos) {
            List<Sys_Role> roles = rolesByUser.getOrDefault(vo.getId(), List.of());
            List<String> codes = roles.stream().map(Sys_Role::getRole_code).toList();
            vo.setRoles(toJson(codes));
            vo.setUser_type(codes.isEmpty() ? null : codes.get(0));
        }
    }

    /** 解析角色编码数组 JSON 并校验角色存在，返回对应 sys_role 记录 */
    private List<Sys_Role> parseRoleCodes(String rolesJson) {
        List<String> codes;
        try {
            codes = objectMapper.readValue(rolesJson == null ? "[]" : rolesJson,
                    new TypeReference<List<String>>() {});
        } catch (Exception e) {
            throw new RuntimeException("roles 格式错误，应为角色编码数组 JSON");
        }
        if (codes.isEmpty()) return List.of();
        List<Sys_Role> roles = new ArrayList<>();
        for (String code : codes) {
            Sys_Role role = roleMapper.findRoleByCode(code);
            if (role == null) throw new RuntimeException("角色不存在: " + code);
            if (role.getStatus() != 1) throw new RuntimeException("角色已停用: " + code);
            roles.add(role);
        }
        return roles;
    }

    /** 重建用户-角色关联（调用方已 delete 旧关联） */
    private void assignRoles(Integer userId, List<Sys_Role> roles) {
        for (Sys_Role role : roles) {
            roleMapper.insertUserRole(userId, role.getId());
        }
    }

    /** 组装与 API-80 列表项一致的角色响应结构 */
    private Map<String, Object> toRoleEntry(Sys_Role role, int memberCount) {
        Set<String> granted = roleMapper.findPermissionsByRoleId(role.getId()).stream()
                .map(Sys_Permission::getPerm_code)
                .collect(Collectors.toSet());
        Map<String, Object> entry = new LinkedHashMap<>();
        entry.put("role_id", role.getId());
        entry.put("role_code", role.getRole_code());
        entry.put("role_name", role.getRole_name());
        entry.put("description", role.getDescription());
        entry.put("permissions", buildPermissionMatrix(roleMapper.findAllPermissions(), granted));
        entry.put("audit_scope", "");
        entry.put("status", role.getStatus());
        entry.put("member_count", memberCount);
        entry.put("created_at", role.getCreated_at());
        return entry;
    }

    /** 查询某角色的有效（未软删除）成员数 */
    private int getMemberCount(String roleCode) {
        return roleMapper.countUsersGroupByRole().stream()
                .filter(row -> roleCode.equals(String.valueOf(row.get("role_code"))))
                .mapToInt(row -> ((Number) row.get("user_count")).intValue())
                .findFirst()
                .orElse(0);
    }

    /**
     * 把角色权限序列化为前端权限矩阵 JSON：
     * [{"moduleKey":"users","moduleLabel":"用户管理","actions":[{"key":"view","label":"查看","granted":true},...]},...]
     */
    private String buildPermissionMatrix(List<Sys_Permission> allPermissions, Set<String> grantedCodes) {
        Map<String, Map<String, Object>> modules = new LinkedHashMap<>();
        for (Sys_Permission p : allPermissions) {
            Map<String, Object> module = modules.computeIfAbsent(p.getModule_key(), k -> {
                Map<String, Object> m = new LinkedHashMap<>();
                m.put("moduleKey", p.getModule_key());
                m.put("moduleLabel", p.getModule_label());
                m.put("actions", new ArrayList<Map<String, Object>>());
                return m;
            });
            @SuppressWarnings("unchecked")
            List<Map<String, Object>> actions = (List<Map<String, Object>>) module.get("actions");
            Map<String, Object> action = new LinkedHashMap<>();
            action.put("key", p.getAction_key());
            action.put("label", p.getAction_label());
            action.put("granted", grantedCodes.contains(p.getPerm_code()));
            actions.add(action);
        }
        return toJson(modules.values());
    }

    /** 解析 API-82 传入的权限矩阵 JSON，返回 granted=true 的权限编码集合 */
    private Set<String> parseGrantedPermCodes(String permissionsJson) {
        Set<String> granted = new LinkedHashSet<>();
        if (permissionsJson == null || permissionsJson.isBlank()) return granted;
        try {
            JsonNode modules = objectMapper.readTree(permissionsJson);
            if (!modules.isArray()) throw new RuntimeException("permissions 格式错误");
            for (JsonNode module : modules) {
                String moduleKey = module.path("moduleKey").asText("");
                for (JsonNode action : module.path("actions")) {
                    if (action.path("granted").asBoolean(false)) {
                        granted.add(moduleKey + ":" + action.path("key").asText(""));
                    }
                }
            }
        } catch (RuntimeException e) {
            throw e;
        } catch (Exception e) {
            throw new RuntimeException("permissions 格式错误，应为权限矩阵 JSON");
        }
        return granted;
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (Exception e) {
            throw new RuntimeException("JSON 序列化失败");
        }
    }

    private void evictUserCache(Sys_User user) {
        if (user == null) return;
        redisCacheUtil.delete("user:auth:" + user.getId());
        redisCacheUtil.delete("user:profile:" + user.getId());
        if (user.getUsername() != null) redisCacheUtil.delete("user:lookup:username:" + user.getUsername());
        if (user.getEmail() != null) redisCacheUtil.delete("user:lookup:email:" + user.getEmail());
    }
}
