package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 用户状态更新请求参数 (API-73)
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class UserStatusDTO {
    private int is_active;
}
