package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 生成上传令牌请求参数
 * 前端传文件名等元数据，后端返回 OSS 签名上传 URL
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class UploadTokenDTO {
    private String file_name;
    private String file_type;
    private String description;
    private Integer replace_target_id;
}
