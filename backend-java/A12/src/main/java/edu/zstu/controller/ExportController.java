package edu.zstu.controller;

import edu.zstu.dto.ExportTaskDTO;
import edu.zstu.dto.ExportPrecheckDTO;
import edu.zstu.dto.TaskQueryDTO;
import edu.zstu.service.ExportService;
import edu.zstu.utils.Result;
import edu.zstu.vo.ExportTaskVO;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import java.util.Map;

import java.nio.charset.StandardCharsets;

/**
 * 成果导出中心 Controller
 * API-43~52：导出预检、任务管理、文件获取
 *
 * <p>负责教学项目的导出预检、异步导出任务的创建与管理、质量报告查看
 * 以及最终成果文件的预览和下载。</p>
 */
@RestController
@RequestMapping("/api/v1")
public class ExportController {
    @Autowired
    private ExportService exportService;

    /**
     * API-43 导出预检
     *
     * <p>检查项目快照、素材、字体、兼容性、版权和敏感信息。</p>
     *
     * @param id               项目ID（路径参数）
     * @param dto              导出预检请求参数 {@link ExportPrecheckDTO}
     * @return 预检结果（passed、warnings、errors）
     */
    @PostMapping("/projects/{id}/export-prechecks")
    public Result<?> precheckExport(@PathVariable String id,
                                    @RequestBody ExportPrecheckDTO dto) {
        try {
            return Result.success(exportService.precheckExport(id, dto));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-44 创建导出任务
     *
     * <p>绑定项目快照、模板版本和导出参数，创建异步导出任务。</p>
     *
     * @param dto 导出任务创建参数 {@link ExportTaskDTO}
     * @return 创建的导出任务详情 {@link ExportTaskVO}
     */
    @PostMapping("/export-tasks")
    public Result<ExportTaskVO> createExportTask(@RequestBody ExportTaskDTO dto) {
        try {
            return Result.success(exportService.createExportTask(dto));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /** 校验任务归属后提供已保存的项目页面，供浏览器直连 Python 导出。 */
    @GetMapping("/export-tasks/{id}/payload")
    public Result<Map<String, Object>> getExportPayload(@PathVariable String id) {
        try { return Result.success(exportService.getExportPayload(id)); }
        catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /** 仅接收 Python 已生成的文件并登记业务成果，不运行 AI。 */
    @PostMapping(value = "/export-tasks/{id}/artifact", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Result<ExportTaskVO> completeExportTask(@PathVariable String id, @RequestParam("file") MultipartFile file) {
        try { return Result.success(exportService.completeExportTask(id, file)); }
        catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PostMapping("/export-tasks/{id}/failure")
    public Result<ExportTaskVO> failExportTask(@PathVariable String id, @RequestBody Map<String, String> body) {
        try { return Result.success(exportService.failExportTask(id, body.get("error"))); }
        catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-45 分页查询导出任务
     *
     * <p>分页查询本人或获授权的导出任务。</p>
     *
     * @param dto 查询参数（status、export_type、page、size 均为选填）
     * @return 分页导出任务列表
     */
    @GetMapping("/export-tasks")
    public Result<?> listExportTasks(TaskQueryDTO dto) {
        try {
            return Result.success(exportService.listExportTasks(dto));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-46 获取导出任务详情
     *
     * <p>查看进度、失败原因、质量状态和文件状态。</p>
     *
     * @param id 导出任务ID（路径参数）
     * @return 导出任务详情 {@link ExportTaskVO}
     */
    @GetMapping("/export-tasks/{id}")
    public Result<ExportTaskVO> getExportTask(@PathVariable String id) {
        try {
            return Result.success(exportService.getExportTask(id));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @GetMapping("/export-tasks/{id}/progress")
    public Result<ExportTaskVO> getExportProgress(@PathVariable String id) {
        try {
            return Result.success(exportService.getExportProgress(id));
        } catch (org.springframework.dao.DataAccessException e) {
            throw e;
        } catch (RuntimeException e) {
            return Result.error(400, e.getMessage());
        }
    }

    /**
     * API-47 取消导出任务
     *
     * <p>取消排队中或生成中的任务。</p>
     *
     * @param id 导出任务ID（路径参数）
     * @return 取消后的任务 {@link ExportTaskVO}
     */
    @PostMapping("/export-tasks/{id}/cancel")
    public Result<ExportTaskVO> cancelExport(@PathVariable String id) {
        try {
            return Result.success(exportService.cancelExport(id));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-48 重试导出任务
     *
     * <p>按原项目快照和导出参数重新执行。</p>
     *
     * @param id 导出任务ID（路径参数）
     * @return 新执行的导出任务 {@link ExportTaskVO}
     */
    @PostMapping("/export-tasks/{id}/retry")
    public Result<ExportTaskVO> retryExport(@PathVariable String id) {
        try {
            return Result.success(exportService.retryExport(id));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-49 获取质量报告
     *
     * <p>获取导出质量报告、警告和降级项。</p>
     *
     * @param id 导出任务ID（路径参数）
     * @return 质量报告数据
     */
    @GetMapping("/export-tasks/{id}/quality-report")
    public Result<?> getQualityReport(@PathVariable String id) {
        try {
            return Result.success(exportService.getQualityReport(id));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-50 获取成果文件元数据
     *
     * <p>获取成果文件元数据、文件状态、缩略图清单和可预览类型。</p>
     *
     * @param id 成果文件ID（路径参数）
     * @return 成果文件信息 {@link ExportTaskVO}
     */
    @GetMapping("/export-artifacts/{id}")
    public Result<ExportTaskVO> getArtifact(@PathVariable String id) {
        try {
            return Result.success(exportService.getArtifact(id));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-51 生成预览地址
     *
     * <p>校验权限并生成成果缩略图或预览文件的短时访问地址。</p>
     *
     * @param id 成果文件ID（路径参数）
     * @return 预览地址及过期时间
     */
    @PostMapping("/export-artifacts/{id}/preview-url")
    public Result<?> createPreviewUrl(@PathVariable String id) {
        try {
            return Result.success(exportService.createPreviewUrl(id));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-52 生成下载链接
     *
     * <p>生成成果文件的短时下载链接。</p>
     *
     * @param id 成果文件ID（路径参数）
     * @return 下载地址及过期时间
     */
    @PostMapping("/export-artifacts/{id}/download-url")
    public Result<?> createDownloadUrl(@PathVariable String id) {
        try {
            return Result.success(exportService.createDownloadUrl(id));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-52A 下载成果文件（流式）
     *
     * <p>校验任务归属、文件可用性与过期时间后，从本地导出目录读取成果文件，
     * 以正确的 Content-Type 和附件文件名流式返回，替代原先无人服务的 /exports 静态路径。</p>
     *
     * @param id 成果文件ID（路径参数）
     * @return 成果文件字节流
     */
    @GetMapping("/export-artifacts/{id}/file")
    public ResponseEntity<byte[]> downloadExportFile(@PathVariable String id) {
        try {
            ExportService.ExportFileResult file = exportService.getExportFile(id);
            return ResponseEntity.ok()
                    .contentType(MediaType.parseMediaType(file.contentType()))
                    .header(HttpHeaders.CONTENT_DISPOSITION, ContentDisposition.attachment()
                            .filename(file.filename(), StandardCharsets.UTF_8)
                            .build().toString())
                    .contentLength(file.bytes().length)
                    .body(file.bytes());
        } catch (RuntimeException e) {
            String message = "{\"code\":400,\"message\":\"" + escapeJson(e.getMessage()) + "\",\"data\":null}";
            return ResponseEntity.status(HttpStatus.BAD_REQUEST)
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(message.getBytes(StandardCharsets.UTF_8));
        }
    }

    private String escapeJson(String value) {
        if (value == null) return "";
        return value.replace("\\", "\\\\").replace("\"", "\\\"");
    }
}
