package edu.zstu.service.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.util.RandomUtil;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.zstu.dto.*;
import edu.zstu.entity.Sys_Role;
import edu.zstu.entity.Sys_User;
import edu.zstu.mapper.SysRoleMapper;
import edu.zstu.mapper.SysUserMapper;
import edu.zstu.service.AuthService;
import edu.zstu.service.BusinessLogService;
import edu.zstu.utils.CurrentHolder;
import edu.zstu.utils.JwtUtil;
import edu.zstu.utils.PasswordUtil;
import edu.zstu.utils.RedisCacheUtil;
import edu.zstu.utils.RedisRateLimiter;
import edu.zstu.vo.LoginVO;
import edu.zstu.vo.UserVO;
import io.jsonwebtoken.Claims;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.time.Duration;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Service
public class AuthServiceImpl implements AuthService {

    /** 新注册用户的默认角色编码 */
    private static final String DEFAULT_ROLE_CODE = "teacher";

    private final SysUserMapper userMapper;
    private final SysRoleMapper roleMapper;
    private final PasswordUtil passwordUtil;
    private final JwtUtil jwtUtil;
    private final StringRedisTemplate redisTemplate;
    private final JavaMailSender mailSender;
    private final BusinessLogService businessLogService;
    private final RedisCacheUtil redisCacheUtil;
    private final RedisRateLimiter rateLimiter;
    private final ObjectMapper objectMapper;

    public AuthServiceImpl(SysUserMapper userMapper, SysRoleMapper roleMapper, PasswordUtil passwordUtil,
                           JwtUtil jwtUtil, StringRedisTemplate redisTemplate,
                           JavaMailSender mailSender, BusinessLogService businessLogService,
                           RedisCacheUtil redisCacheUtil, RedisRateLimiter rateLimiter,
                           ObjectMapper objectMapper) {
        this.userMapper = userMapper;
        this.roleMapper = roleMapper;
        this.passwordUtil = passwordUtil;
        this.jwtUtil = jwtUtil;
        this.redisTemplate = redisTemplate;
        this.mailSender = mailSender;
        this.businessLogService = businessLogService;
        this.redisCacheUtil = redisCacheUtil;
        this.rateLimiter = rateLimiter;
        this.objectMapper = objectMapper;
    }

    @Override
    @Transactional
    public UserVO register(RegisterDTO dto) {
        log.info("register username={}, email={}", dto.getUsername(), dto.getEmail());
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

        // 3. 创建用户（直接激活 is_active=1），默认授予 teacher 角色
        String hashedPassword = passwordUtil.hash(dto.getPassword());
        Sys_User user = new Sys_User();
        user.setUsername(dto.getUsername());
        user.setPassword_hash(hashedPassword);
        user.setReal_name(dto.getReal_name());
        user.setPhone(dto.getPhone());
        user.setEmail(dto.getEmail());
        user.setAvatar(dto.getAvatar() != null ? dto.getAvatar() : "");
        user.setIs_active(1);
        user.setEmail_verified(1);
        user.setPhone_verified(0);

        int result = userMapper.insert(user);
        if (result <= 0) {
            throw new RuntimeException("注册失败，请稍后重试");
        }
        Sys_Role defaultRole = roleMapper.findRoleByCode(DEFAULT_ROLE_CODE);
        if (defaultRole != null) {
            roleMapper.insertUserRole(user.getId(), defaultRole.getId());
        }
        evictUserCache(user);
        log.info("register success userId={}, username={}", user.getId(), user.getUsername());
        businessLogService.record("operation", "auth", "register", "user", user.getId(),
                Map.of("username", user.getUsername(), "role", DEFAULT_ROLE_CODE));
        return toUserVO(user);
    }

    @Override
    public boolean checkUsername(String username) {
        log.info("checkUsername username={}", username);
        return userMapper.findByUsername(username) != null;
    }

    @Override
    public boolean checkEmail(String email) {
        log.info("checkEmail email={}", email);
        return userMapper.findByEmail(email) != null;
    }

    @Override
    public LoginVO login(LoginDTO dto) {
        log.info("login username={}", dto.getUsername());
        String loginIp = currentRequestIp();
        rateLimiter.assertWithinLimit("rate:auth:login:user:" + dto.getUsername(), 10, Duration.ofMinutes(10),
                "登录过于频繁，请稍后再试");
        rateLimiter.assertWithinLimit("rate:auth:login:ip:" + loginIp, 60, Duration.ofMinutes(10),
                "当前IP登录请求过于频繁，请稍后再试");
        String hashedPassword = passwordUtil.hash(dto.getPassword());
        Sys_User user = userMapper.findByUsernameAndPasswordHash(dto.getUsername(), hashedPassword);
        if (user == null) {
            throw new RuntimeException("用户名或密码错误");
        }

        Map<String, Object> claims = new HashMap<>();
        claims.put("user_id", user.getId());
        String token = jwtUtil.generateToken(claims);
        redisTemplate.opsForValue().set("token:user:" + user.getId(), token, 7, TimeUnit.DAYS);
        userMapper.updateLastLogin(user.getId(), loginIp);
        user.setLast_login_at(java.time.LocalDateTime.now());
        user.setLast_login_ip(loginIp);
        evictUserCache(user);
        log.info("login success userId={}, username={}", user.getId(), user.getUsername());
        businessLogService.record("operation", "auth", "login", "user", user.getId());

        LoginVO vo = new LoginVO();
        BeanUtil.copyProperties(user, vo, "id");
        vo.setToken(token);
        vo.setUser_id(user.getId());
        fillRoleFields(vo);
        return vo;
    }

    @Override
    public void sendVerificationCode(VerificationCodeDTO dto) {
        log.info("sendVerificationCode scene={}, channel={}, username={}", dto.getScene(), dto.getChannel(), dto.getUsername());
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

        rateLimiter.assertCooldown("rate:verify:cooldown:" + dto.getScene() + ":" + email,
                Duration.ofSeconds(60), "验证码发送过于频繁，请稍后再试");
        rateLimiter.assertWithinLimit("rate:verify:window:" + dto.getScene() + ":" + email,
                5, Duration.ofMinutes(10), "验证码发送次数过多，请稍后再试");
        String code = RandomUtil.randomNumbers(6);
        redisTemplate.opsForValue().set("verify:code:" + dto.getScene() + ":" + email, code, 60, TimeUnit.SECONDS);

        SimpleMailMessage message = new SimpleMailMessage();
        message.setTo(email);
        message.setSubject("A12 教学平台 - " + ("register".equals(dto.getScene()) ? "注册" : "密码重置") + "验证码");
        message.setText("您的验证码为：" + code + "\n有效期 60 秒，请勿泄露给他人。");
        mailSender.send(message);
        log.info("sendVerificationCode success scene={}, email={}", dto.getScene(), email);
    }

    @Override
    @Transactional
    public void verify(VerifyDTO dto) {
        log.info("verify scene={}, username={}", dto.getScene(), dto.getUsername());
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
            log.info("verifyRegister success userId={}", user.getId());
            businessLogService.record("operation", "auth", "verify_register", "user", user.getId());
        }
    }

    @Override
    @Transactional
    public LoginVO initialPasswordChange(InitialPasswordChangeDTO dto) {
        log.info("initialPasswordChange username={}", dto.getUsername());
        Sys_User user = userMapper.findByUsername(dto.getUsername());
        if (user == null) throw new RuntimeException("用户不存在");
        if (user.getIs_active() != 1) throw new RuntimeException("用户未激活，请先激活");
        if (!passwordUtil.hash(dto.getInitial_password()).equals(user.getPassword_hash())) {
            throw new RuntimeException("初始密码错误");
        }
        userMapper.changePassword(passwordUtil.hash(dto.getNew_password()), user.getUsername());
        String loginIp = currentRequestIp();
        userMapper.updateLastLogin(user.getId(), loginIp);
        user.setLast_login_at(java.time.LocalDateTime.now());
        user.setLast_login_ip(loginIp);
        evictUserCache(user);

        LoginVO vo = new LoginVO();
        BeanUtil.copyProperties(user, vo, "id");
        vo.setUser_id(user.getId());
        fillRoleFields(vo);
        String newToken = jwtUtil.generateToken(Map.of("user_id", user.getId()));
        redisTemplate.opsForValue().set("token:user:" + user.getId(), newToken, 7, TimeUnit.DAYS);
        vo.setToken(newToken);
        vo.setLast_login_at(user.getLast_login_at());
        log.info("initialPasswordChange success userId={}", user.getId());
        businessLogService.record("operation", "auth", "initial_password_change", "user", user.getId());
        return vo;
    }

    @Override
    @Transactional
    public void passwordReset(PasswordResetDTO dto) {
        log.info("passwordReset username={}", dto.getUsername());
        Sys_User user = userMapper.findByUsername(dto.getUsername());
        if (user == null) throw new RuntimeException("用户不存在");
        String redisKey = "verify:code:password_reset:" + user.getEmail();
        String storedCode = redisTemplate.opsForValue().get(redisKey);
        if (storedCode == null) throw new RuntimeException("验证码已过期，请重新发送");
        if (!storedCode.equals(dto.getCode())) throw new RuntimeException("验证码错误");
        redisTemplate.delete(redisKey);
        userMapper.changePassword(passwordUtil.hash(dto.getNew_password()), user.getUsername());
        evictUserCache(user);
        log.info("passwordReset success userId={}", user.getId());
        businessLogService.record("operation", "auth", "password_reset", "user", user.getId());
    }

    @Override
    public void logout(String authorization) {
        log.info("logout currentUserId={}", CurrentHolder.getCurrentId());
        // JwtAuthenticationFilter 跳过 /api/v1/auth/**，CurrentHolder 在此端点恒为 null，
        // 需直接从 Authorization 头解析 JWT 得到 userId，再删除对应的 Redis 登录令牌
        Integer userId = CurrentHolder.getCurrentId();
        if (userId == null && authorization != null && authorization.startsWith("Bearer ")) {
            Claims claims = jwtUtil.parseToken(authorization.substring(7));
            if (claims != null) {
                userId = claims.get("user_id", Integer.class);
            }
        }
        if (userId != null) {
            redisTemplate.delete("token:user:" + userId);
            log.info("logout success userId={}", userId);
            businessLogService.record("operation", "auth", "logout", "user", userId);
        }
    }

    @Override
    @Transactional
    public void passwordChange(String currentPassword, String newPassword) {
        log.info("passwordChange currentUserId={}", CurrentHolder.getCurrentId());
        Integer userId = CurrentHolder.getCurrentId();
        if (userId == null) throw new RuntimeException("未登录");
        Sys_User user = userMapper.findById(userId);
        if (user == null) throw new RuntimeException("用户不存在");
        if (!passwordUtil.hash(currentPassword).equals(user.getPassword_hash())) {
            throw new RuntimeException("当前密码错误");
        }
        userMapper.changePassword(passwordUtil.hash(newPassword), user.getUsername());
        evictUserCache(user);
        log.info("passwordChange success userId={}", user.getId());
        businessLogService.record("operation", "auth", "password_change", "user", user.getId());
    }

    private UserVO toUserVO(Sys_User user) {
        UserVO vo = new UserVO();
        BeanUtil.copyProperties(user, vo);
        fillRoleFields(vo);
        return vo;
    }

    /**
     * 装配角色相关字段（RBAC 重构后不再存于 sys_user）：
     * roles = 角色编码数组 JSON，user_type = 首个角色编码（主角色，兼容前端），
     * permissions 固定 "[]"（角色权限矩阵走 API-80/82 查询）
     */
    private void fillRoleFields(Object target) {
        Integer userId;
        if (target instanceof UserVO) userId = ((UserVO) target).getId();
        else if (target instanceof LoginVO) userId = ((LoginVO) target).getUser_id();
        else return;
        if (userId <= 0) return;

        List<String> codes = roleMapper.findRolesByUserId(userId).stream()
                .map(Sys_Role::getRole_code)
                .toList();
        try {
            String rolesJson = objectMapper.writeValueAsString(codes);
            if (target instanceof UserVO) {
                ((UserVO) target).setRoles(rolesJson);
                ((UserVO) target).setUser_type(codes.isEmpty() ? null : codes.get(0));
                ((UserVO) target).setPermissions("[]");
            } else {
                ((LoginVO) target).setRoles(rolesJson);
                ((LoginVO) target).setUser_type(codes.isEmpty() ? null : codes.get(0));
                ((LoginVO) target).setPermissions("[]");
            }
        } catch (Exception ignored) {
            // 序列化失败时角色字段保持为空，不影响主流程
        }
    }

    private void evictUserCache(Sys_User user) {
        if (user == null) return;
        redisCacheUtil.delete("user:auth:" + user.getId());
        redisCacheUtil.delete("user:profile:" + user.getId());
        if (user.getUsername() != null) redisCacheUtil.delete("user:lookup:username:" + user.getUsername());
        if (user.getEmail() != null) redisCacheUtil.delete("user:lookup:email:" + user.getEmail());
    }

    private String currentRequestIp() {
        try {
            ServletRequestAttributes attributes = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
            if (attributes == null) return "";
            String forwardedFor = attributes.getRequest().getHeader("X-Forwarded-For");
            if (forwardedFor != null && !forwardedFor.isBlank()) {
                return forwardedFor.split(",")[0].trim();
            }
            String realIp = attributes.getRequest().getHeader("X-Real-IP");
            if (realIp != null && !realIp.isBlank()) return realIp;
            return attributes.getRequest().getRemoteAddr();
        } catch (Exception ignored) {
            return "";
        }
    }
}

