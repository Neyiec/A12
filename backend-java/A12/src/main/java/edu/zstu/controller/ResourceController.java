package edu.zstu.controller;

import edu.zstu.dto.MaterialDTO;
import edu.zstu.dto.MaterialQueryDTO;
import edu.zstu.dto.ResourceBatchActionDTO;
import edu.zstu.dto.ResourceTaxonomyDTO;
import edu.zstu.dto.ResourceUploadConfirmDTO;
import edu.zstu.dto.UploadTokenDTO;
import edu.zstu.service.ResourceService;
import edu.zstu.utils.CurrentHolder;
import edu.zstu.utils.PageResult;
import edu.zstu.utils.Result;
import edu.zstu.vo.MaterialVO;
import edu.zstu.vo.UploadTokenVO;
import org.springframework.web.bind.annotation.*;
import java.util.Map;

/**
 * 个人资源库模块 Controller
 * API-32~42：上传、检索、编辑、权限
 *
 * <p>负责个人素材资源的管理，包括获取上传签名 URL、确认上传并入库、分页检索、元数据编辑、软删除、批量操作、权限设置以及获取下载 URL。</p>
 */
@RestController
@RequestMapping("/api/v1/resources")
public class ResourceController {

    private final ResourceService resourceService;

    public ResourceController(ResourceService resourceService) {
        this.resourceService = resourceService;
    }

    /**
     * API-32 获取OSS上传签名URL
     */
    @PostMapping("/upload-tokens")
    public Result<UploadTokenVO> createUploadToken(@RequestBody UploadTokenDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(resourceService.createUploadToken(dto, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-33 确认上传并入库
     */
    @PostMapping("/uploaded-files")
    public Result<MaterialVO> confirmUpload(@RequestBody ResourceUploadConfirmDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(resourceService.confirmUpload(dto, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-34 分页检索个人资源
     */
    @GetMapping
    public Result<PageResult<MaterialVO>> listResources(MaterialQueryDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(resourceService.listResources(dto, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @GetMapping("/tags")
    public Result<java.util.List<Map<String, Object>>> listTags() {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "unauthorized");
            return Result.success(resourceService.listTags(userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @GetMapping("/categories")
    public Result<java.util.List<Map<String, Object>>> listCategories() {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "unauthorized");
            return Result.success(resourceService.listCategories(userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }


    @PostMapping("/tags")
    public Result<Map<String, Object>> createTag(@RequestBody ResourceTaxonomyDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "unauthorized");
            return Result.success(resourceService.createTag(dto, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @DeleteMapping("/tags/{dictId}")
    public Result<Void> deleteTag(@PathVariable Integer dictId) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "unauthorized");
            resourceService.deleteTag(dictId, userId);
            return Result.success();
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PatchMapping("/tags/{dictId}")
    public Result<Map<String, Object>> updateTag(@PathVariable Integer dictId, @RequestBody ResourceTaxonomyDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "unauthorized");
            return Result.success(resourceService.updateTag(dictId, dto, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PostMapping("/categories")
    public Result<Map<String, Object>> createCategory(@RequestBody ResourceTaxonomyDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "unauthorized");
            return Result.success(resourceService.createCategory(dto, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @DeleteMapping("/categories/{dictId}")
    public Result<Void> deleteCategory(@PathVariable Integer dictId) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "unauthorized");
            resourceService.deleteCategory(dictId, userId);
            return Result.success();
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PatchMapping("/categories/{dictId}")
    public Result<Map<String, Object>> updateCategory(@PathVariable Integer dictId, @RequestBody ResourceTaxonomyDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "unauthorized");
            return Result.success(resourceService.updateCategory(dictId, dto, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }


    /**
     * API-35 获取资源详情
     */
    @GetMapping("/{id}")
    public Result<MaterialVO> getResource(@PathVariable Integer id) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(resourceService.getResource(id, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-36 编辑资源元数据
     */
    @PatchMapping("/{id}")
    public Result<MaterialVO> updateResource(@PathVariable Integer id, @RequestBody MaterialDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(resourceService.updateResource(id, dto, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-37 删除资源
     */
    @DeleteMapping("/{id}")
    public Result<Void> deleteResource(@PathVariable Integer id) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            resourceService.deleteResource(id, userId);
            return Result.success();
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-38 批量操作资源
     */
    @PostMapping("/batch-actions")
    public Result<Void> batchAction(@RequestBody ResourceBatchActionDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            resourceService.batchAction(dto, userId);
            return Result.success();
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-39 获取资源权限
     */
    @GetMapping("/{id}/permission")
    public Result<MaterialVO> getPermission(@PathVariable Integer id) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(resourceService.getResource(id, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-40 设置资源权限
     */
    @PutMapping("/{id}/permission")
    public Result<MaterialVO> setPermission(@PathVariable Integer id, @RequestBody MaterialDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(resourceService.setPermission(id, dto, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-42 获取下载URL
     */
    @PostMapping("/{id}/download-url")
    public Result<Map<String, Object>> getDownloadUrl(@PathVariable Integer id) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(resourceService.getDownloadUrl(id, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }
}
