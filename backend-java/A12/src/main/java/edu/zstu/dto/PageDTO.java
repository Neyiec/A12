package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 项目页面操作请求参数（创建/更新页面）
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class PageDTO {
    private Integer page_id;
    private Integer page_order;
    private String page_type;
    private String page_title;
    private String page_content;
    private String components;
    private Integer expected_page_version;
    private String client_version;
    private Boolean autosave;
    private Boolean dirty;
}
