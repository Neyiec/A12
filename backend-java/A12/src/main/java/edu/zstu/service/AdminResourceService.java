package edu.zstu.service;

/**
 * 后台 — 公共资源模块 Service 接口<br>提供公共资源上传、管理、状态控制等后台资源业务方法。
 */

public interface AdminResourceService {
    Object listResources();
    Object createUploadSession();
    Object completeUpload(String id);
    Object getResource(String id);
    Object updateResource(String id);
    Object updateStatus(String id);
    Object getProcessingStatus(String id);
}

