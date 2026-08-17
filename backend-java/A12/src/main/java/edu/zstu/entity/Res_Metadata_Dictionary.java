package edu.zstu.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class Res_Metadata_Dictionary {
    private Integer id;
    private Integer user_id;
    private String dict_type;
    private String name;
    private String color;
    private Integer sort_order;
    private Integer usage_count;
    private Integer status;
    private LocalDateTime created_at;
    private LocalDateTime updated_at;
}
