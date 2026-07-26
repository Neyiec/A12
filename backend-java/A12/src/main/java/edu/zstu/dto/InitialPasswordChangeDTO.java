package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 初始密码修改请求参数 (API-05)
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class InitialPasswordChangeDTO {
    private String username;
    private String initial_password;
    private String new_password;
}
