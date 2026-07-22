package edu.zstu.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class Ws_Page {
    private int id;
    private int project_id;
    private int page_order;
    private String page_type; //页面类型(cover/toc/content/summary)
    private String page_title;
    private String page_content; //json字符串 页面内容(文本/布局)
    private String components; //json字符串 组件列表
    private LocalDateTime created_at;
    private LocalDateTime updated_at;
}
