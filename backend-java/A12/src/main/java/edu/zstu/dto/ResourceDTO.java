package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 公共资源管理请求参数（新增/编辑资源）
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ResourceDTO {
    private String resource_type;
    private String title;
    private String subject;
    private String grade;
    private String file_name;
    private String file_type;
    private String file_url;
    private String template_data;
    private String thumbnail;
    private String description;
    private Long file_size;
    private int status;
}
