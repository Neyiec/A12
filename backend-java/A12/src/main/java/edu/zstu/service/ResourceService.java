package edu.zstu.service;

/**
 * 个人资源库 Service 接口<br>提供文件上传、资源检索编辑、权限管理、审计日志等个人资源相关业务方法。
 */

public interface ResourceService {
    Object createUploadSession();
    Object completeUpload(String id);
    Object listResources();
    Object getResource(String id);
    Object updateResource(String id);
    Object deleteResource(String id);
    Object batchAction();
    Object getPermission(String id);
    Object setPermission(String id);
    Object getAuditLogs(String id);
    Object getDownloadUrl(String id);
}

