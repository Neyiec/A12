package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 系统配置新增/修改请求参数
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ConfigDTO {
    private String config_group;
    private String config_key;
    private String config_value;
    private String description;
}
