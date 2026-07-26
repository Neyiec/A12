package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 修改当前密码请求参数 (API-07)，前端传明文，后端哈希后存储
*/
@Data
@NoArgsConstructor
@AllArgsConstructor
public class PasswordChangeDTO {
    private String current_password;
    private String new_password;
}
