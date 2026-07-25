package edu.zstu.controller;

import edu.zstu.dto.*;
import edu.zstu.service.ResourceService;
import edu.zstu.utils.CurrentHolder;
import edu.zstu.utils.PageResult;
import edu.zstu.utils.Result;
import edu.zstu.vo.MaterialVO;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.Map;

@RestController
@RequestMapping("/api/v1/resources")
public class ResourceController {

    private final ResourceService resourceService;

    public ResourceController(ResourceService resourceService) {
        this.resourceService = resourceService;
    }

    @PostMapping("/uploads")
    public Result<MaterialVO> uploadFile(@RequestParam("file") MultipartFile file,
                                         @RequestParam(value = "file_type", required = false) String fileType) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(resourceService.uploadFile(file, fileType, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @GetMapping
    public Result<PageResult<MaterialVO>> listResources(MaterialQueryDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(resourceService.listResources(dto, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @GetMapping("/{id}")
    public Result<MaterialVO> getResource(@PathVariable Integer id) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(resourceService.getResource(id, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PatchMapping("/{id}")
    public Result<MaterialVO> updateResource(@PathVariable Integer id, @RequestBody MaterialDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(resourceService.updateResource(id, dto, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @DeleteMapping("/{id}")
    public Result<Void> deleteResource(@PathVariable Integer id) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            resourceService.deleteResource(id, userId);
            return Result.success();
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PostMapping("/batch-actions")
    public Result<Void> batchAction(@RequestBody ResourceBatchActionDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            resourceService.batchAction(dto, userId);
            return Result.success();
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @GetMapping("/{id}/permission")
    public Result<MaterialVO> getPermission(@PathVariable Integer id) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(resourceService.getResource(id, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PutMapping("/{id}/permission")
    public Result<MaterialVO> setPermission(@PathVariable Integer id, @RequestBody MaterialDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(resourceService.setPermission(id, dto, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PostMapping("/{id}/download-url")
    public Result<Map<String, Object>> getDownloadUrl(@PathVariable Integer id) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(resourceService.getDownloadUrl(id, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }
}
