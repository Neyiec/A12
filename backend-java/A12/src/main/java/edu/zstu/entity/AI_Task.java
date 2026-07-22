package edu.zstu.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class AI_Task {
    private int id;
    private int user_id;
    private int conversation_id;
    private String title;
    private String subject; //学科
    private String grade; //年级/学段
    private String status; //状态(planning/confirmed/executing/completed/failed)
    private String uploaded_refs; //json字符串 上传参考资料列表
    private String plan_json; //json字符串 教学设计大纲(结构化)
    private String plan_confirm_status; //大纲确认状态(pending/confirmed/rejected)
    private String exec_steps; //json字符串 执行步骤列表
    private String reflections; //json字符串 反思迭代记录列表
    private LocalDateTime created_at;
    private LocalDateTime updated_at;
}
