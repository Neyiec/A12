package edu.zstu.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class Sys_Config {
    private int id;
    private String config_group;
    private String config_key;
    private String config_value;
    private String description;
    private Integer updated_by;
    private LocalDateTime updated_at;
    private int version;
    private String status;
}
