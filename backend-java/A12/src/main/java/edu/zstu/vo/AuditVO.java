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
    // ---- 富化字段（裸 target_id 缺口补齐，见 doc/admin-dashboard-workflow.md 关键设计点 5）----
    private String content_title;   // 关联内容标题（com_content.title，内容已删除时为空）
    private Integer submitter_id;   // 提交者用户 id（com_content.author_id）
    private String submitter_name;  // 提交者显示名（sys_user.real_name，缺省回退 username）
}
