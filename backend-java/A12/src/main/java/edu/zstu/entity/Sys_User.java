package edu.zstu.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;


import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class Sys_User{
    private int id;
    private String username;
    private String password_hash;
    private String real_name;
    private String email;
    private String phone;
    private String avatar; //头像url
    // 角色与权限已迁移至 RBAC 表（sys_role/sys_permission/sys_user_role/sys_role_permission），见 SysRoleMapper
    private int is_active; //是否激活 1表示是 0表示否
    private Integer email_verified;
    private Integer phone_verified;
    private LocalDateTime last_login_at;
    private String last_login_ip;
    private LocalDateTime password_changed_at;
    private LocalDateTime deleted_at;
    private LocalDateTime created_at;
    private LocalDateTime updated_at;

}
