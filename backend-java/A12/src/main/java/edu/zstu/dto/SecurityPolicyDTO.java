package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 更新安全策略请求参数 (API-103)
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class SecurityPolicyDTO {
    private String config_value;
    private int version;
}
