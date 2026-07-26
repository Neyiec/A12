package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 发送验证码请求参数 (API-02)
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class VerificationCodeDTO {
    private String username;
    private String scene;
    private String channel;
}
