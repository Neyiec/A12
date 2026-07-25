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

@RestController
@RequestMapping("/api/v1/projects")
public class ProjectController {

    private final ProjectService projectService;

    public ProjectController(ProjectService projectService) {
        this.projectService = projectService;
    }

    @PostMapping
    public Result<ProjectVO> createProject(@RequestBody ProjectCreateDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(projectService.createProject(dto, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @GetMapping
    public Result<PageResult<ProjectVO>> listProjects(ProjectQueryDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(projectService.listProjects(dto, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @GetMapping("/{id}")
    public Result<ProjectVO> getProject(@PathVariable String id) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(projectService.getProject(id));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PatchMapping("/{id}")
    public Result<ProjectVO> updateProject(@PathVariable String id,
                                           @RequestBody ProjectCreateDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(projectService.updateProject(id, dto, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PostMapping("/{id}/copies")
    public Result<ProjectVO> copyProject(@PathVariable String id, @RequestBody ProjectCopyDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(projectService.copyProject(id, dto, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PostMapping("/{id}/archive")
    public Result<ProjectVO> archiveProject(@PathVariable String id) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(projectService.archiveProject(id, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PostMapping("/{id}/restore")
    public Result<ProjectVO> restoreProject(@PathVariable String id) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(projectService.restoreProject(id, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @DeleteMapping("/{id}")
    public Result<Void> deleteProject(@PathVariable String id) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            projectService.deleteProject(id, userId);
            return Result.success();
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PostMapping("/{id}/ai-revisions")
    public Result<PageVO> aiRevision(@PathVariable String id, @RequestBody AiRevisionDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(projectService.aiRevision(id, dto, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PostMapping("/{id}/components")
    public Result<PageVO> addComponent(@PathVariable String id, @RequestBody PageDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(projectService.addComponent(id, dto, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

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

    @PostMapping("/{id}/versions")
    public Result<Map<String, Object>> saveVersion(@PathVariable String id,
                                                   @RequestBody VersionCreateDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(projectService.saveVersion(id, dto, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @GetMapping("/{id}/versions")
    public Result<PageResult<VersionVO>> listVersions(@PathVariable String id, PageQuery dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(projectService.listVersions(id, dto, userId));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

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
