package edu.zstu.controller;

import edu.zstu.dto.AuditDTO;
import edu.zstu.dto.RecommendationDTO;
import edu.zstu.service.AdminModerationService;
import edu.zstu.utils.CurrentHolder;
import edu.zstu.utils.PageResult;
import edu.zstu.utils.Result;
import edu.zstu.vo.AuditVO;
import edu.zstu.vo.ContentVO;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/v1/admin")
public class AdminModerationController {

    private final AdminModerationService adminModerationService;

    public AdminModerationController(AdminModerationService adminModerationService) {
        this.adminModerationService = adminModerationService;
    }

    @GetMapping("/moderation/tasks")
    public Result<PageResult<AuditVO>> listModerationTasks(
            @RequestParam(required = false) String status,
            @RequestParam(required = false) String target_type,
            @RequestParam(required = false) Integer handler_id,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size) {
        try {
            return Result.success(adminModerationService.listModerationTasks(status, target_type, handler_id, page, size));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @GetMapping("/moderation/tasks/{id}")
    public Result<AuditVO> getModerationTask(@PathVariable Integer id) {
        try {
            return Result.success(adminModerationService.getModerationTask(id));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PostMapping("/moderation/tasks/{id}/decisions")
    public Result<Void> makeDecision(@PathVariable Integer id, @RequestBody AuditDTO dto) {
        try {
            Integer adminId = CurrentHolder.getCurrentId();
            if (adminId == null) return Result.error(401, "未登录");
            adminModerationService.makeDecision(id, dto, adminId);
            return Result.success();
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PutMapping("/community-items/{id}/status")
    public Result<ContentVO> updateItemStatus(@PathVariable Integer id, @RequestBody Map<String, String> body) {
        try {
            String status = body != null ? body.get("status") : null;
            if (status == null || status.isBlank()) return Result.error(400, "缺少 status 字段");
            return Result.success(adminModerationService.updateItemStatus(id, status));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PutMapping("/community-items/{id}/recommendation")
    public Result<ContentVO> updateRecommendation(@PathVariable Integer id, @RequestBody RecommendationDTO dto) {
        try {
            return Result.success(adminModerationService.updateRecommendation(id, dto));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @GetMapping("/reports")
    public Result<PageResult<AuditVO>> listReports(
            @RequestParam(required = false) String status,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size) {
        try {
            return Result.success(adminModerationService.listReports(status, page, size));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @GetMapping("/reports/{id}")
    public Result<AuditVO> getReport(@PathVariable Integer id) {
        try {
            return Result.success(adminModerationService.getReport(id));
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }

    @PostMapping("/reports/{id}/resolution")
    public Result<Void> resolveReport(@PathVariable Integer id, @RequestBody AuditDTO dto) {
        try {
            Integer adminId = CurrentHolder.getCurrentId();
            if (adminId == null) return Result.error(401, "未登录");
            adminModerationService.resolveReport(id, dto, adminId);
            return Result.success();
        } catch (RuntimeException e) { return Result.error(400, e.getMessage()); }
    }
}