package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 公共资源状态更新请求参数 (API-84)
*/
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ItemStatusDTO {
    private int status;
}
