package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 修改当前密码请求参数 (API-07)
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class PasswordChangeDTO {
    private String current_password_hash;
    private String new_password_hash;
}
