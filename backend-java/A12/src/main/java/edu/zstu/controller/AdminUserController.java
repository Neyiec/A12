package edu.zstu.controller;

import edu.zstu.dto.*;
import edu.zstu.service.AdminUserService;
import edu.zstu.utils.PageResult;
import edu.zstu.utils.Result;
import edu.zstu.vo.UserVO;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/admin")
public class AdminUserController {

    private final AdminUserService adminUserService;

    public AdminUserController(AdminUserService adminUserService) {
        this.adminUserService = adminUserService;
    }

    @GetMapping("/users")
    public Result<PageResult<UserVO>> listUsers(UserQueryDTO dto) {
        try {
            return Result.success(adminUserService.listUsers(dto));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @GetMapping("/users/{id}")
    public Result<UserVO> getUser(@PathVariable Integer id) {
        try {
            return Result.success(adminUserService.getUser(id));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PutMapping("/users/{id}")
    public Result<UserVO> updateUser(@PathVariable Integer id, @RequestBody UserDTO dto) {
        try {
            return Result.success(adminUserService.updateUser(id, dto));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @DeleteMapping("/users/{id}")
    public Result<Void> deleteUser(@PathVariable Integer id) {
        try {
            adminUserService.deleteUser(id);
            return Result.success();
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PatchMapping("/users/{id}/status")
    public Result<UserVO> updateUserStatus(@PathVariable Integer id, @RequestBody UserStatusDTO dto) {
        try {
            return Result.success(adminUserService.updateUserStatus(id, dto));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PostMapping("/users")
    public Result<UserVO> createUser(@RequestBody UserDTO dto) {
        try {
            return Result.success(adminUserService.createUser(dto));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PostMapping("/users/batch")
    public Result<Map<String, Object>> batchCreateUsers(@RequestBody BatchCreateUsersDTO dto) {
        try {
            return Result.success(adminUserService.batchCreateUsers(dto));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @GetMapping("/roles")
    public Result<List<Map<String, Object>>> listRoles() {
        try {
            return Result.success(adminUserService.listRoles());
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PostMapping("/roles")
    public Result<Map<String, Object>> createRole(@RequestBody RoleDTO dto) {
        try {
            return Result.success(adminUserService.createRole(dto));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PutMapping("/roles/{id}")
    public Result<Map<String, Object>> updateRole(@PathVariable Integer id, @RequestBody RoleUpdateDTO dto) {
        try {
            return Result.success(adminUserService.updateRole(id, dto));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @DeleteMapping("/roles/{id}")
    public Result<Void> deleteRole(@PathVariable Integer id) {
        try {
            adminUserService.deleteRole(id);
            return Result.success();
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PutMapping("/users/{id}/roles")
    public Result<UserVO> assignRoles(@PathVariable Integer id, @RequestBody AssignRolesDTO dto) {
        try {
            return Result.success(adminUserService.assignRoles(id, dto));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PutMapping("/roles/{id}/permissions")
    public Result<Void> updateRolePermissions(@PathVariable Integer id, @RequestBody RolePermissionsDTO dto) {
        try {
            adminUserService.updateRolePermissions(id, dto);
            return Result.success();
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }
}