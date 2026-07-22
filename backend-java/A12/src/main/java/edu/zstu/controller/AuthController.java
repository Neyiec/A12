package edu.zstu.controller;

import edu.zstu.utils.Result;
import org.springframework.web.bind.annotation.*;

/**
 * 认证模块 Controller
 * API-01~08：注册、验证码、登录、改密、退出
 */
@RestController
@RequestMapping("/api/v1/auth")
public class AuthController {

    @PostMapping("/register")
    public Result<?> register() {
        return Result.success();
    }

    @PostMapping("/verification-codes")
    public Result<?> sendVerificationCode() {
        return Result.success();
    }

    @PostMapping("/verify")
    public Result<?> verify() {
        return Result.success();
    }

    @PostMapping("/login")
    public Result<?> login() {
        return Result.success();
    }

    @PostMapping("/initial-password-change")
    public Result<?> initialPasswordChange() {
        return Result.success();
    }

    @PostMapping("/password-reset")
    public Result<?> passwordReset() {
        return Result.success();
    }

    @PostMapping("/logout")
    public Result<?> logout() {
        return Result.success();
    }
}
