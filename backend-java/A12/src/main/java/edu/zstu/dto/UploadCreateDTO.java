package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 创建上传会话请求参数 (API-32)
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class UploadCreateDTO {
    private String file_name;
    private String file_type;
    private Long file_size;
    private Integer replace_target_id;
}
