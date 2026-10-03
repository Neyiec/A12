package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 社区内容发布/编辑请求参数
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ContentDTO {
    private String content_type;
    private String title;
    private String description;
    private String subject;
    private String grade;
    private String lesson_type;
    private String keywords;
    private String content_data;
    private String input_variables;
    private String example_effect;
    private String license;
}
