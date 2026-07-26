package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 确认资源上传请求参数 (API-33)
 * 前端直传 OSS 成功后，携带 object_key 等信息通知后端入库
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ResourceUploadConfirmDTO {
    private String object_key;
    private String file_name;
    private long file_size;
    private String file_type;
    private String description;
    private Integer replace_target_id;
}
