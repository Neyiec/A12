package edu.zstu.controller;

import edu.zstu.dto.ItemStatusDTO;
import edu.zstu.dto.ResourceDTO;
import edu.zstu.service.AdminResourceService;
import edu.zstu.utils.CurrentHolder;
import edu.zstu.utils.PageResult;
import edu.zstu.utils.Result;
import edu.zstu.vo.ResourceVO;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/v1/admin/public-resources")
public class AdminResourceController {

    private final AdminResourceService adminResourceService;

    public AdminResourceController(AdminResourceService adminResourceService) {
        this.adminResourceService = adminResourceService;
    }

    @GetMapping
    public Result<PageResult<ResourceVO>> listResources(
            @RequestParam(required = false) String resource_type,
            @RequestParam(required = false) Integer status,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size) {
        try {
            return Result.success(adminResourceService.listResources(resource_type, status, page, size));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PostMapping("/uploads")
    public Result<Map<String, Object>> createUploadSession(@RequestBody ResourceDTO dto) {
        try {
            Integer adminId = CurrentHolder.getCurrentId();
            if (adminId == null) return Result.error(401, "未登录");
            return Result.success(adminResourceService.createUploadSession(dto, adminId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PostMapping("/uploads/{id}/complete")
    public Result<ResourceVO> completeUpload(@PathVariable Integer id) {
        try {
            Integer adminId = CurrentHolder.getCurrentId();
            if (adminId == null) return Result.error(401, "未登录");
            return Result.success(adminResourceService.completeUpload(id, adminId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @GetMapping("/{id}")
    public Result<ResourceVO> getResource(@PathVariable Integer id) {
        try {
            return Result.success(adminResourceService.getResource(id));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PatchMapping("/{id}")
    public Result<ResourceVO> updateResource(@PathVariable Integer id, @RequestBody ResourceDTO dto) {
        try {
            Integer adminId = CurrentHolder.getCurrentId();
            if (adminId == null) return Result.error(401, "未登录");
            return Result.success(adminResourceService.updateResource(id, dto, adminId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PutMapping("/{id}/status")
    public Result<ResourceVO> updateStatus(@PathVariable Integer id, @RequestBody ItemStatusDTO dto) {
        try {
            Integer adminId = CurrentHolder.getCurrentId();
            if (adminId == null) return Result.error(401, "未登录");
            return Result.success(adminResourceService.updateStatus(id, dto, adminId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @DeleteMapping("/{id}")
    public Result<ResourceVO> deleteResource(@PathVariable Integer id) {
        try {
            Integer adminId = CurrentHolder.getCurrentId();
            if (adminId == null) return Result.error(401, "未登录");
            return Result.success(adminResourceService.deleteResource(id, adminId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PostMapping("/{id}/reparse")
    public Result<ResourceVO> reparseResource(@PathVariable Integer id) {
        try {
            Integer adminId = CurrentHolder.getCurrentId();
            if (adminId == null) return Result.error(401, "未登录");
            return Result.success(adminResourceService.reparseResource(id, adminId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @GetMapping("/{id}/download-url")
    public Result<Map<String, Object>> getDownloadUrl(@PathVariable Integer id) {
        try {
            return Result.success(adminResourceService.getDownloadUrl(id));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @GetMapping("/{id}/processing-status")
    public Result<Map<String, Object>> getProcessingStatus(@PathVariable Integer id) {
        try {
            return Result.success(adminResourceService.getProcessingStatus(id));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PostMapping("/ai-index/bootstrap")
    public Result<Map<String, Object>> bootstrapAiResourceIndex(
            @RequestParam(defaultValue = "false") boolean force_reparse) {
        try {
            return Result.success(adminResourceService.bootstrapAiResourceIndex(force_reparse));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @GetMapping("/ai-index/overview")
    public Result<Map<String, Object>> aiIndexOverview() {
        try {
            return Result.success(adminResourceService.aiIndexOverview());
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @GetMapping("/ai-index/tasks")
    public Result<Map<String, Object>> aiIndexTasks(
            @RequestParam(required = false) String source_type,
            @RequestParam(required = false) String parse_status,
            @RequestParam(required = false) String keyword,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size) {
        try {
            return Result.success(adminResourceService.aiIndexTasks(source_type, parse_status, keyword, page, size));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @GetMapping("/ai-index/resources/{sourceType}/{resourceId}")
    public Result<Map<String, Object>> aiIndexResource(
            @PathVariable String sourceType,
            @PathVariable String resourceId,
            @RequestParam(defaultValue = "50") Integer chunk_limit) {
        try {
            return Result.success(adminResourceService.aiIndexResource(sourceType, resourceId, chunk_limit));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PostMapping("/ai-index/search")
    public Result<Map<String, Object>> aiIndexSearch(@RequestBody Map<String, Object> body) {
        try {
            String query = body.get("query") == null ? null : String.valueOf(body.get("query"));
            if (query == null || query.isBlank()) return Result.error(400, "检索关键词不能为空");
            String sourceType = body.get("source_type") == null ? null : String.valueOf(body.get("source_type"));
            Integer topK = null;
            Object topKObj = body.get("top_k");
            if (topKObj instanceof Number number) {
                topK = number.intValue();
            }
            return Result.success(adminResourceService.aiIndexSearch(query, sourceType, topK));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PostMapping("/ai-index/{sourceType}/{resourceId}/reparse")
    public Result<Map<String, Object>> aiIndexReparse(
            @PathVariable String sourceType,
            @PathVariable String resourceId) {
        try {
            Integer adminId = CurrentHolder.getCurrentId();
            if (adminId == null) return Result.error(401, "未登录");
            Integer id;
            try {
                id = Integer.valueOf(resourceId);
            } catch (NumberFormatException e) {
                return Result.error(400, "无效的资源 ID");
            }
            return Result.success(adminResourceService.aiIndexReparse(sourceType, id, adminId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }
}
