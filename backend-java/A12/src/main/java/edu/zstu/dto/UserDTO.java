package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 用户新增/修改请求参数，前端传明文 password，后端哈希后存储
 * 不含 id、created_at、updated_at 等后端自动生成字段
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
    private String user_type;
    private String roles;
    private String permissions;
    private int is_active;
}
