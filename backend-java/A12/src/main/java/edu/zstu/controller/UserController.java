package edu.zstu.controller;

import edu.zstu.utils.Result;
import org.springframework.web.bind.annotation.*;

/**
 * 用户模块 Controller
 * API-09：个人信息；API-07 的改密放在此处（/users/me/password-change）
 */
@RestController
@RequestMapping("/api/v1/users")
public class UserController {

    @GetMapping("/me")
    public Result<?> getCurrentUser() {
        return Result.success();
    }

    @PostMapping("/me/password-change")
    public Result<?> changePassword() {
        return Result.success();
    }
}
