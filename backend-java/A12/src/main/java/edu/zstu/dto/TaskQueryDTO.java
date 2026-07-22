package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.NoArgsConstructor;

/**
 * AI教学任务查询参数
 * 支持按用户、学科、年级、状态和关键字筛选
 */
@EqualsAndHashCode(callSuper = true)
@Data
@NoArgsConstructor
@AllArgsConstructor
public class TaskQueryDTO extends PageQuery {
    private Integer user_id;
    private String subject;
    private String grade;
    private String status;
    private String keyword;
}
