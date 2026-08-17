package edu.zstu.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * Project page information.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class PageVO {
    private Integer id;
    private Integer project_id;
    private Integer page_order;
    private String page_type;
    private String page_title;
    private String page_content;
    private String components;
    private Integer page_version;
    private String client_version;
    private Boolean autosave;
    private Boolean dirty;
    private LocalDateTime last_saved_at;
    private LocalDateTime created_at;
    private LocalDateTime updated_at;
}
