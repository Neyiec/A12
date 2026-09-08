package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 用户后台新增/修改请求参数，前端传明文 password，后端哈希后存储
 * 不含 id、created_at、updated_at 等后端自动生成字段
 * 说明: RBAC 重构后 user_type 不再落库（兼容旧前端仍会传入，后端忽略）；
 *       roles 为角色编码(role_code)数组 JSON 字符串，如 ["teacher","admin"]，写入 sys_user_role
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class UserDTO {
    private String username;
    private String password;
    private String real_name;
    private String phone;
    private String email;
    private String avatar;
    private String user_type;   //已废弃，后端忽略
    private String roles;       //角色编码数组 JSON 字符串
    private String permissions; //已废弃，后端忽略（角色权限走 API-82 写 sys_role_permission）
    private int is_active;      //后端不读取，启停走 API-77
}
