package edu.zstu.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.fasterxml.jackson.core.type.TypeReference;
import edu.zstu.dto.PasswordChangeDTO;
import edu.zstu.entity.Sys_User;
import edu.zstu.mapper.SysUserMapper;
import edu.zstu.service.BusinessLogService;
import edu.zstu.service.UserService;
import edu.zstu.utils.CurrentHolder;
import edu.zstu.utils.JwtUtil;
import edu.zstu.utils.PasswordUtil;
import edu.zstu.utils.RedisCacheUtil;
import edu.zstu.vo.UserVO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;

@Slf4j
@Service
public class UserServiceImpl implements UserService {

    private final SysUserMapper userMapper;
    private final PasswordUtil passwordUtil;
    private final JwtUtil jwtUtil;
    private final BusinessLogService businessLogService;
    private final RedisCacheUtil redisCacheUtil;

    public UserServiceImpl(SysUserMapper userMapper, PasswordUtil passwordUtil,
                           JwtUtil jwtUtil, BusinessLogService businessLogService,
                           RedisCacheUtil redisCacheUtil) {
        this.userMapper = userMapper;
        this.passwordUtil = passwordUtil;
        this.jwtUtil = jwtUtil;
        this.businessLogService = businessLogService;
        this.redisCacheUtil = redisCacheUtil;
    }

    @Override
    public UserVO getCurrentUser() {
        log.info("getCurrentUser called");
        Integer userId = CurrentHolder.getCurrentId();
        return redisCacheUtil.getOrLoad("user:profile:" + userId, UserVO.class, Duration.ofMinutes(10), () -> {
            Sys_User user = userMapper.findById(userId);
            if (user == null) {
                throw new RuntimeException("用户不存在");
            }
            if (user.getIs_active() != 1) {
                throw new RuntimeException("用户未激活，请先激活");
            }
            return BeanUtil.copyProperties(user, UserVO.class);
        });
    }

    @Override
    @Transactional
    public void changePassword(PasswordChangeDTO dto) {
        log.info("changePassword called");
        String currentPassword = dto.getCurrent_password();
        String newPassword = dto.getNew_password();
        Sys_User user = userMapper.findById(CurrentHolder.getCurrentId());
        if (user == null) {
            throw new RuntimeException("用户不存在");
        }
        if (user.getIs_active() != 1) {
            throw new RuntimeException("用户未激活，请先激活");
        }
        if (!passwordUtil.hash(currentPassword).equals(user.getPassword_hash())) {
            throw new RuntimeException("当前密码错误");
        }
        int res = userMapper.changePassword(passwordUtil.hash(newPassword), user.getUsername());
        if (res <= 0) {
            throw new RuntimeException("密码修改失败");
        }
        evictUserCache(user.getId(), user.getUsername(), user.getEmail());
        businessLogService.record("operation", "user", "password_change", "user", user.getId());
    }

    @Override
    public Map<String, Object> findUserIdByUsername(String username) {
        if (username == null || username.isBlank()) throw new RuntimeException("用户名不能为空");
        return redisCacheUtil.getOrLoad("user:lookup:username:" + username,
                new TypeReference<Map<String, Object>>() {}, Duration.ofMinutes(10), () -> {
                    Sys_User user = userMapper.findByUsername(username);
                    if (user == null) throw new RuntimeException("用户不存在");
                    return userLookup(user);
                });
    }

    @Override
    public Map<String, Object> findUserIdByEmail(String email) {
        if (email == null || email.isBlank()) throw new RuntimeException("邮箱不能为空");
        return redisCacheUtil.getOrLoad("user:lookup:email:" + email,
                new TypeReference<Map<String, Object>>() {}, Duration.ofMinutes(10), () -> {
                    Sys_User user = userMapper.findByEmail(email);
                    if (user == null) throw new RuntimeException("用户不存在");
                    return userLookup(user);
                });
    }

    private Map<String, Object> userLookup(Sys_User user) {
        Map<String, Object> result = new HashMap<>();
        result.put("id", user.getId());
        result.put("username", user.getUsername());
        result.put("real_name", user.getReal_name());
        result.put("email", user.getEmail());
        return result;
    }

    private void evictUserCache(Integer userId, String username, String email) {
        redisCacheUtil.delete("user:auth:" + userId);
        redisCacheUtil.delete("user:profile:" + userId);
        if (username != null) redisCacheUtil.delete("user:lookup:username:" + username);
        if (email != null) redisCacheUtil.delete("user:lookup:email:" + email);
    }
}
