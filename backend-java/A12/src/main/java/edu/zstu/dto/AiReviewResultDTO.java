package edu.zstu.dto;

import java.util.List;
import java.util.Map;

/** Python 学科审核 Agent 的结构化结果；自动放行规则始终由 Java 业务端决定。 */
public record AiReviewResultDTO(
        Integer content_version,
        String domain,
        String verdict,
        Integer score,
        String summary,
        String model,
        List<Map<String, Object>> checks,
        List<Map<String, Object>> findings
) {}
