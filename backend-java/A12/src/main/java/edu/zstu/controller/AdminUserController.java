package edu.zstu.controller;

import edu.zstu.dto.UserDTO;
import edu.zstu.dto.UserQueryDTO;
import edu.zstu.dto.UserStatusDTO;
import edu.zstu.dto.BatchCreateUsersDTO;
import edu.zstu.dto.AssignRolesDTO;
import edu.zstu.dto.RolePermissionsDTO;
import edu.zstu.utils.Result;
import edu.zstu.vo.UserVO;
import org.springframework.web.bind.annotation.*;

/**
 * 后台 — 用户权限模块 Controller
 * API-71~78：用户管理、角色分配、权限配置
 *
 * <p>管理员对用户进行管理：分页查询、查看详情、启用/停用/锁定、创建账号、
 * 角色分配以及权限配置。支持单个创建和幂等批量创建。</p>
 */
@RestController
@RequestMapping("/api/v1/admin")
public class AdminUserController {

    /**
     * API-71 分页查询用户
     *
     * <p>按角色、账号状态和关键词分页查询用户。</p>
     *
     * @param dto 查询参数（keyword、user_type、is_active、page、size 均为选填）
     * @return 分页用户列表 {@link UserVO}
     */
    @GetMapping("/users")
    public Result<?> listUsers(UserQueryDTO dto) {
        return Result.success();
    }

    /**
     * API-72 获取用户详情
     *
     * <p>获取用户状态、角色、权限摘要及账号安全状态。</p>
     *
     * @param id 用户ID（路径参数）
     * @return 用户详情 {@link UserVO}
     */
    @GetMapping("/users/{id}")
    public Result<UserVO> getUser(@PathVariable String id) {
        return Result.success();
    }

    /**
     * API-73 启用/停用/锁定用户
     *
     * <p>启用、停用或锁定用户账号。停用和锁定时撤销相关会话。</p>
     *
     * @param id        用户ID（路径参数）
     * @param is_active 状态：0=停用, 1=启用, -1=锁定（必填）
     * @return 更新后的用户信息 {@link UserVO}
     */
    @PatchMapping("/users/{id}/status")
    public Result<UserVO> updateUserStatus(@PathVariable String id, @RequestBody UserStatusDTO dto) {
        return Result.success();
    }

    /**
     * API-74 创建单个后台账号
     *
     * <p>创建单个内容审核员或受控后台账号。</p>
     *
     * @param dto 用户创建参数 {@link UserDTO}
     * @return 创建的用户信息 {@link UserVO}
     */
    @PostMapping("/users")
    public Result<UserVO> createUser(@RequestBody UserDTO dto) {
        return Result.success();
    }

    /**
     * API-75 批量创建后台账号
     *
     * <p>按幂等键批量创建受控后台账号，返回逐项成功、失败和初始凭据安全交付结果。</p>
     *
     * @param idempotent_key 幂等键（必填）
     * @param users          用户列表 JSON（必填）
     * @return 逐项处理结果
     */
    @PostMapping("/users/batch")
    public Result<?> batchCreateUsers(@RequestBody BatchCreateUsersDTO dto) {
        return Result.success();
    }

    /**
     * API-76 查询角色列表
     *
     * <p>查询后台角色、权限集合及审核范围。</p>
     *
     * @return 角色列表
     */
    @GetMapping("/roles")
    public Result<?> listRoles() {
        return Result.success();
    }

    /**
     * API-77 分配用户角色
     *
     * <p>为指定用户分配系统管理员或内容审核员角色。</p>
     *
     * @param id    用户ID（路径参数）
     * @param roles 角色列表 JSON（必填）
     * @return 更新后的用户信息 {@link UserVO}
     */
    @PutMapping("/users/{id}/roles")
    public Result<UserVO> assignRoles(@PathVariable String id, @RequestBody AssignRolesDTO dto) {
        return Result.success();
    }

    /**
     * API-78 配置角色权限
     *
     * <p>配置后台功能权限、公共资源权限及内容审核范围。</p>
     *
     * @param id          角色ID（路径参数）
     * @param permissions 权限列表 JSON（必填）
     * @return 操作结果（无数据体）
     */
    @PutMapping("/roles/{id}/permissions")
    public Result<Void> updateRolePermissions(@PathVariable String id, @RequestBody RolePermissionsDTO dto) {
        return Result.success();
    }
}
