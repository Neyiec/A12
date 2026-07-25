package edu.zstu.service.impl;

import edu.zstu.service.ResourceService;
import org.springframework.stereotype.Service;

/**
 * 个人资源库 Service 实现
 */
@Service
public class ResourceServiceImpl implements ResourceService {
    @Override
    public Object createUploadSession() { return null; }
    @Override
    public Object completeUpload(String id) { return null; }
    @Override
    public Object listResources() { return null; }
    @Override
    public Object getResource(String id) { return null; }
    @Override
    public Object updateResource(String id) { return null; }
    @Override
    public Object deleteResource(String id) { return null; }
    @Override
    public Object batchAction() { return null; }
    @Override
    public Object getPermission(String id) { return null; }
    @Override
    public Object setPermission(String id) { return null; }
    @Override
    public Object getAuditLogs(String id) { return null; }
    @Override
    public Object getDownloadUrl(String id) { return null; }
}
