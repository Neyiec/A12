package edu.zstu.service.impl;

import edu.zstu.service.AdminUserService;
import org.springframework.stereotype.Service;

/**
 * 后台 — 用户权限模块 Service 实现
 */
@Service
public class AdminUserServiceImpl implements AdminUserService {
    @Override
    public Object listUsers() { return null; }
    @Override
    public Object getUser(String id) { return null; }
    @Override
    public Object updateUserStatus(String id) { return null; }
    @Override
    public Object createUser() { return null; }
    @Override
    public Object batchCreateUsers() { return null; }
    @Override
    public Object listRoles() { return null; }
    @Override
    public Object assignRoles(String id) { return null; }
    @Override
    public Object updateRolePermissions(String id) { return null; }
}
