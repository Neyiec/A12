package edu.zstu.service.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.util.RandomUtil;
import cn.hutool.json.JSONUtil;
import edu.zstu.dto.*;
import edu.zstu.entity.Sys_User;
import edu.zstu.mapper.SysUserMapper;
import edu.zstu.service.AuthService;
import edu.zstu.utils.JwtUtil;
import edu.zstu.utils.PasswordUtil;
import edu.zstu.vo.LoginVO;
import edu.zstu.vo.UserVO;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

@Service
public class AuthServiceImpl implements AuthService {

    private final SysUserMapper userMapper;
    private final PasswordUtil passwordUtil;
    private final JwtUtil jwtUtil;
    private final StringRedisTemplate redisTemplate;
    private final JavaMailSender mailSender;

    public AuthServiceImpl(SysUserMapper userMapper, PasswordUtil passwordUtil,
                           JwtUtil jwtUtil, StringRedisTemplate redisTemplate,
                           JavaMailSender mailSender) {
        this.userMapper = userMapper;
        this.passwordUtil = passwordUtil;
        this.jwtUtil = jwtUtil;
        this.redisTemplate = redisTemplate;
        this.mailSender = mailSender;
    }

    @Override
    public UserVO register(RegisterDTO dto) {
        Sys_User existing = userMapper.findByUsername(dto.getUsername());
        if (existing != null) {
            throw new RuntimeException("用户名已存在");
        }
        //根据邮箱查找
        existing = userMapper.findByEmail(dto.getEmail());
        if (existing != null) {
            throw new RuntimeException("邮箱已存在");
        }


        String hashedPassword = passwordUtil.hash(dto.getPassword());

        Sys_User user = new Sys_User();
        user.setUsername(dto.getUsername());
        user.setPassword_hash(hashedPassword);
        user.setReal_name(dto.getReal_name());
        user.setPhone(dto.getPhone());
        user.setEmail(dto.getEmail());
        user.setAvatar(dto.getAvatar() != null ? dto.getAvatar() : "");
        user.setUser_type("teacher");
        ArrayList<String> roles= new ArrayList<>();
        roles.add("teacher");
        user.setRoles(JSONUtil.toJsonStr(roles));
        user.setPermissions("[]");
        user.setIs_active(0);
        user.setCreated_at(LocalDateTime.now());
        user.setUpdated_at(LocalDateTime.now());

        int result = userMapper.insert(user);
        if (result <= 0) {
            throw new RuntimeException("注册失败，请稍后重试");
        }

        return toUserVO(user);
    }

    @Override
    public LoginVO login(LoginDTO dto) {
        String hashedPassword = passwordUtil.hash(dto.getPassword());
        Sys_User user = userMapper.findByUsernameAndPasswordHash(dto.getUsername(), hashedPassword);
        if (user == null) {
            throw new RuntimeException("用户名或密码错误");
        }

        Map<String, Object> claims = new HashMap<>();
        claims.put("user_id", user.getId());
        String token = jwtUtil.generateToken(claims);
        // 令牌存入 Redis，有效期 7 天
        redisTemplate.opsForValue().set("token:" + token, String.valueOf(user.getId()), 7, TimeUnit.DAYS);

        LoginVO vo = new LoginVO();
        BeanUtil.copyProperties(user, vo, "id");
        vo.setToken(token);
        vo.setUser_id(user.getId());
        return vo;
    }

    @Override
    public void sendVerificationCode(VerificationCodeDTO dto) {
        if (!"email".equals(dto.getChannel())) {
            throw new RuntimeException("目前仅支持邮箱验证码，不支持手机");
        }
        Sys_User user = userMapper.findByUsername(dto.getUsername());
        if (user == null) {
            throw new RuntimeException("用户不存在");
        }

        String email = user.getEmail();
        if (email == null || !email.contains("@")) {
            throw new RuntimeException("邮箱地址无效");
        }

        String code = RandomUtil.randomNumbers(6);
        String redisKey = "verify:code:"+ email;
        redisTemplate.opsForValue().set(redisKey, code, 60, TimeUnit.SECONDS);

        SimpleMailMessage message = new SimpleMailMessage();
        message.setTo(email);
        message.setSubject("A12 教学平台 - " + "验证码");
        message.setText("您的验证码为：" + code + "\n有效期 60 秒，请勿泄露给他人。");
        mailSender.send(message);
    }

    @Override
    public void verify(VerifyDTO dto) {
        Sys_User user = userMapper.findByUsername(dto.getUsername());
        if (user == null) {
            throw new RuntimeException("用户不存在");
        }

        String redisKey = "verify:code:" + user.getEmail();
        String storedCode = redisTemplate.opsForValue().get(redisKey);

        if (storedCode == null) {
            throw new RuntimeException("验证码已过期，请重新发送");
        }
        if (!storedCode.equals(dto.getCode())) {
            throw new RuntimeException("验证码错误");
        }

        redisTemplate.delete(redisKey);

        userMapper.updateActiveStatus(user.getId(), 1);
    }

    @Override
    public LoginVO initialPasswordChange(InitialPasswordChangeDTO dto) {
        Sys_User user = userMapper.findByUsername(dto.getUsername());
        if (user == null) {
            throw new RuntimeException("用户不存在");
        }
        if (user.getIs_active() != 1) {
            throw new RuntimeException("用户未激活，请先激活");
        }
        if (!passwordUtil.hash(dto.getInitial_password()).equals(user.getPassword_hash())) {
            throw new RuntimeException("初始密码错误");
        }
        userMapper.changePassword(passwordUtil.hash(dto.getNew_password_hash()), user.getUsername(),LocalDateTime.now());
        LoginVO vo = new LoginVO();
        BeanUtil.copyProperties(user, vo, "id");
        vo.setUser_id(user.getId());
        String newToken = jwtUtil.generateToken(Map.of("user_id", user.getId()));
        redisTemplate.opsForValue().set("token:" + newToken, String.valueOf(user.getId()), 7, TimeUnit.DAYS);
        vo.setToken(newToken);
        return vo;
    }

    @Override
    public void passwordReset(PasswordResetDTO dto) {
        //先根据账号查询邮箱
        Sys_User user=userMapper.findByUsername(dto.getUsername());

        if(user==null){
            throw new RuntimeException("用户不存在");
        }
        if(user.getIs_active()!=1){
            throw new RuntimeException("用户未激活，请先激活");
        }
        String email=user.getEmail();
        String redisKey="verify:code:"+email;
        String storedCode=redisTemplate.opsForValue().get(redisKey);
        if(storedCode==null){
            throw new RuntimeException("验证码已过期，请重新发送");
        }
        if(!storedCode.equals(dto.getCode())){
            throw new RuntimeException("验证码错误");
        }
        String new_password=passwordUtil.hash(dto.getNew_password_hash());
        int res=userMapper.changePassword(new_password,user.getUsername(), LocalDateTime.now());
        if (res<=0){
            throw new RuntimeException("密码修改失败");
        }
        return ; }
    @Override
    public void logout(String authorization) {
        if (authorization == null || !authorization.startsWith("Bearer ")) {
            throw new RuntimeException("无效的令牌格式");
        }

        String token = authorization.substring(7);
        // 从 Redis 中删除令牌，后续请求视为未登录
        redisTemplate.delete("token:" + token);
    }


    private UserVO toUserVO(Sys_User user) {
        UserVO vo = new UserVO();
        BeanUtil.copyProperties(user, vo);
        return vo;
    }
}
