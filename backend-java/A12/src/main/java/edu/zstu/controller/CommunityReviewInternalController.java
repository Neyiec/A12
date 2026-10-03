package edu.zstu.controller;

import edu.zstu.dto.AiReviewResultDTO;
import edu.zstu.service.AdminModerationService;
import edu.zstu.utils.Result;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/** 仅供持共享密钥的 Python 消费者读取待审课件及回写 AI 初审结果。 */
@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/internal/community-review")
public class CommunityReviewInternalController {
    private final AdminModerationService moderation;

    @GetMapping("/{auditId}")
    public Result<Map<String, Object>> payload(@PathVariable Integer auditId) {
        try { return Result.success(moderation.getAiReviewPayload(auditId)); }
        catch (IllegalStateException e) { return Result.error(409, e.getMessage()); }
    }

    @PostMapping("/{auditId}/result")
    public Result<Void> result(@PathVariable Integer auditId, @RequestBody AiReviewResultDTO result) {
        try { moderation.acceptAiReview(auditId, result); return Result.success(); }
        catch (IllegalStateException e) { return Result.error(409, e.getMessage()); }
    }
}
