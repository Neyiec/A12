package edu.zstu.service.impl;

import edu.zstu.service.AdminResourceService;
import org.springframework.stereotype.Service;

/**
 * 后台 — 公共资源模块 Service 实现
 */
@Service
public class AdminResourceServiceImpl implements AdminResourceService {
    @Override
    public Object listResources() { return null; }
    @Override
    public Object createUploadSession() { return null; }
    @Override
    public Object completeUpload(String id) { return null; }
    @Override
    public Object getResource(String id) { return null; }
    @Override
    public Object updateResource(String id) { return null; }
    @Override
    public Object updateStatus(String id) { return null; }
    @Override
    public Object getProcessingStatus(String id) { return null; }
}
