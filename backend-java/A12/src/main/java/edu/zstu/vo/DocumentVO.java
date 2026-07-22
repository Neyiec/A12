package edu.zstu.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 知识文档信息
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class DocumentVO {
    private int id;
    private String source_type;
    private Integer source_id;
    private Integer user_id;
    private String title;
    private String doc_type;
    private String parse_status;
    private String chunks;
    private LocalDateTime created_at;
    private LocalDateTime updated_at;
}
