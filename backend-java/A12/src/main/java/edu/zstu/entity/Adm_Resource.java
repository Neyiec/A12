package edu.zstu.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class Adm_Resource {
    private int id;
    private String resource_type; //类型(textbook/question_bank/media/component)
    private String title;
    private String subject; //学科
    private String grade; //适用年级
    private String file_url;
    private String template_data; //json字符串 组件模板数据(仅component类型)
    private String thumbnail;
    private String description;
    private int status; //状态(1启用/0禁用)
    private int uploaded_by; //上传人ID
    private LocalDateTime created_at;
    private LocalDateTime updated_at;
}
