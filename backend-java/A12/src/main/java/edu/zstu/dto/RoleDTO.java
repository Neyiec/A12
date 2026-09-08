package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 创建角色请求参数（API-80A）
 * role_code 为全局唯一的角色标识（如 content_auditor），创建后作为角色关联与权限判定的依据
 * sort_order 缺省时追加到现有角色末尾；status 缺省为 1（启用）
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class RoleDTO {
    private String role_code;   //角色标识，全局唯一，小写字母开头
    private String role_name;   //角色名称（展示用）
    private String description; //角色说明（选填，最长 255）
    private Integer sort_order; //展示排序（选填）
    private Integer status;     //是否启用 1启用/0停用（选填，默认 1）
}
