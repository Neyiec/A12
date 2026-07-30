package edu.zstu.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class Res_Material {
    private int id;
    private int user_id;
    private String file_name;
    private String file_type;
    private String file_url;
    private long file_size;
    private String thumbnail;
    private String description;
    private String categories;
    private String tags;
    private String access_type;
    private String authorized_users;
    private int allow_ai;
    private int status;
    private String ai_index_status;
    private LocalDateTime ai_indexed_at;
    private String ai_index_error;
    private LocalDateTime created_at;
    private LocalDateTime updated_at;
}
