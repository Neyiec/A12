package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * AI配置回滚请求参数 (API-101)
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class RollbackDTO {
    private int target_version;
    private String reason;
}
