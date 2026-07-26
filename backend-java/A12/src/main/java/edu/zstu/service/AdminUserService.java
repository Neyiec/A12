package edu.zstu.service;

/**
 * 后台 — 用户权限模块 Service 接口<br>提供后台用户管理、角色分配、权限配置等管理业务方法。
 */

public interface AdminUserService {
    Object listUsers();
    Object getUser(String id);
    Object updateUserStatus(String id);
    Object createUser();
    Object batchCreateUsers();
    Object listRoles();
    Object assignRoles(String id);
    Object updateRolePermissions(String id);
}

