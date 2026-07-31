package edu.zstu.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import edu.zstu.dto.*;
import edu.zstu.entity.Sys_User;
import edu.zstu.mapper.SysUserMapper;
import edu.zstu.service.AdminUserService;
import edu.zstu.service.BusinessLogService;
import edu.zstu.utils.PageResult;
import edu.zstu.utils.PasswordUtil;
import edu.zstu.utils.RedisCacheUtil;
import edu.zstu.vo.UserVO;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;
import java.time.Duration;
import java.util.stream.Collectors;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Service
public class AdminUserServiceImpl implements AdminUserService {

    private final SysUserMapper userMapper;
    private final PasswordUtil passwordUtil;
    private final BusinessLogService businessLogService;
    private final RedisCacheUtil redisCacheUtil;

    public AdminUserServiceImpl(SysUserMapper userMapper, PasswordUtil passwordUtil,
                                BusinessLogService businessLogService,
                                RedisCacheUtil redisCacheUtil) {
        this.userMapper = userMapper;
        this.passwordUtil = passwordUtil;
        this.businessLogService = businessLogService;
        this.redisCacheUtil = redisCacheUtil;
    }

    // ==================== API-71 分页查询用户 ====================

    @Override
    public PageResult<UserVO> listUsers(UserQueryDTO dto) {
        log.info("listUsers keyword={}, userType={}, isActive={}, page={}, size={}", dto.getKeyword(), dto.getUser_type(), dto.getIs_active(), dto.getPage(), dto.getSize());
        PageHelper.startPage(dto.getPage(), dto.getSize());
        List<Sys_User> list = userMapper.findByQuery(dto);
        PageInfo<Sys_User> info = new PageInfo<>(list);

        List<UserVO> records = info.getList().stream().map(this::toUserVO).toList();
        PageResult<UserVO> r = new PageResult<>();
        r.setTotal(info.getTotal()); r.setPage(dto.getPage());
        r.setSize(dto.getSize()); r.setRecords(records);
        return r;
    }

    // ==================== API-72 获取用户详情 ====================

    @Override
    public UserVO getUser(Integer id) {
        log.info("getUser userId={}", id);
        Sys_User u = userMapper.findById(id);
        if (u == null) throw new RuntimeException("用户不存在");
        return toUserVO(u);
    }

    // ==================== API-73 启用/停用/锁定用户 ====================

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
        return toUserVO(u);
    }

    // ==================== API-74 创建单个后台账号 ====================

    @Override
    @Transactional
    public UserVO createUser(UserDTO dto) {
        log.info("createUser username={}, userType={}, roles={}", dto.getUsername(), dto.getUser_type(), dto.getRoles());
        if (dto.getUsername() == null || dto.getReal_name() == null ||
            dto.getUser_type() == null || dto.getRoles() == null) {
            throw new RuntimeException("缺少必填字段: username, real_name, user_type, roles");
        }
        if (userMapper.findByUsername(dto.getUsername()) != null) {
            throw new RuntimeException("用户名已存在");
        }

        String hashedPassword = passwordUtil.hash(dto.getPassword() != null ? dto.getPassword() : "123456");
        Sys_User user = new Sys_User();
        BeanUtil.copyProperties(dto, user);
        user.setPassword_hash(hashedPassword);
        user.setIs_active(1);
        userMapper.insert(user);
        evictUserCache(user);
        redisCacheUtil.delete("admin:roles");
        log.info("createUser success userId={}, username={}", user.getId(), user.getUsername());
        businessLogService.record("operation", "admin_user", "create", "user", user.getId(),
                Map.of("username", user.getUsername(), "user_type", user.getUser_type()));
        return toUserVO(user);
    }

    // ==================== API-75 批量创建后台账号 ====================

    @Override
    @Transactional
    public Map<String, Object> batchCreateUsers(BatchCreateUsersDTO dto) {
        log.info("batchCreateUsers called");
        List<Map<String, Object>> results = new ArrayList<>();
        List<Map<String, Object>> userList;

        try {
            @SuppressWarnings("unchecked")
            List<Map<String, Object>> parsed = new com.fasterxml.jackson.databind.ObjectMapper()
                    .readValue(dto.getUsers(), List.class);
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

    // ==================== API-76 查询角色列表 ====================

    @Override
    public List<Map<String, Object>> listRoles() {
        log.info("listRoles");
        return redisCacheUtil.getOrLoad("admin:roles",
                new com.fasterxml.jackson.core.type.TypeReference<List<Map<String, Object>>>() {},
                Duration.ofMinutes(10), this::loadRoles);
    }

    private List<Map<String, Object>> loadRoles() {
        List<Sys_User> all = userMapper.findAll();
        // 从所有用户中提取不重复的 roles JSON 并解析
        Set<String> seen = new HashSet<>();
        List<Map<String, Object>> roleList = new ArrayList<>();
        int idx = 1;
        for (Sys_User u : all) {
            if (u.getRoles() == null || u.getRoles().isBlank()) continue;
            try {
                @SuppressWarnings("unchecked")
                List<String> roles = new com.fasterxml.jackson.databind.ObjectMapper()
                        .readValue(u.getRoles(), List.class);
                for (String r : roles) {
                    if (seen.add(r)) {
                        Map<String, Object> entry = new HashMap<>();
                        entry.put("role_id", idx++);
                        entry.put("role_name", r);
                        entry.put("permissions", u.getPermissions() != null ? u.getPermissions() : "[]");
                        entry.put("audit_scope", "");
                        roleList.add(entry);
                    }
                }
            } catch (Exception ignored) {
            }
        }
        return roleList;
    }

    // ==================== API-77 分配角色 ====================

    @Override
    @Transactional
    public UserVO assignRoles(Integer id, AssignRolesDTO dto) {
        log.info("assignRoles userId={}, roles={}", id, dto.getRoles());
        Sys_User u = userMapper.findById(id);
        if (u == null) throw new RuntimeException("用户不存在");
        u.setRoles(dto.getRoles());
        userMapper.update(u);
        evictUserCache(u);
        redisCacheUtil.delete("admin:roles");
        log.info("assignRoles success userId={}", id);
        businessLogService.record("operation", "admin_user", "assign_roles", "user", id,
                Map.of("roles", dto.getRoles()));
        return toUserVO(u);
    }

    // ==================== API-78 配置角色权限 ====================

    @Override
    @Transactional
    public void updateRolePermissions(Integer id, RolePermissionsDTO dto) {
        log.info("updateRolePermissions roleId={}", id);
        // 查找所有拥有该角色的用户
        List<Sys_User> all = userMapper.findAll();
        for (Sys_User u : all) {
            if (u.getRoles() == null || u.getRoles().isBlank()) continue;
            try {
                @SuppressWarnings("unchecked")
                List<String> roles = new com.fasterxml.jackson.databind.ObjectMapper()
                        .readValue(u.getRoles(), List.class);
                String roleKey = getRoleKey(id);
                if (roles.contains(roleKey)) {
                    u.setPermissions(dto.getPermissions());
                    userMapper.update(u);
                    evictUserCache(u);
                }
            } catch (Exception ignored) {
            }
        }
        log.info("updateRolePermissions success roleId={}", id);
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

    private String getRoleKey(Integer id) {
        // 根据 role_id 映射角色名称（简单映射，实际可扩展）
        Map<Integer, String> roleMap = Map.of(
                1, "admin",
                2, "moderator",
                3, "teacher"
        );
        return roleMap.getOrDefault(id, "role_" + id);
    }

    private void evictUserCache(Sys_User user) {
        if (user == null) return;
        redisCacheUtil.delete("user:auth:" + user.getId());
        redisCacheUtil.delete("user:profile:" + user.getId());
        if (user.getUsername() != null) redisCacheUtil.delete("user:lookup:username:" + user.getUsername());
        if (user.getEmail() != null) redisCacheUtil.delete("user:lookup:email:" + user.getEmail());
    }
}




