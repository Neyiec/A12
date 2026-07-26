package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 解决告警请求参数 (API-111)
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class AlertResolveDTO {
    private String resolution;
}
