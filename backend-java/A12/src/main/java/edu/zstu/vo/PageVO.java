package edu.zstu.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 项目页面信息
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class PageVO {
    private int id;
    private int project_id;
    private int page_order;
    private String page_type;
    private String page_title;
    private String page_content;
    private String components;
    private LocalDateTime created_at;
    private LocalDateTime updated_at;
}
