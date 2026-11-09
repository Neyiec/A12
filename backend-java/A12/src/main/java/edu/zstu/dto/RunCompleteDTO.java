package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * AI 执行任务完成回写请求参数 (API-17)
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class RunCompleteDTO {
    private String presentation_id;
}
