package edu.zstu.controller;

import edu.zstu.dto.AuditDTO;
import edu.zstu.dto.RecommendationDTO;
import edu.zstu.utils.Result;
import edu.zstu.vo.AuditVO;
import edu.zstu.vo.ContentVO;
import org.springframework.web.bind.annotation.*;

/**
 * 后台 — 内容审核与举报处理 Controller
 * API-86~93：审核任务、内容状态、举报处理
 *
 * <p>管理员对社区投稿进行审核（查看待审内容、提交审核决定）、管理社区内容状态
 * （上架/下架/推荐/置顶）、以及处理教师举报。</p>
 */
@RestController
@RequestMapping("/api/v1/admin")
public class AdminModerationController {

    /**
     * API-86 分页查询审核任务
     *
     * <p>按状态、对象类型和审核员查询审核任务。</p>
     *
     * @param status      任务状态（选填）：pending / processing / completed
     * @param target_type 目标类型（选填）
     * @param handler_id  审核员ID（选填）
     * @param page        页码（选填，默认1）
     * @param size        每页条数（选填，默认10）
     * @return 分页审核任务列表 {@link AuditVO}
     */
    @GetMapping("/moderation/tasks")
    public Result<?> listModerationTasks(@RequestParam(required = false) String status,
                                         @RequestParam(required = false) String target_type,
                                         @RequestParam(required = false) Integer handler_id,
                                         @RequestParam(defaultValue = "1") int page,
                                         @RequestParam(defaultValue = "10") int size) {
        return Result.success();
    }

    /**
     * API-87 获取审核任务详情
     *
     * <p>获取待审内容、投稿人、来源版本、授权信息和自动检测结果。</p>
     *
     * @param id 审核任务ID（路径参数）
     * @return 审核任务详情 {@link AuditVO}
     */
    @GetMapping("/moderation/tasks/{id}")
    public Result<AuditVO> getModerationTask(@PathVariable String id) {
        return Result.success();
    }

    /**
     * API-88 提交审核决定
     *
     * <p>提交通过、驳回或退回修改决定及原因。</p>
     *
     * @param id  审核任务ID（路径参数）
     * @param dto 审核决定参数（action 必填）{@link AuditDTO}
     * @return 操作结果（无数据体）
     */
    @PostMapping("/moderation/tasks/{id}/decisions")
    public Result<Void> makeDecision(@PathVariable String id,
                                     @RequestBody AuditDTO dto) {
        return Result.success();
    }

    /**
     * API-89 更新社区内容状态
     *
     * <p>执行上架、下架或停用并触发统一内容状态事件。</p>
     *
     * @param id     社区内容ID（路径参数）
     * @param status 状态：published / unpublished / disabled（必填）
     * @return 更新后的社区内容 {@link ContentVO}
     */
    @PutMapping("/community-items/{id}/status")
    public Result<ContentVO> updateItemStatus(@PathVariable String id,
                                              @RequestParam String status) {
        return Result.success();
    }

    /**
     * API-90 设置推荐/置顶
     *
     * <p>设置、取消推荐或置顶，并记录生效时间。</p>
     *
     * @param id         社区内容ID（路径参数）
     * @param is_top     0=取消推荐, 1=推荐, 2=置顶（必填）
     * @param expires_at 推荐/置顶到期时间（选填）
     * @return 更新后的社区内容 {@link ContentVO}
     */
    @PutMapping("/community-items/{id}/recommendation")
    public Result<ContentVO> updateRecommendation(@PathVariable String id, @RequestBody RecommendationDTO dto) {
        return Result.success();
    }

    /**
     * API-91 分页查询举报记录
     *
     * <p>分页查询待处理、处理中和已完成举报。</p>
     *
     * @param status 状态（选填）：pending / processing / resolved
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
     * API-92 获取举报详情
     *
     * <p>查看举报对象、证据、历史审核及关联治理记录。</p>
     *
     * @param id 举报ID（路径参数）
     * @return 举报详情 {@link AuditVO}
     */
    @GetMapping("/reports/{id}")
    public Result<AuditVO> getReport(@PathVariable String id) {
        return Result.success();
    }

    /**
     * API-93 处理举报
     *
     * <p>提交举报处理结论并联动内容治理。</p>
     *
     * @param id  举报ID（路径参数）
     * @param dto 处理参数（action 必填）{@link AuditDTO}
     * @return 操作结果（无数据体）
     */
    @PostMapping("/reports/{id}/resolution")
    public Result<Void> resolveReport(@PathVariable String id,
                                      @RequestBody AuditDTO dto) {
        return Result.success();
    }
}
