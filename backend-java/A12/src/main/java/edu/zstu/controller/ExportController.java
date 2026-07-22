package edu.zstu.controller;

import edu.zstu.utils.Result;
import org.springframework.web.bind.annotation.*;

/**
 * 成果导出中心 Controller
 * API-43~52：导出预检、任务管理、文件获取
 */
@RestController
@RequestMapping("/api/v1")
public class ExportController {

    @PostMapping("/projects/{id}/export-prechecks")
    public Result<?> precheckExport(@PathVariable String id) {
        return Result.success();
    }

    @PostMapping("/export-tasks")
    public Result<?> createExportTask() {
        return Result.success();
    }

    @GetMapping("/export-tasks")
    public Result<?> listExportTasks() {
        return Result.success();
    }

    @GetMapping("/export-tasks/{id}")
    public Result<?> getExportTask(@PathVariable String id) {
        return Result.success();
    }

    @PostMapping("/export-tasks/{id}/cancel")
    public Result<?> cancelExport(@PathVariable String id) {
        return Result.success();
    }

    @PostMapping("/export-tasks/{id}/retry")
    public Result<?> retryExport(@PathVariable String id) {
        return Result.success();
    }

    @GetMapping("/export-tasks/{id}/quality-report")
    public Result<?> getQualityReport(@PathVariable String id) {
        return Result.success();
    }

    @GetMapping("/export-artifacts/{id}")
    public Result<?> getArtifact(@PathVariable String id) {
        return Result.success();
    }

    @PostMapping("/export-artifacts/{id}/preview-url")
    public Result<?> createPreviewUrl(@PathVariable String id) {
        return Result.success();
    }

    @PostMapping("/export-artifacts/{id}/download-url")
    public Result<?> createDownloadUrl(@PathVariable String id) {
        return Result.success();
    }
}
