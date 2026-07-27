package edu.zstu.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class Ws_Project {
    private int id;
    private int user_id;
    private int task_id;
    private String project_name;
    private String project_type; //项目类型(ppt/word/h5/mixed)
    private String status; //状态(draft/editing/confirmed/exported)
    private int current_version; //当前版本号
    private String snapshots; //json字符串 版本快照列表
    private String edit_history; //json字符串 编辑历史列表
    private String permissions; //json字符串 授权用户ID列表
    private LocalDateTime created_at;
    private LocalDateTime updated_at;
}
