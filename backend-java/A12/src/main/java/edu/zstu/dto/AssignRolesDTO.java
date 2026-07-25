package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 分配用户角色请求参数 (API-77)
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class AssignRolesDTO {
    private String roles;
}
