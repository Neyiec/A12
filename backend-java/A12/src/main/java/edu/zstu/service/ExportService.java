package edu.zstu.service;

import edu.zstu.dto.ExportPrecheckDTO;
import edu.zstu.dto.ExportTaskDTO;
import edu.zstu.dto.TaskQueryDTO;
import edu.zstu.utils.PageResult;
import edu.zstu.vo.ExportTaskVO;

import java.util.Map;
import org.springframework.web.multipart.MultipartFile;

/**
 * 成果导出中心 Service 接口<br>提供导出预检、导出任务管理、成果文件获取等导出相关业务方法。
 */

public interface ExportService {
    Map<String, Object> precheckExport(String id, ExportPrecheckDTO dto);
    ExportTaskVO createExportTask(ExportTaskDTO dto);
    Map<String, Object> getExportPayload(String id);
    ExportTaskVO completeExportTask(String id, MultipartFile file);
    ExportTaskVO failExportTask(String id, String error);
    PageResult<ExportTaskVO> listExportTasks(TaskQueryDTO dto);
    ExportTaskVO getExportTask(String id);
    ExportTaskVO cancelExport(String id);
    ExportTaskVO retryExport(String id);
    Map<String, Object> getQualityReport(String id);
    ExportTaskVO getArtifact(String id);
    Map<String, Object> createPreviewUrl(String id);
    Map<String, Object> createDownloadUrl(String id);
    ExportFileResult getExportFile(String id);

    /** 成果文件流式下载结果 */
    record ExportFileResult(String filename, String contentType, byte[] bytes) {
    }
}

