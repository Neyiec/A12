package edu.zstu.service.impl;

import edu.zstu.service.ExportService;
import org.springframework.stereotype.Service;

/**
 * 成果导出中心 Service 实现
 */
@Service
public class ExportServiceImpl implements ExportService {
    @Override
    public Object precheckExport(String id) { return null; }
    @Override
    public Object createExportTask() { return null; }
    @Override
    public Object listExportTasks() { return null; }
    @Override
    public Object getExportTask(String id) { return null; }
    @Override
    public Object cancelExport(String id) { return null; }
    @Override
    public Object retryExport(String id) { return null; }
    @Override
    public Object getQualityReport(String id) { return null; }
    @Override
    public Object getArtifact(String id) { return null; }
    @Override
    public Object createPreviewUrl(String id) { return null; }
    @Override
    public Object createDownloadUrl(String id) { return null; }
}
