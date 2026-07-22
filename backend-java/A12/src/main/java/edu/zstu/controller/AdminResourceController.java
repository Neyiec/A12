package edu.zstu.controller;

import edu.zstu.utils.Result;
import org.springframework.web.bind.annotation.*;

/**
 * 后台 — 公共资源模块 Controller
 * API-79~85：公共资源上传、检索、状态管理
 */
@RestController
@RequestMapping("/api/v1/admin/public-resources")
public class AdminResourceController {

    @GetMapping
    public Result<?> listResources() {
        return Result.success();
    }

    @PostMapping("/uploads")
    public Result<?> createUploadSession() {
        return Result.success();
    }

    @PostMapping("/uploads/{id}/complete")
    public Result<?> completeUpload(@PathVariable String id) {
        return Result.success();
    }

    @GetMapping("/{id}")
    public Result<?> getResource(@PathVariable String id) {
        return Result.success();
    }

    @PatchMapping("/{id}")
    public Result<?> updateResource(@PathVariable String id) {
        return Result.success();
    }

    @PutMapping("/{id}/status")
    public Result<?> updateStatus(@PathVariable String id) {
        return Result.success();
    }

    @GetMapping("/{id}/processing-status")
    public Result<?> getProcessingStatus(@PathVariable String id) {
        return Result.success();
    }
}
