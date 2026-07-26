package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 配置角色权限请求参数 (API-78)
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class RolePermissionsDTO {
    private String permissions;
}
