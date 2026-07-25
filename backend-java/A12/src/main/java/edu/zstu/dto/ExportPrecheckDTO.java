package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 导出预检请求参数 (API-43)
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ExportPrecheckDTO {
    private int snapshot_version;
    private String export_type;
}
