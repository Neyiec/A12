package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 导出模板创建/更新请求参数 (API-95/96)
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ExportTemplateCreateDTO {
    private String name;
    private String export_type;
    private String template_data;
    private String description;
}
