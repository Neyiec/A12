package edu.zstu.entity;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class Sys_Log {
    private int id;
    private int user_id;
    private String log_type; //日志类型(operation/download/browse/audit)
    private String module; //模块
    private String action;
    private String target_type; //目标类型
    private int target_id;
    private String detail; //json字符串 详细信息
    private String ip; //ip
    private LocalDateTime create_at;

}
