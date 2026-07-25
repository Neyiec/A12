package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 投稿提交审核请求参数 (API-67)
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ReviewSubmissionDTO {
    private String source_declaration;
    private String notes;
}
