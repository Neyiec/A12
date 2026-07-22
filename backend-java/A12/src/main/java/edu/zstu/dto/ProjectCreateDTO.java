package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 创作项目创建请求参数
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ProjectCreateDTO {
    private String project_name;
    private String project_type;
    private String status;
    private String snapshots;
    private String edit_history;
}
