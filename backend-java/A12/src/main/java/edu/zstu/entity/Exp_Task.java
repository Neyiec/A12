package edu.zstu.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class Exp_Task {
    private int id;
    private int user_id;
    private int project_id;
    private int snapshot_version; //绑定的快照版本号
    private String export_type; //导出类型(pptx/word/package)
    private String status; //状态(queued/generating/checking/success/partial/failed/cancelled)
    private String config; //json字符串 导出配置
    private String file_name;
    private String file_url;
    private long file_size;
    private String download_url;
    private LocalDateTime url_expire_at;
    private String file_status; //文件状态(available/expired/cleaned)
    private String quality_report; //json字符串 质量报告
    private String error_msg;
    private LocalDateTime created_at;
    private LocalDateTime completed_at;
}
