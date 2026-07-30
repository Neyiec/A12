package edu.zstu.service.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.util.RandomUtil;
import edu.zstu.dto.*;
import edu.zstu.entity.Sys_User;
import edu.zstu.mapper.SysUserMapper;
import edu.zstu.service.AuthService;
import edu.zstu.service.BusinessLogService;
import edu.zstu.utils.CurrentHolder;
import edu.zstu.utils.JwtUtil;
import edu.zstu.utils.PasswordUtil;
import edu.zstu.utils.RedisCacheUtil;
import edu.zstu.vo.LoginVO;
import edu.zstu.vo.UserVO;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Service
public class AuthServiceImpl implements AuthService {

    private final SysUserMapper userMapper;
    private final PasswordUtil passwordUtil;
    private final JwtUtil jwtUtil;
    private final StringRedisTemplate redisTemplate;
    private final JavaMailSender mailSender;
    private final BusinessLogService businessLogService;
    private final RedisCacheUtil redisCacheUtil;

    public AuthServiceImpl(SysUserMapper userMapper, PasswordUtil passwordUtil,
                           JwtUtil jwtUtil, StringRedisTemplate redisTemplate,
                           JavaMailSender mailSender, BusinessLogService businessLogService,
                           RedisCacheUtil redisCacheUtil) {
        this.userMapper = userMapper;
        this.passwordUtil = passwordUtil;
        this.jwtUtil = jwtUtil;
        this.redisTemplate = redisTemplate;
        this.mailSender = mailSender;
        this.businessLogService = businessLogService;
        this.redisCacheUtil = redisCacheUtil;
    }

    @Override
    @Transactional
    public UserVO register(RegisterDTO dto) {
        log.info("register called");
        // 1. 校验验证码（注册场景）
        String redisKey = "verify:code:register:" + dto.getEmail();
        String storedCode = redisTemplate.opsForValue().get(redisKey);
        if (storedCode == null) {
            throw new RuntimeException("验证码已过期，请重新发送");
        }
        if (dto.getCode() == null || !storedCode.equals(dto.getCode())) {
            throw new RuntimeException("验证码错误");
        }
        redisTemplate.delete(redisKey);

        // 2. 校验唯一性
        if (userMapper.findByUsername(dto.getUsername()) != null) {
            throw new RuntimeException("用户名已存在");
        }
        if (userMapper.findByEmail(dto.getEmail()) != null) {
            throw new RuntimeException("邮箱已存在");
        }

        // 3. 创建用户（直接激活 is_active=1）
        String hashedPassword = passwordUtil.hash(dto.getPassword());
        Sys_User user = new Sys_User();
        user.setUsername(dto.getUsername());
        user.setPassword_hash(hashedPassword);
        user.setReal_name(dto.getReal_name());
        user.setPhone(dto.getPhone());
        user.setEmail(dto.getEmail());
        user.setAvatar(dto.getAvatar() != null ? dto.getAvatar() : "");
        user.setUser_type("teacher");
        user.setRoles("[\"teacher\"]");
        user.setPermissions("[]");
        user.setIs_active(1);

        int result = userMapper.insert(user);
        if (result <= 0) {
            throw new RuntimeException("注册失败，请稍后重试");
        }
        evictUserCache(user);
        businessLogService.record("operation", "auth", "register", "user", user.getId(),
                Map.of("username", user.getUsername(), "user_type", user.getUser_type()));
        return toUserVO(user);
    }

    @Override
    public boolean checkUsername(String username) {
        log.info("checkUsername called");
        return userMapper.findByUsername(username) != null;
    }

    @Override
    public boolean checkEmail(String email) {
        log.info("checkEmail called");
        return userMapper.findByEmail(email) != null;
    }

    @Override
    public LoginVO login(LoginDTO dto) {
        log.info("login called");
        String hashedPassword = passwordUtil.hash(dto.getPassword());
        Sys_User user = userMapper.findByUsernameAndPasswordHash(dto.getUsername(), hashedPassword);
        if (user == null) {
            throw new RuntimeException("用户名或密码错误");
        }

        Map<String, Object> claims = new HashMap<>();
        claims.put("user_id", user.getId());
        String token = jwtUtil.generateToken(claims);
        redisTemplate.opsForValue().set("token:user:" + user.getId(), token, 7, TimeUnit.DAYS);
        businessLogService.record("operation", "auth", "login", "user", user.getId());

        LoginVO vo = new LoginVO();
        BeanUtil.copyProperties(user, vo, "id");
        vo.setToken(token);
        vo.setUser_id(user.getId());
        return vo;
    }

    @Override
    public void sendVerificationCode(VerificationCodeDTO dto) {
        log.info("sendVerificationCode called");
        if (!"register".equals(dto.getScene()) && !"password_reset".equals(dto.getScene())) {
            throw new RuntimeException("无效的场景值，仅支持 register / password_reset");
        }
        if (!"email".equals(dto.getChannel())) {
            throw new RuntimeException("目前仅支持邮箱验证码，不支持手机");
        }

        String email;
        if ("register".equals(dto.getScene())) {
            // 注册场景：用户未创建，username 字段是邮箱
            email = dto.getUsername();
        } else {
            // 密码重置场景：通过用户名查邮箱
            Sys_User user = userMapper.findByUsername(dto.getUsername());
            if (user == null) throw new RuntimeException("用户不存在");
            email = user.getEmail();
        }

        if (email == null || !email.contains("@")) {
            throw new RuntimeException("邮箱地址无效");
        }

        String code = RandomUtil.randomNumbers(6);
        redisTemplate.opsForValue().set("verify:code:" + dto.getScene() + ":" + email, code, 60, TimeUnit.SECONDS);

        SimpleMailMessage message = new SimpleMailMessage();
        message.setTo(email);
        message.setSubject("A12 教学平台 - " + ("register".equals(dto.getScene()) ? "注册" : "密码重置") + "验证码");
        message.setText("您的验证码为：" + code + "\n有效期 60 秒，请勿泄露给他人。");
        mailSender.send(message);
    }

    @Override
    @Transactional
    public void verify(VerifyDTO dto) {
        log.info("verify called");
        if (!"register".equals(dto.getScene()) && !"password_reset".equals(dto.getScene())) {
            throw new RuntimeException("无效的场景值，仅支持 register / password_reset");
        }

        Sys_User user = userMapper.findByUsername(dto.getUsername());
        if (user == null) throw new RuntimeException("用户不存在");

        String redisKey = "verify:code:" + dto.getScene() + ":" + user.getEmail();
        String storedCode = redisTemplate.opsForValue().get(redisKey);

        if (storedCode == null) throw new RuntimeException("验证码已过期，请重新发送");
        if (!storedCode.equals(dto.getCode())) throw new RuntimeException("验证码错误");

        redisTemplate.delete(redisKey);

        if ("register".equals(dto.getScene())) {
            userMapper.updateActiveStatus(user.getId(), 1);
            evictUserCache(user);
            businessLogService.record("operation", "auth", "verify_register", "user", user.getId());
        }
    }

    @Override
    @Transactional
    public LoginVO initialPasswordChange(InitialPasswordChangeDTO dto) {
        log.info("initialPasswordChange called");
        Sys_User user = userMapper.findByUsername(dto.getUsername());
        if (user == null) throw new RuntimeException("用户不存在");
        if (user.getIs_active() != 1) throw new RuntimeException("用户未激活，请先激活");
        if (!passwordUtil.hash(dto.getInitial_password()).equals(user.getPassword_hash())) {
            throw new RuntimeException("初始密码错误");
        }
        userMapper.changePassword(passwordUtil.hash(dto.getNew_password()), user.getUsername());
        evictUserCache(user);

        LoginVO vo = new LoginVO();
        BeanUtil.copyProperties(user, vo, "id");
        vo.setUser_id(user.getId());
        String newToken = jwtUtil.generateToken(Map.of("user_id", user.getId()));
        redisTemplate.opsForValue().set("token:user:" + user.getId(), newToken, 7, TimeUnit.DAYS);
        vo.setToken(newToken);
        businessLogService.record("operation", "auth", "initial_password_change", "user", user.getId());
        return vo;
    }

    @Override
    @Transactional
    public void passwordReset(PasswordResetDTO dto) {
        log.info("passwordReset called");
        Sys_User user = userMapper.findByUsername(dto.getUsername());
        if (user == null) throw new RuntimeException("用户不存在");
        String redisKey = "verify:code:password_reset:" + user.getEmail();
        String storedCode = redisTemplate.opsForValue().get(redisKey);
        if (storedCode == null) throw new RuntimeException("验证码已过期，请重新发送");
        if (!storedCode.equals(dto.getCode())) throw new RuntimeException("验证码错误");
        redisTemplate.delete(redisKey);
        userMapper.changePassword(passwordUtil.hash(dto.getNew_password()), user.getUsername());
        evictUserCache(user);
        businessLogService.record("operation", "auth", "password_reset", "user", user.getId());
    }

    @Override
    public void logout(String authorization) {
        log.info("logout called");
        Integer userId = CurrentHolder.getCurrentId();
        if (userId != null) {
            redisTemplate.delete("token:user:" + userId);
            businessLogService.record("operation", "auth", "logout", "user", userId);
        }
    }

    @Override
    @Transactional
    public void passwordChange(String currentPassword, String newPassword) {
        log.info("passwordChange called");
        Integer userId = CurrentHolder.getCurrentId();
        if (userId == null) throw new RuntimeException("未登录");
        Sys_User user = userMapper.findById(userId);
        if (user == null) throw new RuntimeException("用户不存在");
        if (!passwordUtil.hash(currentPassword).equals(user.getPassword_hash())) {
            throw new RuntimeException("当前密码错误");
        }
        userMapper.changePassword(passwordUtil.hash(newPassword), user.getUsername());
        evictUserCache(user);
        businessLogService.record("operation", "auth", "password_change", "user", user.getId());
    }

    private UserVO toUserVO(Sys_User user) {
        UserVO vo = new UserVO();
        BeanUtil.copyProperties(user, vo);
        return vo;
    }

    private void evictUserCache(Sys_User user) {
        if (user == null) return;
        redisCacheUtil.delete("user:auth:" + user.getId());
        redisCacheUtil.delete("user:profile:" + user.getId());
        if (user.getUsername() != null) redisCacheUtil.delete("user:lookup:username:" + user.getUsername());
        if (user.getEmail() != null) redisCacheUtil.delete("user:lookup:email:" + user.getEmail());
    }
}
