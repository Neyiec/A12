package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 密码重置请求参数 (API-06)
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class PasswordResetDTO {
    private String username;
    private String code;
    private String new_password;
}
