package edu.zstu.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 创作项目详情
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ProjectVO {
    private int id;
    private int user_id;
    private int task_id;
    private String project_name;
    private String project_type;
    private String status;
    private int current_version;
    private String snapshots;
    private String edit_history;
    private LocalDateTime created_at;
    private LocalDateTime updated_at;
}
