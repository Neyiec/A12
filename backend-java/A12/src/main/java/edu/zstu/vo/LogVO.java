package edu.zstu.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 系统日志记录
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class LogVO {
    private long id;
    private Integer user_id;
    private String log_type;
    private String module;
    private String action;
    private String target_type;
    private Integer target_id;
    private String detail;
    private String ip;
    private String request_id;
    private String method;
    private String path;
    private String user_agent;
    private String status;
    private String error_message;
    private Integer duration_ms;
    private LocalDateTime created_at;
}
