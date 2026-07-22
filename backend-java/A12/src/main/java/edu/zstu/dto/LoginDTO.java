package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 用户登录请求参数
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class LoginDTO {
    private String username;
    private String password_hash;
}
