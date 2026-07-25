package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 资源批量操作请求参数 (API-38)
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ResourceBatchActionDTO {
    private String idempotent_key;
    private String action;
    private String resource_ids;
    private String target;
}
