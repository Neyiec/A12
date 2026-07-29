package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 素材资源上传/编辑请求参数
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class MaterialDTO {
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
    private Integer replace_target_id;
}
