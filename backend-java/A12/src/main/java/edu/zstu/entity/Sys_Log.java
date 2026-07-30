package edu.zstu.entity;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class Sys_Log {
    private long id;
    private Integer user_id;
    private String log_type; //日志类型(operation/download/browse/audit)
    private String module; //模块
    private String action;
    private String target_type; //目标类型
    private Integer target_id;
    private String detail; //json字符串 详细信息
    private String ip; //ip
    private String request_id;
    private String method;
    private String path;
    private String user_agent;
    private String status;
    private String error_message;
    private Integer duration_ms;
    private LocalDateTime create_at;

}
