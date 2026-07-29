package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * AI教学任务创建请求参数
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class TaskCreateDTO {
    private String title;
    private String subject;
    private String grade;
    private String status;
    private String uploaded_refs;
    private String plan_json;
    private String messages;
    private String resource_ids;
    private Boolean enable_rag;
    private Boolean enable_web;
    private Integer slide_count;
}
