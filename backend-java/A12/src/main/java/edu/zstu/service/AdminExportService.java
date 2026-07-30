package edu.zstu.service;

import edu.zstu.dto.ExportTemplateCreateDTO;
import edu.zstu.utils.PageResult;

import java.util.Map;

/**
 * 后台 — 导出模板模块 Service 接口<br>提供导出模板的查询、创建、版本更新和状态发布等业务方法。
 */

public interface AdminExportService {
    PageResult<Map<String, Object>> listTemplates(String exportType, String status, int page, int size);
    Map<String, Object> createTemplate(ExportTemplateCreateDTO dto);
    Map<String, Object> updateTemplate(String id, ExportTemplateCreateDTO dto);
    void updateTemplateStatus(String id, String status);
}

