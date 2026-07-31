package edu.zstu.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 导出任务详情
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ExportTaskVO {
    private int id;
    private int user_id;
    private int project_id;
    private Integer snapshot_version;
    private String export_type;
    private String status;
    private String config;
    private String file_name;
    private String file_url;
    private long file_size;
    private String download_url;
    private LocalDateTime url_expire_at;
    private String file_status;
    private String quality_report;
    private String error_msg;
    private Integer progress;
    private Integer retry_count;
    private String worker_id;
    private LocalDateTime started_at;
    private LocalDateTime created_at;
    private LocalDateTime updated_at;
    private LocalDateTime completed_at;
}
