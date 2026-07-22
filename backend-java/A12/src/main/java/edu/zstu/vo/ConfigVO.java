package edu.zstu.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 系统配置信息
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ConfigVO {
    private int id;
    private String config_group;
    private String config_key;
    private String config_value;
    private String description;
    private Integer updated_by;
    private LocalDateTime updated_at;
}
