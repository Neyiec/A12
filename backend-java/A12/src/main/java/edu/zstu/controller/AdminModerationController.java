package edu.zstu.controller;

import edu.zstu.utils.Result;
import org.springframework.web.bind.annotation.*;

/**
 * 后台 — 内容审核与举报处理 Controller
 * API-86~93：审核任务、内容状态、举报处理
 */
@RestController
@RequestMapping("/api/v1/admin")
public class AdminModerationController {

    @GetMapping("/moderation/tasks")
    public Result<?> listModerationTasks() {
        return Result.success();
    }

    @GetMapping("/moderation/tasks/{id}")
    public Result<?> getModerationTask(@PathVariable String id) {
        return Result.success();
    }

    @PostMapping("/moderation/tasks/{id}/decisions")
    public Result<?> makeDecision(@PathVariable String id) {
        return Result.success();
    }

    @PutMapping("/community-items/{id}/status")
    public Result<?> updateItemStatus(@PathVariable String id) {
        return Result.success();
    }

    @PutMapping("/community-items/{id}/recommendation")
    public Result<?> updateRecommendation(@PathVariable String id) {
        return Result.success();
    }

    @GetMapping("/reports")
    public Result<?> listReports() {
        return Result.success();
    }

    @GetMapping("/reports/{id}")
    public Result<?> getReport(@PathVariable String id) {
        return Result.success();
    }

    @PostMapping("/reports/{id}/resolution")
    public Result<?> resolveReport(@PathVariable String id) {
        return Result.success();
    }
}
