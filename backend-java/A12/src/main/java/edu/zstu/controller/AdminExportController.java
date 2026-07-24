package edu.zstu.controller;

import edu.zstu.utils.Result;
import edu.zstu.dto.ExportTemplateCreateDTO;
import org.springframework.web.bind.annotation.*;

/**
 * 后台 — 导出模板模块 Controller
 * API-94~97：模板管理、版本、状态
 *
 * <p>管理员管理导出模板，包括模板检索、创建、更新（创建新版本）以及模板状态控制。</p>
 */
@RestController
@RequestMapping("/api/v1/admin/export-templates")
public class AdminExportController {

    /**
     * API-94 分页查询导出模板
     *
     * <p>分页查询导出模板、版本、适用成果类型和生效状态。</p>
     *
     * @param export_type 模板类型（选填）
     * @param status      状态（选填）
     * @param page        页码（选填，默认1）
     * @param size        每页条数（选填，默认10）
     * @return 分页模板列表
     */
    @GetMapping
    public Result<?> listTemplates(@RequestParam(required = false) String export_type,
                                   @RequestParam(required = false) String status,
                                   @RequestParam(defaultValue = "1") int page,
                                   @RequestParam(defaultValue = "10") int size) {
        return Result.success();
    }

    /**
     * API-95 创建导出模板
     *
     * <p>创建导出模板及首个版本。</p>
     *
     * @param dto 模板创建请求参数 {@link ExportTemplateCreateDTO}
     * @return 创建结果（含模板ID和版本号）
     */
    @PostMapping
    public Result<?> createTemplate(@RequestBody ExportTemplateCreateDTO dto) {
        return Result.success();
    }

    /**
     * API-96 更新导出模板
     *
     * <p>更新模板元数据或创建新的模板文件版本。</p>
     *
     * @param id            模板ID（路径参数）
     * @param dto           模板更新请求参数 {@link ExportTemplateCreateDTO}
     * @return 更新结果（含模板ID和版本号）
     */
    @PatchMapping("/{id}")
    public Result<?> updateTemplate(@PathVariable String id, @RequestBody ExportTemplateCreateDTO dto) {
        return Result.success();
    }

    /**
     * API-97 发布/停用模板版本
     *
     * <p>发布或停用指定模板版本。</p>
     *
     * @param id     模板ID（路径参数）
     * @param status 状态：published / unpublished（必填）
     * @return 操作结果（无数据体）
     */
    @PutMapping("/{id}/status")
    public Result<Void> updateTemplateStatus(@PathVariable String id,
                                             @RequestParam String status) {
        return Result.success();
    }
}
