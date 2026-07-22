package edu.zstu.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 审核记录信息
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class AuditVO {
    private int id;
    private String audit_type;
    private String target_type;
    private int target_id;
    private Integer reporter_id;
    private String reason;
    private Integer handler_id;
    private String action;
    private String comment;
    private String status;
    private LocalDateTime created_at;
    private LocalDateTime processed_at;
}
