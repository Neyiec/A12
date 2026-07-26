package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 教师注册请求参数 (API-01)
 * 前端传明文 password，后端哈希后存储
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class RegisterDTO {
    private String username;
    private String password;
    private String real_name;
    private String phone;
    private String email;
    private String avatar;
    private String code;
}
