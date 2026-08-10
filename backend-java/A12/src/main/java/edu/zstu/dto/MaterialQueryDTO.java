package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 素材资源查询参数（API-34）
 * 支持按用户、文件类型、关键字和时间范围筛选
 */
@EqualsAndHashCode(callSuper = true)
@Data
@NoArgsConstructor
@AllArgsConstructor
public class MaterialQueryDTO extends PageQuery {
    private Integer user_id;
    private String file_type;
    private String category;
    private String tag;
    private String access_type;
    private Integer allow_ai;
    private String ai_index_status;
    private String keyword;
    private LocalDateTime start_time;
    private LocalDateTime end_time;
}
