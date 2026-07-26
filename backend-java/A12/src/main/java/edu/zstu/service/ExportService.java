package edu.zstu.service;

/**
 * 成果导出中心 Service 接口<br>提供导出预检、导出任务管理、成果文件获取等导出相关业务方法。
 */

public interface ExportService {
    Object precheckExport(String id);
    Object createExportTask();
    Object listExportTasks();
    Object getExportTask(String id);
    Object cancelExport(String id);
    Object retryExport(String id);
    Object getQualityReport(String id);
    Object getArtifact(String id);
    Object createPreviewUrl(String id);
    Object createDownloadUrl(String id);
}

