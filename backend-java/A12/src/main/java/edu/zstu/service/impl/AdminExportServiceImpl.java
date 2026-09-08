package edu.zstu.service.impl;

import edu.zstu.dto.ExportTemplateCreateDTO;
import edu.zstu.entity.Sys_Config;
import edu.zstu.mapper.SysConfigMapper;
import edu.zstu.service.AdminExportService;
import edu.zstu.service.BusinessLogService;
import edu.zstu.service.PythonPptClient;
import edu.zstu.utils.PageResult;
import edu.zstu.utils.RedisCacheUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
public class AdminExportServiceImpl implements AdminExportService {
    private final SysConfigMapper configMapper;
    private final BusinessLogService businessLogService;
    private final RedisCacheUtil redisCacheUtil;
    private final PythonPptClient pythonPptClient;

    public AdminExportServiceImpl(SysConfigMapper configMapper, BusinessLogService businessLogService,
                                  RedisCacheUtil redisCacheUtil, PythonPptClient pythonPptClient) {
        this.configMapper = configMapper;
        this.businessLogService = businessLogService;
        this.redisCacheUtil = redisCacheUtil;
        this.pythonPptClient = pythonPptClient;
    }

    @Override
    public PageResult<Map<String, Object>> listTemplates(String exportType, String status, int page, int size) {
        log.info("listTemplates exportType={}, status={}, page={}, size={}", exportType, status, page, size);
        String key = "config:template:list:" + blankToAll(exportType) + ":" + blankToAll(status) + ":p" + page + ":s" + size;
        return redisCacheUtil.getOrLoad(key,
                new com.fasterxml.jackson.core.type.TypeReference<PageResult<Map<String, Object>>>() {},
                Duration.ofMinutes(5), () -> {
                    int p = page <= 0 ? 1 : page;
                    int s = size <= 0 ? 10 : size;
                    List<Map<String, Object>> all = fetchPythonTemplates().stream()
                            .filter(t -> exportType == null || exportType.isBlank() || exportType.equals(t.get("export_type")))
                            .filter(t -> status == null || status.isBlank() || status.equals(t.get("status")))
                            .toList();
                    int from = Math.min((p - 1) * s, all.size());
                    int to = Math.min(from + s, all.size());
                    return new PageResult<>(all.size(), p, s, all.subList(from, to));
                });
    }

    /**
     * 模板真实存储在 Python PPT 服务（模板 JSON 文件），这里调 API-134 GET /api/v1/python/templates 获取，
     * 并映射为 API-98 响应结构 {id, name, export_type, version, status, created_at, updated_at}：
     * id 取 theme（替换等操作以此为准），export_type 固定 pptx，status 固定 published（Python 模板均可用），
     * created_at/updated_at Python 不提供，置 null 由前端显示 '—'
     */
    private List<Map<String, Object>> fetchPythonTemplates() {
        Map<String, Object> res = pythonPptClient.templates();
        Object code = res.get("code");
        if (code != null && !"200".equals(String.valueOf(code))) {
            throw new RuntimeException("获取Python模板列表失败: " + res.get("message"));
        }
        Object data = res.get("data");
        if (!(data instanceof Map<?, ?> dataMap)) return List.of();
        Object templates = dataMap.get("templates");
        if (!(templates instanceof List<?> templateList)) return List.of();
        List<Map<String, Object>> result = new ArrayList<>();
        for (Object item : templateList) {
            if (!(item instanceof Map<?, ?> t)) continue;
            String theme = str(t.get("theme"));
            if (theme == null || theme.isBlank()) continue;
            String name = str(t.get("template_name"));
            Map<String, Object> vo = new LinkedHashMap<>();
            vo.put("id", theme);
            vo.put("name", name == null || name.isBlank() ? theme : name);
            vo.put("export_type", "pptx");
            vo.put("version", 1);
            vo.put("status", "published");
            vo.put("description", str(t.get("description")));
            vo.put("is_default", Boolean.TRUE.equals(t.get("is_default")));
            vo.put("filename", str(t.get("filename")));
            vo.put("size", t.get("size"));
            vo.put("created_at", null);
            vo.put("updated_at", null);
            result.add(vo);
        }
        return result;
    }

    private String str(Object value) {
        return value == null ? null : String.valueOf(value);
    }

    /**
     * 创建导出模板 — 转发 Python 落盘为 {theme}.json（模板唯一存储在 Python 侧，不再写 sys_config）
     * template_data 必须是模板 JSON 文件文本内容（含 html_template 字段），由 Python 校验
     */
    @Override
    public Map<String, Object> createTemplate(ExportTemplateCreateDTO dto) {
        log.info("createTemplate name={}, exportType={}", dto.getName(), dto.getExport_type());
        if (dto.getName() == null || dto.getName().isBlank()) throw new RuntimeException("模板名称不能为空");
        if (dto.getExport_type() == null || dto.getExport_type().isBlank()) throw new RuntimeException("导出类型不能为空");
        // 后端导出类型词表为 pptx / word，教案模板尚未开放
        if (!"pptx".equals(dto.getExport_type())) throw new RuntimeException("目前仅支持 PPTX 模板，Word 教案模板暂未开放");
        if (dto.getTemplate_data() == null || dto.getTemplate_data().isBlank()) throw new RuntimeException("模板数据不能为空");
        Map<String, Object> res = pythonPptClient.createTemplate(dto.getName().trim(), dto.getTemplate_data(), dto.getDescription());
        String theme = requireEnvelopeTheme(res);
        evictTemplateCache(theme);
        log.info("createTemplate success theme={}", theme);
        businessLogService.record("operation", "admin_export_template", "create", "config", null,
                Map.of("name", dto.getName(), "theme", theme, "export_type", dto.getExport_type()));
        return Map.of("id", theme, "version", 1);
    }

    /**
     * 替换导出模板内容 — 转发 Python 覆盖 {theme}.json（id 即 theme；默认模板由 Python 侧拒绝）
     */
    @Override
    public Map<String, Object> updateTemplate(String id, ExportTemplateCreateDTO dto) {
        log.info("updateTemplate theme={}, exportType={}", id, dto.getExport_type());
        if (id == null || id.isBlank()) throw new RuntimeException("模板 ID 不能为空");
        if (dto.getTemplate_data() == null || dto.getTemplate_data().isBlank()) throw new RuntimeException("模板数据不能为空");
        Map<String, Object> res = pythonPptClient.replaceTemplate(id, dto.getTemplate_data(), dto.getDescription());
        String theme = requireEnvelopeTheme(res);
        evictTemplateCache(theme);
        log.info("updateTemplate success theme={}", theme);
        businessLogService.record("operation", "admin_export_template", "replace", "config", null,
                Map.of("theme", theme));
        return Map.of("id", theme, "version", 1);
    }

    @Override
    @Transactional
    public void updateTemplateStatus(String id, String status) {
        log.info("updateTemplateStatus templateId={}, status={}", id, status);
        if (!"published".equals(status) && !"unpublished".equals(status)) throw new RuntimeException("无效状态");
        Sys_Config config = requireConfig(id);
        configMapper.updateStatus(Integer.parseInt(id), status);
        evictTemplateCache(config.getConfig_key().split(":", 2)[0]);
        log.info("updateTemplateStatus success templateId={}, status={}", id, status);
        businessLogService.record("operation", "admin_export_template", "update_status", "config", Integer.parseInt(id),
                Map.of("status", status));
    }

    /**
     * 删除导出模板 — 转发 Python 删除 {theme}.json（默认模板不可删除）
     */
    @Override
    public void deleteTemplate(String id) {
        log.info("deleteTemplate theme={}", id);
        if (id == null || id.isBlank()) throw new RuntimeException("模板 ID 不能为空");
        Map<String, Object> res = pythonPptClient.deleteTemplate(id);
        String theme = requireEnvelopeTheme(res);
        evictTemplateCache(theme);
        log.info("deleteTemplate success theme={}", theme);
        businessLogService.record("operation", "admin_export_template", "delete", "config", null,
                Map.of("theme", theme));
    }

    /**
     * 下载导出模板 JSON 文件 — 从 Python 拉取字节流与 UTF-8 文件名
     */
    @Override
    public PythonPptClient.PythonFileResult downloadTemplate(String id) {
        log.info("downloadTemplate theme={}", id);
        if (id == null || id.isBlank()) throw new RuntimeException("模板 ID 不能为空");
        return pythonPptClient.downloadTemplate(id);
    }

    /** 校验 Python Result envelope 并取出 data.theme，业务错误（code != 200）直接抛出 message */
    private String requireEnvelopeTheme(Map<String, Object> res) {
        Object code = res.get("code");
        if (code != null && !"200".equals(String.valueOf(code))) {
            throw new RuntimeException(res.get("message") == null ? "Python模板服务调用失败" : String.valueOf(res.get("message")));
        }
        Object data = res.get("data");
        if (data instanceof Map<?, ?> dataMap && dataMap.get("theme") != null) {
            return String.valueOf(dataMap.get("theme"));
        }
        throw new RuntimeException("Python模板服务返回数据异常");
    }

    private Sys_Config requireConfig(String id) {
        Sys_Config config = configMapper.findById(Integer.parseInt(id));
        if (config == null || !"template".equals(config.getConfig_group())) throw new RuntimeException("模板不存在");
        return config;
    }

    /** 模板存储已迁移至 Python 侧，此处仅清理模板列表相关 Redis 缓存（theme 为空则只清列表缓存） */
    private void evictTemplateCache(String theme) {
        redisCacheUtil.delete("config:all");
        redisCacheUtil.delete("config:group:template");
        if (theme != null && !theme.isBlank()) {
            redisCacheUtil.delete("config:key:pptx:" + theme);
            redisCacheUtil.delete("config:key:word:" + theme);
        }
        redisCacheUtil.deleteByPattern("config:template:list:*");
    }

    private String blankToAll(String value) {
        return value == null || value.isBlank() ? "all" : value;
    }
}


