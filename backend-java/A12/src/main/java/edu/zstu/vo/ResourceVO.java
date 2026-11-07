package edu.zstu.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 公共资源信息
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ResourceVO {
    private int id;
    private String resource_type;
    private String title;
    private String subject;
    private String grade;
    private String file_url;
    private String template_data;
    private String thumbnail;
    private String description;
    private String source_metadata;
    private Long file_size;
    private int status;
    private Integer uploaded_by;
    private String ai_index_status;
    private LocalDateTime ai_indexed_at;
    private String ai_index_error;
    private LocalDateTime created_at;
    private LocalDateTime updated_at;
}
