package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 更新角色信息请求参数（API-80B）
 * 所有字段可选，仅更新传入的字段；role_code 为角色标识，不支持修改
 * 启停角色（status 变更）会即时影响持有该角色用户的有效权限
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class RoleUpdateDTO {
    private String role_name;   //角色名称（选填，全局唯一，最长 50）
    private String description; //角色说明（选填，最长 255）
    private Integer sort_order; //展示排序（选填）
    private Integer status;     //是否启用 1启用/0停用（选填）
}
