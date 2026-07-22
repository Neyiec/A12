package edu.zstu.controller;

import edu.zstu.utils.Result;
import org.springframework.web.bind.annotation.*;

/**
 * 项目模块 Controller
 * API-17~31：项目的 CRUD、组件、版本管理
 */
@RestController
@RequestMapping("/api/v1/projects")
public class ProjectController {

    @PostMapping
    public Result<?> createProject() {
        return Result.success();
    }

    @GetMapping
    public Result<?> listProjects() {
        return Result.success();
    }

    @GetMapping("/{id}")
    public Result<?> getProject(@PathVariable String id) {
        return Result.success();
    }

    @PatchMapping("/{id}")
    public Result<?> updateProject(@PathVariable String id) {
        return Result.success();
    }

    @PostMapping("/{id}/copies")
    public Result<?> copyProject(@PathVariable String id) {
        return Result.success();
    }

    @PostMapping("/{id}/archive")
    public Result<?> archiveProject(@PathVariable String id) {
        return Result.success();
    }

    @PostMapping("/{id}/restore")
    public Result<?> restoreProject(@PathVariable String id) {
        return Result.success();
    }

    @DeleteMapping("/{id}")
    public Result<?> deleteProject(@PathVariable String id) {
        return Result.success();
    }

    @PostMapping("/{id}/ai-revisions")
    public Result<?> aiRevision(@PathVariable String id) {
        return Result.success();
    }

    @PostMapping("/{id}/components")
    public Result<?> addComponent(@PathVariable String id) {
        return Result.success();
    }

    @PatchMapping("/{id}/components/{componentId}")
    public Result<?> updateComponent(@PathVariable String id, @PathVariable String componentId) {
        return Result.success();
    }

    @PostMapping("/{id}/versions")
    public Result<?> saveVersion(@PathVariable String id) {
        return Result.success();
    }

    @GetMapping("/{id}/versions")
    public Result<?> listVersions(@PathVariable String id) {
        return Result.success();
    }

    @GetMapping("/{id}/versions/{versionId}/diff")
    public Result<?> versionDiff(@PathVariable String id, @PathVariable String versionId) {
        return Result.success();
    }

    @PostMapping("/{id}/versions/{versionId}/restore")
    public Result<?> restoreVersion(@PathVariable String id, @PathVariable String versionId) {
        return Result.success();
    }
}
