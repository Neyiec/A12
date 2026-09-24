package edu.zstu.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.fasterxml.jackson.core.type.TypeReference;
import edu.zstu.dto.PasswordChangeDTO;
import edu.zstu.dto.ContactChangeDTO;
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
import org.springframework.data.redis.core.StringRedisTemplate;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;
import java.util.Objects;

@Slf4j
@Service
public class UserServiceImpl implements UserService {

    private final SysUserMapper userMapper;
    private final PasswordUtil passwordUtil;
    private final JwtUtil jwtUtil;
    private final BusinessLogService businessLogService;
    private final RedisCacheUtil redisCacheUtil;
    private final StringRedisTemplate redisTemplate;

    public UserServiceImpl(SysUserMapper userMapper, PasswordUtil passwordUtil,
                           JwtUtil jwtUtil, BusinessLogService businessLogService,
                           RedisCacheUtil redisCacheUtil, StringRedisTemplate redisTemplate) {
        this.userMapper = userMapper;
        this.passwordUtil = passwordUtil;
        this.jwtUtil = jwtUtil;
        this.businessLogService = businessLogService;
        this.redisCacheUtil = redisCacheUtil;
        this.redisTemplate = redisTemplate;
    }

    @Override
    public UserVO getCurrentUser() {
        log.info("getCurrentUser called");
        Integer userId = CurrentHolder.getCurrentId();
        // 账号中心属于安全敏感页面，始终读取数据库最新联系方式，避免人工更新后仍命中旧缓存。
        Sys_User user = userMapper.findById(userId);
        if (user == null) throw new RuntimeException("用户不存在");
        if (user.getIs_active() != 1) throw new RuntimeException("用户未激活，请先激活");
        return BeanUtil.copyProperties(user, UserVO.class);
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
    @Transactional
    public UserVO changeContact(ContactChangeDTO dto) {
        Integer userId = CurrentHolder.getCurrentId();
        Sys_User user = userMapper.findById(userId);
        if (user == null) throw new RuntimeException("用户不存在");
        if (user.getEmail() == null || user.getEmail().isBlank()) {
            throw new RuntimeException("当前账号未绑定邮箱，请联系管理员处理");
        }
        if (dto == null || dto.getCode() == null || dto.getCode().isBlank()) {
            throw new RuntimeException("请输入原邮箱收到的验证码");
        }

        String redisKey = "verify:code:profile_update:" + user.getEmail();
        String storedCode = redisTemplate.opsForValue().get(redisKey);
        if (storedCode == null) throw new RuntimeException("验证码已过期，请重新发送");
        if (!storedCode.equals(dto.getCode().trim())) throw new RuntimeException("验证码错误");

        String newRealName = dto.getReal_name() == null ? "" : dto.getReal_name().trim();
        String newEmail = dto.getEmail() == null ? "" : dto.getEmail().trim();
        String newPhone = dto.getPhone() == null ? "" : dto.getPhone().trim();
        boolean realNameChanged = !newRealName.isBlank() && !Objects.equals(newRealName, user.getReal_name());
        boolean emailChanged = !newEmail.isBlank() && !Objects.equals(newEmail, user.getEmail());
        boolean phoneChanged = !newPhone.isBlank() && !Objects.equals(newPhone, user.getPhone());
        if (!realNameChanged && !emailChanged && !phoneChanged) throw new RuntimeException("个人信息没有发生变化");
        if (realNameChanged && (newRealName.length() < 2 || newRealName.length() > 50)) {
            throw new RuntimeException("真实姓名长度需要在 2 到 50 个字符之间");
        }
        if (emailChanged && !newEmail.matches("^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$")) {
            throw new RuntimeException("新邮箱格式不正确");
        }
        if (phoneChanged && !newPhone.matches("^1\\d{10}$")) {
            throw new RuntimeException("新手机号格式不正确");
        }
        if (emailChanged) {
            Sys_User emailOwner = userMapper.findByEmail(newEmail);
            if (emailOwner != null && emailOwner.getId() != userId) throw new RuntimeException("该邮箱已被其他账号使用");
        }
        if (phoneChanged) {
            Sys_User phoneOwner = userMapper.findByPhone(newPhone);
            if (phoneOwner != null && phoneOwner.getId() != userId) throw new RuntimeException("该手机号已被其他账号使用");
        }

        int updated = userMapper.updateContact(userId, newRealName, newEmail, newPhone,
                realNameChanged, emailChanged, phoneChanged);
        if (updated <= 0) throw new RuntimeException("个人信息修改失败");
        redisTemplate.delete(redisKey);
        evictUserCache(userId, user.getUsername(), user.getEmail());
        if (emailChanged) redisCacheUtil.delete("user:lookup:email:" + newEmail);
        businessLogService.record("operation", "user", "contact_change", "user", userId);
        return getCurrentUser();
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
