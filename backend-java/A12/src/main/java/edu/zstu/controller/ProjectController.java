package edu.zstu.controller;

import edu.zstu.dto.*;
import edu.zstu.service.ProjectService;
import edu.zstu.utils.CurrentHolder;
import edu.zstu.utils.PageResult;
import edu.zstu.utils.Result;
import edu.zstu.vo.PageVO;
import edu.zstu.vo.ProjectVO;
import edu.zstu.vo.VersionVO;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * 项目模块 Controller
 * API-17~31：项目管理、组件、版本
 *
 * <p>负责个人教学项目的创建、查询、编辑、复制、归档、删除，页面与组件管理（插入、修改、AI修改），以及版本保存、差异对比、版本回滚等操作。
 */
@RestController
@RequestMapping("/api/v1/projects")
public class ProjectController {

    private final ProjectService projectService;

    public ProjectController(ProjectService projectService) {
        this.projectService = projectService;
    }

    /**
     * API-17 创建教学项目
     */
    @PostMapping
    public Result<ProjectVO> createProject(@RequestBody ProjectCreateDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(projectService.createProject(dto, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-18 分页查询项目
     */
    @GetMapping
    public Result<PageResult<ProjectVO>> listProjects(ProjectQueryDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(projectService.listProjects(dto, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-19 获取项目内容
     */
    @GetMapping("/{id}")
    public Result<ProjectVO> getProject(@PathVariable String id) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(projectService.getProject(id, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-20 修改项目元数据
     */
    @PatchMapping("/{id}")
    public Result<ProjectVO> updateProject(@PathVariable String id,
                                           @RequestBody ProjectCreateDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(projectService.updateProject(id, dto, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-32 添加项目授权用户
     */
    @PostMapping("/{id}/permissions")
    public Result<ProjectVO> addPermission(@PathVariable String id,
                                           @RequestBody ProjectPermissionDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(projectService.addPermission(id, dto, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-21 复制项目
     */
    @PostMapping("/{id}/copies")
    public Result<ProjectVO> copyProject(@PathVariable String id, @RequestBody ProjectCopyDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(projectService.copyProject(id, dto, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-22 归档项目
     */
    @PostMapping("/{id}/archive")
    public Result<ProjectVO> archiveProject(@PathVariable String id) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(projectService.archiveProject(id, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-23 恢复项目
     */
    @PostMapping("/{id}/restore")
    public Result<ProjectVO> restoreProject(@PathVariable String id) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(projectService.restoreProject(id, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-24 删除项目
     */
    @DeleteMapping("/{id}")
    public Result<Void> deleteProject(@PathVariable String id) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            projectService.deleteProject(id, userId);
            return Result.success();
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-25 AI修改页面/组件
     */
    @PostMapping("/{id}/ai-revisions")
    public Result<PageVO> aiRevision(@PathVariable String id, @RequestBody AiRevisionDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(projectService.aiRevision(id, dto, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-26 插入页面组件
     */
    @PostMapping("/{id}/components")
    public Result<PageVO> addComponent(@PathVariable String id, @RequestBody PageDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(projectService.addComponent(id, dto, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-27 修改组件内容
     */
    @PatchMapping("/{id}/components/{componentId}")
    public Result<PageVO> updateComponent(@PathVariable String id,
                                          @PathVariable String componentId,
                                          @RequestBody PageDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(projectService.updateComponent(id, componentId, dto, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-28 保存项目版本
     */
    @PostMapping("/{id}/versions")
    public Result<Map<String, Object>> saveVersion(@PathVariable String id,
                                                   @RequestBody VersionCreateDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(projectService.saveVersion(id, dto, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-29 分页查询版本列表
     */
    @GetMapping("/{id}/versions")
    public Result<PageResult<VersionVO>> listVersions(@PathVariable String id, PageQuery dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(projectService.listVersions(id, dto, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-30 版本差异比较
     */
    @GetMapping("/{id}/versions/{versionId}/diff")
    public Result<Map<String, Object>> versionDiff(@PathVariable String id,
                                                   @PathVariable String versionId,
                                                   @RequestParam(required = false) Integer compareVersionId) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(projectService.versionDiff(id, versionId, compareVersionId, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    /**
     * API-31 恢复历史版本
     */
    @PostMapping("/{id}/versions/{versionId}/restore")
    public Result<ProjectVO> restoreVersion(@PathVariable String id,
                                            @PathVariable String versionId) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(projectService.restoreVersion(id, versionId, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }
}