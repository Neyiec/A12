package edu.zstu.controller;

import edu.zstu.dto.AuditDTO;
import edu.zstu.dto.ContentDTO;
import edu.zstu.dto.ContentQueryDTO;
import edu.zstu.dto.InteractionDTO;
import edu.zstu.dto.ReviewSubmissionDTO;
import edu.zstu.utils.Result;
import edu.zstu.vo.AuditVO;
import edu.zstu.vo.ContentVO;
import edu.zstu.vo.ProjectVO;
import org.springframework.web.bind.annotation.*;

/**
 * 社区模块 Controller
 * API-53~70：内容检索、收藏、投稿、举报
 *
 * <p>管理社区内容的公开检索、收藏、浏览记录、内容复用、教师投稿以及举报处理。
 * 部分功能（投稿审核、举报）首期MVP由功能开关控制。</p>
 */
@RestController
@RequestMapping("/api/v1/community")
public class CommunityController {

    /**
     * API-53 检索社区内容
     *
     * <p>检索公开可用的 Skill 和教学案例。</p>
     *
     * @param dto 查询参数（content_type、subject、grade、keyword、page、size 均为选填）
     * @return 分页社区内容列表
     */
    @GetMapping("/items")
    public Result<?> listItems(ContentQueryDTO dto) {
        return Result.success();
    }

    /**
     * API-54 获取社区内容详情
     *
     * <p>获取用途、变量、示例、作者、版本和授权信息。不在GET请求中写入浏览记录。</p>
     *
     * @param id 内容ID（路径参数）
     * @return 社区内容详情 {@link ContentVO}
     */
    @GetMapping("/items/{id}")
    public Result<ContentVO> getItem(@PathVariable String id) {
        return Result.success();
    }

    /**
     * API-55 收藏
     *
     * <p>收藏指定社区内容。</p>
     *
     * @param id 内容ID（路径参数）
     * @return 操作结果（无数据体）
     */
    @PutMapping("/items/{id}/favorite")
    public Result<Void> favorite(@PathVariable String id) {
        return Result.success();
    }

    /**
     * API-56 取消收藏
     *
     * <p>取消收藏指定社区内容。</p>
     *
     * @param id 内容ID（路径参数）
     * @return 操作结果（无数据体）
     */
    @DeleteMapping("/items/{id}/favorite")
    public Result<Void> unfavorite(@PathVariable String id) {
        return Result.success();
    }

    /**
     * API-57 记录浏览事件
     *
     * <p>记录当前用户最近浏览，按用户和内容幂等更新最近浏览时间。</p>
     *
     * @param id 内容ID（路径参数）
     * @return 操作结果（无数据体）
     */
    @PostMapping("/items/{id}/view-events")
    public Result<Void> recordView(@PathVariable String id) {
        return Result.success();
    }

    /**
     * API-58 查询收藏列表
     *
     * <p>分页查询当前用户收藏的公开可用内容及下架状态提示。</p>
     *
     * @param page 页码（选填，默认1）
     * @param size 每页条数（选填，默认10）
     * @return 分页收藏内容列表
     */
    @GetMapping("/favorites")
    public Result<?> listFavorites(@RequestParam(defaultValue = "1") int page,
                                   @RequestParam(defaultValue = "10") int size) {
        return Result.success();
    }

    /**
     * API-59 查询最近浏览记录
     *
     * <p>分页查询当前用户最近浏览记录。</p>
     *
     * @param page 页码（选填，默认1）
     * @param size 每页条数（选填，默认10）
     * @return 分页浏览记录
     */
    @GetMapping("/recent-views")
    public Result<?> listRecentViews(@RequestParam(defaultValue = "1") int page,
                                     @RequestParam(defaultValue = "10") int size) {
        return Result.success();
    }

    /**
     * API-60 移除浏览记录
     *
     * <p>移除指定最近浏览记录。</p>
     *
     * @param itemId 内容ID（路径参数）
     * @return 操作结果（无数据体）
     */
    @DeleteMapping("/recent-views/{itemId}")
    public Result<Void> removeRecentView(@PathVariable String itemId) {
        return Result.success();
    }

    /**
     * API-61 复用社区内容
     *
     * <p>校验内容状态、版本和授权，复制到个人空间并返回派生项目。</p>
     *
     * @param id        内容ID（路径参数）
     * @param dto       复用参数 {@link InteractionDTO}
     * @return 派生项目信息 {@link ProjectVO}
     */
    @PostMapping("/items/{id}/reuse")
    public Result<ProjectVO> reuseItem(@PathVariable String id,
                                       @RequestBody InteractionDTO dto) {
        return Result.success();
    }

    /**
     * API-62 创建投稿草稿
     *
     * <p>创建当前教师的 Skill 或案例投稿草稿。</p>
     *
     * @param dto 投稿草稿参数（content_type、title、license 必填）{@link ContentDTO}
     * @return 投稿草稿信息 {@link ContentVO}
     */
    @PostMapping("/submissions")
    public Result<ContentVO> createSubmission(@RequestBody ContentDTO dto) {
        return Result.success();
    }

    /**
     * API-63 分页查询投稿列表
     *
     * <p>分页查询当前教师的投稿及审核状态。</p>
     *
     * @param dto 查询参数（status、page、size 均为选填）
     * @return 分页投稿列表
     */
    @GetMapping("/submissions")
    public Result<?> listSubmissions(ContentQueryDTO dto) {
        return Result.success();
    }

    /**
     * API-64 获取投稿详情
     *
     * <p>获取投稿草稿、版本、审核状态和退回意见。</p>
     *
     * @param id 投稿ID（路径参数）
     * @return 投稿详情 {@link ContentVO}
     */
    @GetMapping("/submissions/{id}")
    public Result<ContentVO> getSubmission(@PathVariable String id) {
        return Result.success();
    }

    /**
     * API-65 修改投稿
     *
     * <p>修改处于草稿或退回修改状态的投稿内容。</p>
     *
     * @param id  投稿ID（路径参数）
     * @param dto 更新参数（仅传递需要更新的字段）{@link ContentDTO}
     * @return 更新后的投稿 {@link ContentVO}
     */
    @PatchMapping("/submissions/{id}")
    public Result<ContentVO> updateSubmission(@PathVariable String id,
                                              @RequestBody ContentDTO dto) {
        return Result.success();
    }

    /**
     * API-66 保存投稿版本
     *
     * <p>为投稿保存不可变版本并返回版本编号。</p>
     *
     * @param id          投稿ID（路径参数）
     * @param description 版本说明（选填）
     * @return 版本ID和版本号
     */
    @PostMapping("/submissions/{id}/versions")
    public Result<?> saveSubmissionVersion(@PathVariable String id,
                                           @RequestParam(required = false) String description) {
        return Result.success();
    }

    /**
     * API-67 提交审核
     *
     * <p>校验来源和授权说明后提交审核并触发审核任务。首期MVP由功能开关禁用。</p>
     *
     * @param id                 投稿ID（路径参数）
     * @param dto                提交审核请求参数 {@link ReviewSubmissionDTO}
     * @return 操作结果（无数据体）
     */
    @PostMapping("/submissions/{id}/submit")
    public Result<Void> submitForReview(@PathVariable String id,
                                        @RequestBody ReviewSubmissionDTO dto) {
        return Result.success();
    }

    /**
     * API-68 创建举报
     *
     * <p>校验举报对象后创建举报记录并返回编号。首期MVP由功能开关禁用。</p>
     *
     * @param dto 举报参数（target_type、target_id、reason 必填）{@link AuditDTO}
     * @return 举报记录编号
     */
    @PostMapping("/reports")
    public Result<?> createReport(@RequestBody AuditDTO dto) {
        return Result.success();
    }

    /**
     * API-69 分页查询举报记录
     *
     * <p>分页查询当前教师提交的举报及处理状态。</p>
     *
     * @param status 状态（选填）
     * @param page   页码（选填，默认1）
     * @param size   每页条数（选填，默认10）
     * @return 分页举报记录 {@link AuditVO}
     */
    @GetMapping("/reports")
    public Result<?> listReports(@RequestParam(required = false) String status,
                                 @RequestParam(defaultValue = "1") int page,
                                 @RequestParam(defaultValue = "10") int size) {
        return Result.success();
    }

    /**
     * API-70 获取举报详情
     *
     * <p>获取本人举报的受理状态及允许公开的处理结果。</p>
     *
     * @param id 举报ID（路径参数）
     * @return 举报详情 {@link AuditVO}
     */
    @GetMapping("/reports/{id}")
    public Result<AuditVO> getReport(@PathVariable String id) {
        return Result.success();
    }
}
