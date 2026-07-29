package edu.zstu.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * AI教学任务详情
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class TaskVO {
    private int id;
    private int user_id;
    private Integer conversation_id;
    private String title;
    private String subject;
    private String grade;
    private String status;
    private String uploaded_refs;
    private String plan_json;
    private String plan_confirm_status;
    private String exec_steps;
    private String reflections;
    private String python_session_id;
    private String python_outline_id;
    private String python_presentation_id;
    private String generation_mode;
    private String error_message;
    private LocalDateTime created_at;
    private LocalDateTime updated_at;
}
