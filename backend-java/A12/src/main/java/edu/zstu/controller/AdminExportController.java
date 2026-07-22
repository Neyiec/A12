package edu.zstu.controller;

import edu.zstu.utils.Result;
import org.springframework.web.bind.annotation.*;

/**
 * 后台 — 导出模板模块 Controller
 * API-94~97：模板管理、版本、状态
 */
@RestController
@RequestMapping("/api/v1/admin/export-templates")
public class AdminExportController {

    @GetMapping
    public Result<?> listTemplates() {
        return Result.success();
    }

    @PostMapping
    public Result<?> createTemplate() {
        return Result.success();
    }

    @PatchMapping("/{id}")
    public Result<?> updateTemplate(@PathVariable String id) {
        return Result.success();
    }

    @PutMapping("/{id}/status")
    public Result<?> updateTemplateStatus(@PathVariable String id) {
        return Result.success();
    }
}
