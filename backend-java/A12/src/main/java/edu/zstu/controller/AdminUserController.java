package edu.zstu.controller;

import edu.zstu.utils.Result;
import org.springframework.web.bind.annotation.*;

/**
 * 后台 — 用户权限模块 Controller
 * API-71~78：用户管理、角色分配、权限配置
 */
@RestController
@RequestMapping("/api/v1/admin")
public class AdminUserController {

    @GetMapping("/users")
    public Result<?> listUsers() {
        return Result.success();
    }

    @GetMapping("/users/{id}")
    public Result<?> getUser(@PathVariable String id) {
        return Result.success();
    }

    @PatchMapping("/users/{id}/status")
    public Result<?> updateUserStatus(@PathVariable String id) {
        return Result.success();
    }

    @PostMapping("/users")
    public Result<?> createUser() {
        return Result.success();
    }

    @PostMapping("/users/batch")
    public Result<?> batchCreateUsers() {
        return Result.success();
    }

    @GetMapping("/roles")
    public Result<?> listRoles() {
        return Result.success();
    }

    @PutMapping("/users/{id}/roles")
    public Result<?> assignRoles(@PathVariable String id) {
        return Result.success();
    }

    @PutMapping("/roles/{id}/permissions")
    public Result<?> updateRolePermissions(@PathVariable String id) {
        return Result.success();
    }
}
