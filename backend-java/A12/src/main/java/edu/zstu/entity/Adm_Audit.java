package edu.zstu.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class Adm_Audit {
    private int id;
    private String audit_type; //类型(audit/report)
    private String target_type; //目标类型(skill/case)
    private int target_id;
    private Integer reporter_id; //举报人ID(审核时为空)
    private String reason; //举报原因/审核备注
    private int handler_id; //处理人ID
    private String action; //处理动作(approve/reject/offline/ignore)
    private String comment; //处理意见
    private String status; //状态(pending/processed/ignored)
    private String ai_domain; // arts/science/engineering
    private String ai_verdict; // pass/review/fail/error
    private Integer ai_score;
    private String ai_report; // JSON 审核依据
    private String ai_model;
    private LocalDateTime ai_reviewed_at;
    private LocalDateTime created_at;
    private LocalDateTime processed_at;
}
