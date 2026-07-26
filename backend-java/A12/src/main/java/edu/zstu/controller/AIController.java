package edu.zstu.controller;

import edu.zstu.dto.ConversationDTO;
import edu.zstu.dto.PlanConfirmationDTO;
import edu.zstu.dto.TaskCreateDTO;
import edu.zstu.utils.Result;
import edu.zstu.vo.ConversationVO;
import edu.zstu.vo.TaskVO;
import org.springframework.web.bind.annotation.*;

/**
 * AI 教学引擎 Controller
 * API-10~16：备课会话、消息、计划、执行
 *
 * <p>负责AI备课会话的创建、消息交互、教学大纲确认、任务执行以及实时事件订阅。</p>
 */
@RestController
@RequestMapping("/api/v1/ai")
public class AIController {

    /**
     * API-10 创建备课会话
     *
     * <p>创建备课会话并提交文字、语音、参考资料、Skill和课程信息。</p>
     *
     * @param dto 会话创建参数（title、subject、grade 必填）
     * @return 新创建的AI教学任务信息 {@link TaskVO}
     */
    @PostMapping("/sessions")
    public Result<TaskVO> createSession(@RequestBody TaskCreateDTO dto) {
        return Result.success();
    }

    /**
     * API-11 发送会话消息
     *
     * <p>在已有备课会话中补充需求、回答澄清问题或提交反馈。</p>
     *
     * @param id  会话ID（路径参数）
     * @param dto 消息请求参数 {@link ConversationDTO}（messages 必填）
     * @return 更新后的会话信息 {@link ConversationVO}
     */
    @PostMapping("/sessions/{id}/messages")
    public Result<ConversationVO> sendMessage(@PathVariable String id,
                                              @RequestBody ConversationDTO dto) {
        return Result.success();
    }

    /**
     * API-12 获取教学设计大纲
     *
     * <p>获取当前会话的教学设计大纲及其版本号。</p>
     *
     * @param id 会话ID（路径参数）
     * @return 当前教学任务信息（含 plan_json、plan_confirm_status）{@link TaskVO}
     */
    @GetMapping("/sessions/{id}/plan")
    public Result<TaskVO> getPlan(@PathVariable String id) {
        return Result.success();
    }

    /**
     * API-13 确认/退回/补充教学设计大纲
     *
     * <p>教师确认大纲、退回修改或补充需求。需携带大纲版本号防止并发冲突。</p>
     *
     * @param id           会话ID（路径参数）
     * @param dto          操作请求参数 {@link PlanConfirmationDTO}
     * @return 操作结果（无数据体）
     */
    @PostMapping("/sessions/{id}/plan-confirmations")
    public Result<Void> confirmPlan(@PathVariable String id,
                                    @RequestBody PlanConfirmationDTO dto) {
        return Result.success();
    }

    /**
     * API-14 创建执行任务
     *
     * <p>依据已确认的教学计划创建执行任务。</p>
     *
     * @param id 会话ID（路径参数）
     * @return 创建的执行任务 {@link TaskVO}（status 转为 running）
     */
    @PostMapping("/sessions/{id}/runs")
    public Result<TaskVO> createRun(@PathVariable String id) {
        return Result.success();
    }

    /**
     * API-15 查询执行任务状态
     *
     * <p>查询AI生成、反思及失败状态。</p>
     *
     * @param runId 执行任务ID（路径参数）
     * @return 任务当前状态 {@link TaskVO}
     */
    @GetMapping("/runs/{runId}")
    public Result<TaskVO> getRun(@PathVariable String runId) {
        return Result.success();
    }

    /**
     * API-16 获取执行事件流（SSE）
     *
     * <p>通过 Server-Sent Events 接收阶段、进度和预览更新，支持断线续传。
     * 返回值类型为 text/event-stream。</p>
     *
     * @param runId       执行任务ID（路径参数）
     * @param lastEventId 断线续传时携带最后收到的 eventId（选填）
     * @return SSE 事件流，包含阶段进度和预览数据
     */
    @GetMapping("/runs/{runId}/events")
    public Result<Void> getRunEvents(@PathVariable String runId,
                                     @RequestParam(required = false) String lastEventId) {
        return Result.success();
    }
}
