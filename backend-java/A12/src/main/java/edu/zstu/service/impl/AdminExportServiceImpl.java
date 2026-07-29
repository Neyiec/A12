package edu.zstu.service.impl;

import edu.zstu.dto.ExportTemplateCreateDTO;
import edu.zstu.entity.Sys_Config;
import edu.zstu.mapper.SysConfigMapper;
import edu.zstu.service.AdminExportService;
import edu.zstu.service.BusinessLogService;
import edu.zstu.utils.CurrentHolder;
import edu.zstu.utils.PageResult;
import edu.zstu.utils.RedisCacheUtil;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.Duration;
import java.util.List;
import java.util.Map;

@Service
public class AdminExportServiceImpl implements AdminExportService {
    private final SysConfigMapper configMapper;
    private final BusinessLogService businessLogService;
    private final RedisCacheUtil redisCacheUtil;

    public AdminExportServiceImpl(SysConfigMapper configMapper, BusinessLogService businessLogService,
                                  RedisCacheUtil redisCacheUtil) {
        this.configMapper = configMapper;
        this.businessLogService = businessLogService;
        this.redisCacheUtil = redisCacheUtil;
    }

    @Override
    public PageResult<Map<String, Object>> listTemplates(String exportType, String status, int page, int size) {
        String key = "config:template:list:" + blankToAll(exportType) + ":" + blankToAll(status) + ":p" + page + ":s" + size;
        return redisCacheUtil.getOrLoad(key,
                new com.fasterxml.jackson.core.type.TypeReference<PageResult<Map<String, Object>>>() {},
                Duration.ofMinutes(5), () -> {
                    int p = page <= 0 ? 1 : page;
                    int s = size <= 0 ? 10 : size;
                    List<Map<String, Object>> all = configMapper.findByGroup("template").stream()
                            .filter(c -> exportType == null || exportType.isBlank() || c.getConfig_key().contains(exportType))
                            .filter(c -> status == null || status.isBlank() || status.equals(c.getStatus()))
                            .map(this::toMap)
                            .toList();
                    int from = Math.min((p - 1) * s, all.size());
                    int to = Math.min(from + s, all.size());
                    return new PageResult<>(all.size(), p, s, all.subList(from, to));
                });
    }

    @Override
    @Transactional
    public Map<String, Object> createTemplate(ExportTemplateCreateDTO dto) {
        if (dto.getName() == null || dto.getName().isBlank()) throw new RuntimeException("模板名称不能为空");
        if (dto.getExport_type() == null || dto.getExport_type().isBlank()) throw new RuntimeException("导出类型不能为空");
        if (dto.getTemplate_data() == null || dto.getTemplate_data().isBlank()) throw new RuntimeException("模板数据不能为空");
        Sys_Config config = new Sys_Config();
        config.setConfig_group("template");
        config.setConfig_key(dto.getExport_type() + ":" + dto.getName());
        config.setConfig_value(dto.getTemplate_data());
        config.setDescription(dto.getDescription());
        config.setUpdated_by(CurrentHolder.getCurrentId());
        config.setUpdated_at(LocalDateTime.now());
        config.setVersion(1);
        config.setStatus("draft");
        configMapper.insert(config);
        evictTemplateCache(config);
        businessLogService.record("operation", "admin_export_template", "create", "config", config.getId(),
                Map.of("name", dto.getName(), "export_type", dto.getExport_type()));
        return Map.of("id", config.getId(), "version", config.getVersion());
    }

    @Override
    @Transactional
    public Map<String, Object> updateTemplate(String id, ExportTemplateCreateDTO dto) {
        Sys_Config config = requireConfig(id);
        if (dto.getName() != null && !dto.getName().isBlank()) {
            String exportType = dto.getExport_type() == null || dto.getExport_type().isBlank()
                    ? config.getConfig_key().split(":", 2)[0] : dto.getExport_type();
            config.setConfig_key(exportType + ":" + dto.getName());
        }
        if (dto.getTemplate_data() != null) {
            config.setConfig_value(dto.getTemplate_data());
            config.setVersion(config.getVersion() + 1);
        }
        if (dto.getDescription() != null) config.setDescription(dto.getDescription());
        config.setUpdated_by(CurrentHolder.getCurrentId());
        configMapper.update(config);
        evictTemplateCache(config);
        businessLogService.record("operation", "admin_export_template", "update", "config", config.getId(),
                Map.of("version", config.getVersion()));
        return Map.of("id", config.getId(), "version", config.getVersion());
    }

    @Override
    @Transactional
    public void updateTemplateStatus(String id, String status) {
        if (!"published".equals(status) && !"unpublished".equals(status)) throw new RuntimeException("无效状态");
        Sys_Config config = requireConfig(id);
        configMapper.updateStatus(Integer.parseInt(id), status);
        evictTemplateCache(config);
        businessLogService.record("operation", "admin_export_template", "update_status", "config", Integer.parseInt(id),
                Map.of("status", status));
    }

    private Sys_Config requireConfig(String id) {
        Sys_Config config = configMapper.findById(Integer.parseInt(id));
        if (config == null || !"template".equals(config.getConfig_group())) throw new RuntimeException("模板不存在");
        return config;
    }

    private Map<String, Object> toMap(Sys_Config c) {
        String[] parts = c.getConfig_key().split(":", 2);
        return Map.of("id", c.getId(), "name", parts.length > 1 ? parts[1] : c.getConfig_key(),
                "export_type", parts[0], "version", c.getVersion(), "status", c.getStatus(),
                "created_at", c.getUpdated_at(), "updated_at", c.getUpdated_at());
    }

    private void evictTemplateCache(Sys_Config config) {
        redisCacheUtil.delete("config:all");
        redisCacheUtil.delete("config:group:template");
        redisCacheUtil.delete("config:key:" + config.getConfig_key());
        redisCacheUtil.deleteByPattern("config:template:list:*");
    }

    private String blankToAll(String value) {
        return value == null || value.isBlank() ? "all" : value;
    }
}
