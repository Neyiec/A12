package edu.zstu.controller;

import edu.zstu.utils.Result;
import org.springframework.web.bind.annotation.*;

/**
 * AI 教学引擎 Controller
 * API-10~16：备课会话、消息、计划、执行
 */
@RestController
@RequestMapping("/api/v1/ai")
public class AIController {

    @PostMapping("/sessions")
    public Result<?> createSession() {
        return Result.success();
    }

    @PostMapping("/sessions/{id}/messages")
    public Result<?> sendMessage(@PathVariable String id) {
        return Result.success();
    }

    @GetMapping("/sessions/{id}/plan")
    public Result<?> getPlan(@PathVariable String id) {
        return Result.success();
    }

    @PostMapping("/sessions/{id}/plan-confirmations")
    public Result<?> confirmPlan(@PathVariable String id) {
        return Result.success();
    }

    @PostMapping("/sessions/{id}/runs")
    public Result<?> createRun(@PathVariable String id) {
        return Result.success();
    }

    @GetMapping("/runs/{runId}")
    public Result<?> getRun(@PathVariable String runId) {
        return Result.success();
    }

    @GetMapping("/runs/{runId}/events")
    public Result<?> getRunEvents(@PathVariable String runId) {
        return Result.success();
    }
}
