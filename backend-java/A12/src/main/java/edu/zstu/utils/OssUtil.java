package edu.zstu.utils;

import com.aliyun.oss.OSS;
import com.aliyun.oss.internal.OSSHeaders;
import com.aliyun.oss.model.GeneratePresignedUrlRequest;
import org.springframework.stereotype.Component;

import java.io.InputStream;
import java.net.URL;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;

@Component
public class OssUtil {

    private final OSS ossClient;
    private final OssConfig ossConfig;

    public OssUtil(OSS ossClient, OssConfig ossConfig) {
        this.ossClient = ossClient;
        this.ossConfig = ossConfig;
    }

    /** 生成 OSS 文件上传签名 URL（PUT） */
    public URL generateUploadUrl(String objectKey, String content_type, long expiresMinutes) {
        Date expiration = new Date(System.currentTimeMillis() + expiresMinutes * 60 * 1000);
        GeneratePresignedUrlRequest request = new GeneratePresignedUrlRequest(
                ossConfig.getBucketName(), objectKey, com.aliyun.oss.HttpMethod.PUT);
        request.setExpiration(expiration);
        Map<String, String> headers = new HashMap<String, String>();
        headers.put(OSSHeaders.CONTENT_TYPE, content_type);
        request.setHeaders(headers);
        return ossClient.generatePresignedUrl(request);
    }

    /** 生成 OSS 文件下载签名 URL（GET） */
    public URL generateDownloadUrl(String objectKey, long expiresMinutes) {
        Date expiration = new Date(System.currentTimeMillis() + expiresMinutes * 60 * 1000);
        GeneratePresignedUrlRequest request = new GeneratePresignedUrlRequest(
                ossConfig.getBucketName(), objectKey, com.aliyun.oss.HttpMethod.GET);
        request.setExpiration(expiration);
        return ossClient.generatePresignedUrl(request);
    }

    /** 上传文件流到 OSS */
    public void putObject(String objectKey, InputStream inputStream) {
        ossClient.putObject(ossConfig.getBucketName(), objectKey, inputStream);
    }

    /** 判断文件是否存在 */
    public boolean doesObjectExist(String objectKey) {
        return ossClient.doesObjectExist(ossConfig.getBucketName(), objectKey);
    }

    /** 删除文件 */
    public void deleteObject(String objectKey) {
        ossClient.deleteObject(ossConfig.getBucketName(), objectKey);
    }

    /**
     * 为索引同步等服务间调用生成临时下载 URL（默认 60 分钟有效）
     * 规则：剥离已有签名参数后，若为本 bucket 的 OSS 地址则重签 GET URL；
     * 非 OSS 地址原样返回，避免误签外部链接
     */
    public String resolveDownloadUrl(String fileUrl, long expiresMinutes) {
        String objectKey = tryExtractObjectKey(fileUrl);
        if (objectKey == null) {
            return fileUrl;
        }
        return generateDownloadUrl(objectKey, expiresMinutes).toString();
    }

    /** 判断是否本 bucket 的 OSS 地址并提取 objectKey（自动剥离签名参数），非本 bucket 地址返回 null */
    public String tryExtractObjectKey(String fileUrl) {
        if (fileUrl == null || fileUrl.isBlank()) {
            return null;
        }
        String plainUrl = fileUrl.split("\\?", 2)[0];
        String prefix = "https://" + ossConfig.getBucketName() + "." + ossConfig.getEndpoint() + "/";
        return plainUrl.startsWith(prefix) ? plainUrl.substring(prefix.length()) : null;
    }

    /** 从完整 OSS URL 中提取 objectKey */
    public String extractObjectKey(String ossUrl) {
        String prefix = "https://" + ossConfig.getBucketName() + "." + ossConfig.getEndpoint() + "/";
        if (ossUrl.startsWith(prefix)) {
            return ossUrl.substring(prefix.length());
        }
        // 兼容 endpoint 包含 bucket 路径的情况
        return ossUrl.substring(ossUrl.indexOf("/", ossUrl.indexOf("://") + 3) + 1);
    }

    /** 获取文件公开访问的完整 URL */
    public String getObjectUrl(String objectKey) {
        return "https://" + ossConfig.getBucketName() + "." + ossConfig.getEndpoint() + "/" + objectKey;
    }
}
