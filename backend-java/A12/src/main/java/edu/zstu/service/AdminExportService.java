package edu.zstu.service;

/**
 * 后台 — 导出模板模块 Service 接口<br>提供导出模板的查询、创建、版本更新和状态发布等业务方法。
 */

public interface AdminExportService {
    Object listTemplates();
    Object createTemplate();
    Object updateTemplate(String id);
    Object updateTemplateStatus(String id);
}

