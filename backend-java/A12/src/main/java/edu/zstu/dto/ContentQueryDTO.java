package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.NoArgsConstructor;

/**
 * 社区内容搜索查询参数
 * 支持按内容类型、学科、年级、状态和关键字筛选
 */
@EqualsAndHashCode(callSuper = true)
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ContentQueryDTO extends PageQuery {
    private String content_type;
    private String subject;
    private String grade;
    private String status;
    private String keyword;
}
