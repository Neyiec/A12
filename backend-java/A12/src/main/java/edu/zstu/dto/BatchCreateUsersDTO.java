package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 批量创建后台账号请求参数 (API-75)
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class BatchCreateUsersDTO {
    private String idempotent_key;
    private String users;
}
