package edu.zstu.controller;

import edu.zstu.dto.*;
import edu.zstu.service.AuthService;
import edu.zstu.utils.Result;
import edu.zstu.vo.LoginVO;
import edu.zstu.vo.UserVO;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * 认证模块 Controller
 * API-01~08：注册、登录、密码管理、退出
 *
 * <p>负责用户注册、登录、邮箱验证码、密码重置、初始密码修改、当前密码修改以及退出登录等认证相关操作。</p>
 */
@RestController
@RequestMapping("/api/v1/auth")
public class AuthController {
    @Autowired
    private AuthService authService;

    /**
     * API 检查用户名是否存在
     */
    @GetMapping("/check-username")
    public Result<Map<String, Boolean>> checkUsername(@RequestParam String username) {
        return Result.success(Map.of("exists", authService.checkUsername(username)));
    }

    /**
     * API 检查邮箱是否存在
     */
    @GetMapping("/check-email")
    public Result<Map<String, Boolean>> checkEmail(@RequestParam String email) {
        return Result.success(Map.of("exists", authService.checkEmail(email)));
    }

    /**
     * API-01 注册教师账号
     */
    @PostMapping("/register")
    public Result<UserVO> register(@RequestBody RegisterDTO dto) {
        try {
            return Result.success(authService.register(dto));
        } catch (RuntimeException e) {
            return Result.error(400, e.getMessage());
        }
    }

    /**
     * API-02 发送邮箱验证码
     */
    @PostMapping("/verification-codes")
    public Result<Void> sendVerificationCode(@RequestBody VerificationCodeDTO dto) {
        try {
            authService.sendVerificationCode(dto);
            return Result.success();
        } catch (RuntimeException e) {
            return Result.error(400, e.getMessage());
        }
    }

    /**
     * API-03 校验验证码
     */
    @PostMapping("/verify")
    public Result<Void> verify(@RequestBody VerifyDTO dto) {
        try {
            authService.verify(dto);
            return Result.success();
        } catch (RuntimeException e) {
            return Result.error(400, e.getMessage());
        }
    }

    /**
     * API-04 统一登录
     */
    @PostMapping("/login")
    public Result<LoginVO> login(@RequestBody LoginDTO dto) {
        try {
            return Result.success(authService.login(dto));
        } catch (RuntimeException e) {
            return Result.error(400, e.getMessage());
        }
    }

    /**
     * API-05 首次登录强制改密
     */
    @PostMapping("/initial-password-change")
    public Result<LoginVO> initialPasswordChange(@RequestBody InitialPasswordChangeDTO dto) {
        return Result.success(authService.initialPasswordChange(dto));
    }

    /**
     * API-06 通过验证码重置密码
     */
    @PostMapping("/password-reset")
    public Result<Void> passwordReset(@RequestBody PasswordResetDTO dto) {
        authService.passwordReset(dto);
        return Result.success();
    }

    /**
     * API-08 退出登录
     */
    @PostMapping("/logout")
    public Result<Void> logout(@RequestHeader("Authorization") String authorization) {
        try {
            authService.logout(authorization);
            return Result.success();
        } catch (RuntimeException e) {
            return Result.error(400, e.getMessage());
        }
    }
}
