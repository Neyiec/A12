package edu.zstu.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 社区内容详情
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ContentVO {
    private int id;
    private String content_type;
    private int author_id;
    private String title;
    private String description;
    private String subject;
    private String grade;
    private String lesson_type;
    private String content_data;
    private String input_variables;
    private String example_effect;
    private int version;
    private String version_history;
    private String license;
    private String status;
    private int is_top;
    private int view_count;
    private int use_count;
    private LocalDateTime created_at;
    private LocalDateTime updated_at;
}
