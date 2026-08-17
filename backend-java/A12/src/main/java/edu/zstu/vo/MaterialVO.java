package edu.zstu.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 素材资源信息
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class MaterialVO {
    private Integer id;
    private Integer user_id;
    private String file_name;
    private String file_type;
    private String file_url;
    private Long file_size;
    private String thumbnail;
    private String description;
    private String categories;
    private String tags;
    private String access_type;
    private String authorized_users;
    private Integer allow_ai;
    private Integer status;
    private String ai_index_status;
    private LocalDateTime ai_indexed_at;
    private String ai_index_error;
    private LocalDateTime created_at;
    private LocalDateTime updated_at;
}
