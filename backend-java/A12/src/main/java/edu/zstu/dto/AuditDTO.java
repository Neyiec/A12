package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 审核处理请求参数
 * 包含审核/举报的处理动作和处理意见
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class AuditDTO {
    private String audit_type;
    private String target_type;
    private int target_id;
    private String reason;
    private String action;
    private String comment;
}
