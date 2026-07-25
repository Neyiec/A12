package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 校验验证码请求参数 (API-03)
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class VerifyDTO {
    private String username;
    private String code;
    private String scene;
}
