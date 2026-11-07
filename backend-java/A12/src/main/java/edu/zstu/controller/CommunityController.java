package edu.zstu.controller;

import edu.zstu.dto.*;
import edu.zstu.service.CommunityService;
import edu.zstu.utils.CurrentHolder;
import edu.zstu.utils.PageResult;
import edu.zstu.utils.Result;
import edu.zstu.vo.AuditVO;
import edu.zstu.vo.ContentVO;
import edu.zstu.vo.ProjectVO;
import edu.zstu.vo.RankItemVO;
import edu.zstu.vo.RecentViewVO;
import org.springframework.dao.DataAccessException;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * 社区模块 Controller
 * API-53~70：内容检索、收藏、投稿、举报
 *
 * <p>管理社区公开内容的检索、获取详情、收藏与取消收藏、浏览记录、内容复用（派生项目）、教师投稿管理（草稿/审核/版本）以及举报处理。</p>
 */
@RestController
@RequestMapping("/api/v1/community")
public class CommunityController {

    private final CommunityService communityService;

    public CommunityController(CommunityService communityService) {
        this.communityService = communityService;
    }

    /**
     * API-53 搜索公开社区内容（功能11 支持 sort_by/period 排序，登录可选以返回 liked 点赞态）
     */
    @GetMapping("/items")
    public Result<PageResult<ContentVO>> listItems(ContentQueryDTO dto) {
        try {
            return Result.success(communityService.listItems(dto, CurrentHolder.getCurrentId()));
        } catch (RuntimeException e) { if (e instanceof DataAccessException) throw e; return Result.error(400, e.getMessage()); }
    }

    /**
     * API-54 获取社区内容详情（登录可选以返回 liked 点赞态）
     */
    @GetMapping("/items/{id}")
    public Result<ContentVO> getItem(@PathVariable Integer id) {
        try {
            return Result.success(communityService.getItem(id, CurrentHolder.getCurrentId()));
        } catch (RuntimeException e) { if (e instanceof DataAccessException) throw e; return Result.error(400, e.getMessage()); }
    }

    /**
     * API-71 点赞社区内容（功能11，幂等；限流防刷）
     */
    @PutMapping("/items/{id}/like")
    public Result<Void> like(@PathVariable Integer id) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            communityService.like(id, userId);
            return Result.success();
        } catch (RuntimeException e) { if (e instanceof DataAccessException) throw e; return Result.error(400, e.getMessage()); }
    }

    /**
     * API-72 取消点赞（功能11，幂等）
     */
    @DeleteMapping("/items/{id}/like")
    public Result<Void> unlike(@PathVariable Integer id) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            communityService.unlike(id, userId);
            return Result.success();
        } catch (RuntimeException e) { if (e instanceof DataAccessException) throw e; return Result.error(400, e.getMessage()); }
    }

    /**
     * API-73 热门榜单（功能11，公开可读；content_type 必填，period=day/week/month 默认 week）
     */
    @GetMapping("/rankings")
    public Result<List<RankItemVO>> rankings(
            @RequestParam String content_type,
            @RequestParam(defaultValue = "week") String period,
            @RequestParam(defaultValue = "10") int limit) {
        try {
            return Result.success(communityService.listRankings(content_type, period, limit, CurrentHolder.getCurrentId()));
        } catch (RuntimeException e) { if (e instanceof DataAccessException) throw e; return Result.error(400, e.getMessage()); }
    }

    /**
     * API-55 收藏社区内容
     */
    @PutMapping("/items/{id}/favorite")
    public Result<Void> favorite(@PathVariable Integer id) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            communityService.favorite(id, userId);
            return Result.success();
        } catch (RuntimeException e) { if (e instanceof DataAccessException) throw e; return Result.error(400, e.getMessage()); }
    }

    /**
     * API-56 取消收藏
     */
    @DeleteMapping("/items/{id}/favorite")
    public Result<Void> unfavorite(@PathVariable Integer id) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            communityService.unfavorite(id, userId);
            return Result.success();
        } catch (RuntimeException e) { if (e instanceof DataAccessException) throw e; return Result.error(400, e.getMessage()); }
    }

    /**
     * API-57 记录浏览事件
     */
    @PostMapping("/items/{id}/view-events")
    public Result<Void> recordView(@PathVariable Integer id) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            communityService.recordView(id, userId);
            return Result.success();
        } catch (RuntimeException e) { if (e instanceof DataAccessException) throw e; return Result.error(400, e.getMessage()); }
    }

    /**
     * API-58 查询收藏列表
     */
    @GetMapping("/favorites")
    public Result<PageResult<ContentVO>> listFavorites(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(communityService.listFavorites(page, size, userId));
        } catch (RuntimeException e) { if (e instanceof DataAccessException) throw e; return Result.error(400, e.getMessage()); }
    }

    /**
     * API-59 查询最近浏览记录
     */
    @GetMapping("/recent-views")
    public Result<PageResult<RecentViewVO>> listRecentViews(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(communityService.listRecentViews(page, size, userId));
        } catch (RuntimeException e) { if (e instanceof DataAccessException) throw e; return Result.error(400, e.getMessage()); }
    }

    /**
     * API-60 移除浏览记录
     */
    @DeleteMapping("/recent-views/{itemId}")
    public Result<Void> removeRecentView(@PathVariable Integer itemId) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            communityService.removeRecentView(itemId, userId);
            return Result.success();
        } catch (RuntimeException e) { if (e instanceof DataAccessException) throw e; return Result.error(400, e.getMessage()); }
    }

    /**
     * API-61 复用社区内容为项目
     */
    @PostMapping("/items/{id}/reuse")
    public Result<ProjectVO> reuseItem(@PathVariable Integer id, @RequestBody InteractionDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(communityService.reuseItem(id, dto, userId));
        } catch (RuntimeException e) { if (e instanceof DataAccessException) throw e; return Result.error(400, e.getMessage()); }
    }

    /**
     * API-62 创建投稿草稿
     */
    @PostMapping("/submissions")
    public Result<ContentVO> createSubmission(@RequestBody ContentDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(communityService.createSubmission(dto, userId));
        } catch (RuntimeException e) { if (e instanceof DataAccessException) throw e; return Result.error(400, e.getMessage()); }
    }

    /**
     * API-63 分页查询投稿列表
     */
    @GetMapping("/submissions")
    public Result<PageResult<ContentVO>> listSubmissions(ContentQueryDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(communityService.listSubmissions(dto, userId));
        } catch (RuntimeException e) { if (e instanceof DataAccessException) throw e; return Result.error(400, e.getMessage()); }
    }

    /**
     * API-64 获取投稿详情
     */
    @GetMapping("/submissions/{id}")
    public Result<ContentVO> getSubmission(@PathVariable Integer id) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(communityService.getSubmission(id, userId));
        } catch (RuntimeException e) { if (e instanceof DataAccessException) throw e; return Result.error(400, e.getMessage()); }
    }

    /**
     * API-65 修改投稿
     */
    @PatchMapping("/submissions/{id}")
    public Result<ContentVO> updateSubmission(@PathVariable Integer id, @RequestBody ContentDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(communityService.updateSubmission(id, dto, userId));
        } catch (RuntimeException e) { if (e instanceof DataAccessException) throw e; return Result.error(400, e.getMessage()); }
    }

    /**
     * API-66 保存投稿版本
     */
    @PostMapping("/submissions/{id}/versions")
    public Result<Map<String, Object>> saveSubmissionVersion(
            @PathVariable Integer id,
            @RequestBody(required = false) Map<String, String> body) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            String desc = (body != null) ? body.get("description") : null;
            return Result.success(communityService.saveSubmissionVersion(id, desc, userId));
        } catch (RuntimeException e) { if (e instanceof DataAccessException) throw e; return Result.error(400, e.getMessage()); }
    }

    /**
     * API-67 提交审核
     */
    @PostMapping("/submissions/{id}/submit")
    public Result<Void> submitForReview(@PathVariable Integer id, @RequestBody ReviewSubmissionDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            communityService.submitForReview(id, dto, userId);
            return Result.success();
        } catch (RuntimeException e) { if (e instanceof DataAccessException) throw e; return Result.error(400, e.getMessage()); }
    }

    /**
     * API-68 创建举报记录
     */
    @PostMapping("/reports")
    public Result<Map<String, Object>> createReport(@RequestBody AuditDTO dto) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            int reportId = communityService.createReport(dto, userId);
            return Result.success(Map.of("report_id", reportId));
        } catch (RuntimeException e) { if (e instanceof DataAccessException) throw e; return Result.error(400, e.getMessage()); }
    }

    /**
     * API-69 分页查询举报记录
     */
    @GetMapping("/reports")
    public Result<PageResult<AuditVO>> listReports(
            @RequestParam(required = false) String status,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(communityService.listReports(status, page, size, userId));
        } catch (RuntimeException e) { if (e instanceof DataAccessException) throw e; return Result.error(400, e.getMessage()); }
    }

    /**
     * API-70 获取举报详情
     */
    @GetMapping("/reports/{id}")
    public Result<AuditVO> getReport(@PathVariable Integer id) {
        try {
            Integer userId = CurrentHolder.getCurrentId();
            if (userId == null) return Result.error(401, "未登录");
            return Result.success(communityService.getReport(id, userId));
        } catch (RuntimeException e) { if (e instanceof DataAccessException) throw e; return Result.error(400, e.getMessage()); }
    }
}
