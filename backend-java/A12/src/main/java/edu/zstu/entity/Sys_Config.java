package edu.zstu.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class Sys_Config {
    private int id;
    private String config_group; //配置分组配置分组(ai_model/platform/security/template/sensitive_word)
    private String config_key; //配置键
    private String config_value; //配置值
    private String description; //描述
    private int updated_by; //更新人
    private String updated_at;
}
