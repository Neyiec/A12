package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 系统日志查询参数
 * 支持按用户、日志类型、所属模块和时间范围筛选
 */
@EqualsAndHashCode(callSuper = true)
@Data
@NoArgsConstructor
@AllArgsConstructor
public class LogQueryDTO extends PageQuery {
    private Integer user_id;
    private String log_type;
    private String module;
    private LocalDateTime start_time;
    private LocalDateTime end_time;
}
