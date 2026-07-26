package edu.zstu.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 上传令牌响应
 * 包含 OSS 签名 URL、对象键和过期时间
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class UploadTokenVO {
    private String object_key;
    private String upload_url;
    private LocalDateTime expires_at;
}
