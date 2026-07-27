package edu.zstu.controller;

import edu.zstu.dto.PasswordChangeDTO;
import edu.zstu.service.UserService;
import edu.zstu.utils.Result;
import edu.zstu.vo.UserVO;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * 用户模块 Controller
 * API-09：个人信息；API-07 的改密放在此处（/users/me/password-change）
 *
 * <p>管理当前登录用户的信息查询和密码变更操作。</p>
 */
@RestController
@RequestMapping("/api/v1/users")
public class UserController {
    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }

    /**
     * API-09 获取当前用户信息
     *
     * <p>获取当前登录用户的详细信息，包括角色、权限、联系方式及账号状态。</p>
     *
     * @return 当前用户详情 {@link UserVO}
     */
    @GetMapping("/me")
    public Result<UserVO> getCurrentUser()
    {
        UserVO user= userService.getCurrentUser();
        return Result.success(user);
    }

    /**
     * API-07 修改当前密码
     *
     * <p>校验当前密码和新密码规则，更新密码并按安全策略撤销其他会话。</p>
     *
     * @param dto 密码修改请求参数 {@link PasswordChangeDTO}
     * @return 修改结果（无数据体）
     */
    @PostMapping("/me/password-change")
    public Result<Void> changePassword(@RequestBody PasswordChangeDTO dto)
    {
        userService.changePassword(dto);
        return Result.success();
    }

    /**
     * 根据用户名查询用户ID
     */
    @GetMapping("/by-username")
    public Result<Map<String, Object>> findByUsername(@RequestParam String username) {
        try {
            return Result.success(userService.findUserIdByUsername(username));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * 根据邮箱查询用户ID
     */
    @GetMapping("/by-email")
    public Result<Map<String, Object>> findByEmail(@RequestParam String email) {
        try {
            return Result.success(userService.findUserIdByEmail(email));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }
}
