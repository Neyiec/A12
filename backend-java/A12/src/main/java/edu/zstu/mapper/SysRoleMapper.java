package edu.zstu.mapper;

import edu.zstu.entity.Sys_Permission;
import edu.zstu.entity.Sys_Role;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Map;

/**
 * RBAC 角色/权限 Mapper
 * 覆盖 sys_role / sys_permission / sys_user_role / sys_role_permission 四张表
 */
@Mapper
public interface SysRoleMapper {

    // ==================== 角色查询 ====================

    Sys_Role findRoleById(@Param("id") Integer id);

    Sys_Role findRoleByCode(@Param("roleCode") String roleCode);

    /** 新增角色，生成的主键回填到 role.id */
    int insertRole(Sys_Role role);

    /** 按主键更新角色信息（动态 SET，仅更新非空字段） */
    int updateRole(Sys_Role role);

    /** 删除角色（sys_user_role / sys_role_permission 关联行由外键级联清理） */
    int deleteRoleById(@Param("id") Integer id);

    /** 全部角色（含停用），按 sort_order 排序 */
    List<Sys_Role> findAllRoles();

    /** 用户的有效角色（角色 status=1），按 sort_order 排序 */
    List<Sys_Role> findRolesByUserId(@Param("userId") Integer userId);

    /**
     * 批量查询多个用户的角色（列表页装配用）
     * 每行包含 user_id / role_id / role_code / role_name / sort_order
     */
    List<Map<String, Object>> findUserRolesByUserIds(@Param("userIds") List<Integer> userIds);

    /** 用户的有效权限编码集合（有效角色 → sys_role_permission → sys_permission，去重），接口鉴权用 */
    List<String> findPermCodesByUserId(@Param("userId") Integer userId);

    // ==================== 用户-角色关联维护 ====================

    int insertUserRole(@Param("userId") Integer userId, @Param("roleId") Integer roleId);

    int deleteUserRoles(@Param("userId") Integer userId);

    /** 拥有某角色的用户ID列表（含已软删除用户，调用方自行过滤） */
    List<Integer> findUserIdsByRoleId(@Param("roleId") Integer roleId);

    // ==================== 权限查询与角色-权限关联维护 ====================

    /** 全部启用中的权限，按 id 排序（id 顺序即种子定义的模块顺序） */
    List<Sys_Permission> findAllPermissions();

    Sys_Permission findPermissionByCode(@Param("permCode") String permCode);

    /** 角色拥有的权限 */
    List<Sys_Permission> findPermissionsByRoleId(@Param("roleId") Integer roleId);

    int deleteRolePermissions(@Param("roleId") Integer roleId);

    int insertRolePermission(@Param("roleId") Integer roleId, @Param("permissionId") Integer permissionId);

    // ==================== 统计 ====================

    /**
     * 按角色统计有效用户数（看板 users_by_type 分布）
     * 每行包含 role_code / user_count
     */
    List<Map<String, Object>> countUsersGroupByRole();
}
