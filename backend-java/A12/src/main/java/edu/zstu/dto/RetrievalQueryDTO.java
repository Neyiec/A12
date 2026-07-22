package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.NoArgsConstructor;

/**
 * 知识库检索/生成记录查询参数
 * 支持按用户、记录类型和关联任务筛选
 */
@EqualsAndHashCode(callSuper = true)
@Data
@NoArgsConstructor
@AllArgsConstructor
public class RetrievalQueryDTO extends PageQuery {
    private Integer user_id;
    private String type;
    private Integer task_id;
}
