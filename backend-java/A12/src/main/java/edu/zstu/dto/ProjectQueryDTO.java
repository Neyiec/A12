package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.NoArgsConstructor;

/**
 * 创作项目查询参数
 * 支持按用户、项目类型、状态和关键字筛选
 */
@EqualsAndHashCode(callSuper = true)
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ProjectQueryDTO extends PageQuery {
    private Integer user_id;
    private String project_type;
    private String status;
    private String keyword;
}
