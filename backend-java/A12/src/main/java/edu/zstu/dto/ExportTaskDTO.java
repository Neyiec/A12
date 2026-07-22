package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 导出任务创建请求参数
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ExportTaskDTO {
    private int project_id;
    private Integer snapshot_version;
    private String export_type;
    private String config;
}
