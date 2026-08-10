package edu.zstu.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class Ws_Page {
    private Integer id;
    private Integer project_id;
    private Integer page_order;
    private String page_type; // page type: cover/toc/content/summary
    private String page_title;
    private String page_content; // JSON string for full page content/layout
    private String components; // JSON string for component list
    private Integer page_version;
    private String client_version;
    private Boolean autosave;
    private Boolean dirty;
    private LocalDateTime last_saved_at;
    private LocalDateTime created_at;
    private LocalDateTime updated_at;
}
