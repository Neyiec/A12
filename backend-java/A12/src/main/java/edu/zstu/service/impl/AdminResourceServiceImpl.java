package edu.zstu.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import edu.zstu.dto.ItemStatusDTO;
import edu.zstu.dto.ResourceDTO;
import edu.zstu.entity.Adm_Resource;
import edu.zstu.entity.Res_Material;
import edu.zstu.mapper.AdmResourceMapper;
import edu.zstu.mapper.ResMaterialMapper;
import edu.zstu.service.AdminResourceService;
import edu.zstu.service.BusinessLogService;
import edu.zstu.service.PythonPptClient;
import edu.zstu.utils.OssUtil;
import edu.zstu.utils.PageResult;
import edu.zstu.vo.ResourceVO;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.net.URL;
import java.time.LocalDateTime;
import java.util.*;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Service
public class AdminResourceServiceImpl implements AdminResourceService {

    private final AdmResourceMapper resourceMapper;
    private final ResMaterialMapper materialMapper;
    private final OssUtil ossUtil;
    private final BusinessLogService businessLogService;
    private final PythonPptClient pythonPptClient;

    public AdminResourceServiceImpl(AdmResourceMapper resourceMapper, ResMaterialMapper materialMapper,
                                    OssUtil ossUtil, BusinessLogService businessLogService,
                                    PythonPptClient pythonPptClient) {
        this.resourceMapper = resourceMapper;
        this.materialMapper = materialMapper;
        this.ossUtil = ossUtil;
        this.businessLogService = businessLogService;
        this.pythonPptClient = pythonPptClient;
    }

    @Override
    public PageResult<ResourceVO> listResources(String resourceType, Integer status, int page, int size) {
        log.info("listResources resourceType={}, status={}, page={}, size={}", resourceType, status, page, size);
        PageHelper.startPage(page, size);
        List<Adm_Resource> list = resourceMapper.findByQuery(resourceType, status);
        PageInfo<Adm_Resource> info = new PageInfo<>(list);

        List<ResourceVO> records = info.getList().stream().map(this::toResourceVO).toList();
        PageResult<ResourceVO> r = new PageResult<>();
        r.setTotal(info.getTotal()); r.setPage(page); r.setSize(size); r.setRecords(records);
        return r;
    }

    @Override
    @Transactional
    public Map<String, Object> createUploadSession(ResourceDTO dto, Integer adminId) {
        log.info("createUploadSession adminId={}, resourceType={}, title={}", adminId, dto.getResource_type(), dto.getTitle());
        if (dto.getResource_type() == null || dto.getTitle() == null) {
            throw new RuntimeException("缺少必填字段: resource_type, title");
        }

        // 创建待上传记录 (status=0)
        Adm_Resource resource = new Adm_Resource();
        BeanUtil.copyProperties(dto, resource);
        resource.setStatus(0);
        resource.setUploaded_by(adminId);
        resource.setAi_index_status("pending");
        resourceMapper.insert(resource);

        // 生成 OSS 签名上传 URL
        String fileType = detectFileType(dto.getFile_type(), dto.getFile_name(), dto.getFile_url(), dto.getTitle());
        String objectKey = "public/" + dto.getResource_type() + "/" + resource.getId() + "_" + UUID.randomUUID()
                + extensionForFileType(fileType, dto.getFile_name(), dto.getFile_url(), dto.getTitle());
        URL signedUrl = ossUtil.generateUploadUrl(objectKey, 120);
        log.info("createUploadSession signedUrlCreated resourceId={}, objectKey={}", resource.getId(), objectKey);

        // 暂存 objectKey（用于 complete 时拼接 file_url）
        resource.setFile_url(ossUtil.getObjectUrl(objectKey));
        resourceMapper.update(resource);
        businessLogService.record("operation", "admin_resource", "create_upload_session", "resource", resource.getId(),
                Map.of("resource_type", dto.getResource_type(), "title", dto.getTitle()));

        Map<String, Object> result = new HashMap<>();
        result.put("upload_id", resource.getId());
        result.put("upload_url", signedUrl.toString());
        result.put("expires_at", LocalDateTime.now().plusMinutes(120));
        return result;
    }

    @Override
    @Transactional
    public ResourceVO completeUpload(Integer id, Integer adminId) {
        log.info("completeUpload uploadId={}, adminId={}", id, adminId);
        Adm_Resource resource = resourceMapper.findById(id);
        if (resource == null) throw new RuntimeException("上传会话不存在");
        if (resource.getStatus() != 0) throw new RuntimeException("上传会话状态异常");

        // 验证 OSS 文件是否存在
        String objectKey = ossUtil.extractObjectKey(resource.getFile_url());
        if (!ossUtil.doesObjectExist(objectKey)) {
            throw new RuntimeException("文件上传尚未完成或文件不存在于OSS");
        }

        resource.setStatus(1);
        resourceMapper.updateStatus(id, 1);
        log.info("completeUpload success resourceId={}, objectKey={}", id, objectKey);
        businessLogService.record("operation", "admin_resource", "complete_upload", "resource", id);
        syncPublicResourceIndex(resourceMapper.findById(id));
        return toResourceVO(resource);
    }

    @Override
    public ResourceVO getResource(Integer id) {
        log.info("getResource resourceId={}", id);
        Adm_Resource r = resourceMapper.findById(id);
        if (r == null) throw new RuntimeException("资源不存在");
        return toResourceVO(r);
    }

    @Override
    @Transactional
    public ResourceVO updateResource(Integer id, ResourceDTO dto, Integer adminId) {
        log.info("updateResource resourceId={}, adminId={}, title={}, subject={}, grade={}", id, adminId, dto.getTitle(), dto.getSubject(), dto.getGrade());
        Adm_Resource r = resourceMapper.findById(id);
        if (r == null) throw new RuntimeException("资源不存在");

        if (dto.getTitle() != null) r.setTitle(dto.getTitle());
        if (dto.getSubject() != null) r.setSubject(dto.getSubject());
        if (dto.getGrade() != null) r.setGrade(dto.getGrade());
        if (dto.getDescription() != null) r.setDescription(dto.getDescription());
        if (dto.getFile_url() != null) r.setFile_url(dto.getFile_url());
        if (dto.getTemplate_data() != null) r.setTemplate_data(dto.getTemplate_data());
        if (dto.getThumbnail() != null) r.setThumbnail(dto.getThumbnail());
        resourceMapper.update(r);
        log.info("updateResource success resourceId={}, status={}", id, r.getStatus());
        businessLogService.record("operation", "admin_resource", "update", "resource", id);
        if (r.getStatus() == 1) {
            syncPublicResourceIndex(resourceMapper.findById(id));
        }
        return toResourceVO(r);
    }

    @Override
    @Transactional
    public ResourceVO updateStatus(Integer id, ItemStatusDTO dto, Integer adminId) {
        log.info("updateStatus resourceId={}, adminId={}, status={}", id, adminId, dto.getStatus());
        Adm_Resource r = resourceMapper.findById(id);
        if (r == null) throw new RuntimeException("资源不存在");
        resourceMapper.updateStatus(id, dto.getStatus());
        r.setStatus(dto.getStatus());
        log.info("updateStatus success resourceId={}, status={}", id, dto.getStatus());
        businessLogService.record("operation", "admin_resource", "update_status", "resource", id,
                Map.of("status", dto.getStatus()));
        updatePublicResourceAvailability(r);
        return toResourceVO(r);
    }

    @Override
    public Map<String, Object> getProcessingStatus(Integer id) {
        log.info("getProcessingStatus resourceId={}", id);
        Adm_Resource r = resourceMapper.findById(id);
        if (r == null) throw new RuntimeException("资源不存在");

        // MVP 返回模拟处理状态（实际暂不接入安全检测/解析/索引流水线）
        Map<String, Object> result = new HashMap<>();
        result.put("security_check", "passed");
        result.put("parse_status", "completed");
        result.put("index_status", r.getAi_index_status() == null ? "pending" : r.getAi_index_status());
        result.put("indexed_at", r.getAi_indexed_at());
        result.put("error_msg", r.getAi_index_error() == null ? "" : r.getAi_index_error());
        return result;
    }

    @Override
    public Map<String, Object> bootstrapAiResourceIndex(boolean forceReparse) {
        log.info("bootstrapAiResourceIndex forceReparse={}", forceReparse);
        List<Map<String, Object>> resources = new ArrayList<>();
        for (Adm_Resource resource : resourceMapper.findActive()) {
            if (resource.getFile_url() != null && !resource.getFile_url().isBlank()) {
                resources.add(publicResourcePayload(resource, forceReparse));
            }
        }
        for (Res_Material material : materialMapper.findAiAvailable()) {
            if (material.getFile_url() != null && !material.getFile_url().isBlank()) {
                resources.add(personalResourcePayload(material, forceReparse));
            }
        }
        log.info("bootstrapAiResourceIndex callPython resourceCount={}, forceReparse={}", resources.size(), forceReparse);
        Map<String, Object> response = pythonPptClient.bootstrapResourceIndex(resources, forceReparse);
        log.info("bootstrapAiResourceIndex pythonResponseKeys={}", response.keySet());
        applyBootstrapStatuses(response);
        return response;
    }

    private void syncPublicResourceIndex(Adm_Resource resource) {
        if (resource == null || resource.getFile_url() == null || resource.getFile_url().isBlank()) {
            return;
        }
        try {
            resourceMapper.updateAiIndexStatus(resource.getId(), "indexing", null);
            log.info("syncPublicResourceIndex callPython resourceId={}", resource.getId());
            Map<String, Object> response = pythonPptClient.syncResourceIndex(publicResourcePayload(resource, false));
            Object data = response.get("data");
            String status = extractPythonStatus(data);
            if ("failed".equals(status)) {
                resourceMapper.updateAiIndexStatus(resource.getId(), "failed", extractPythonError(data));
            } else {
                resourceMapper.updateAiIndexStatus(resource.getId(), "completed", null);
            }
        } catch (Exception e) {
            log.warn("sync public resource index failed, resourceId={}", resource.getId(), e);
            resourceMapper.updateAiIndexStatus(resource.getId(), "failed", e.getMessage());
        }
    }

    private void updatePublicResourceAvailability(Adm_Resource resource) {
        try {
            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("source_type", "public");
            payload.put("resource_id", String.valueOf(resource.getId()));
            payload.put("available", resource.getStatus() == 1);
            payload.put("allow_ai", resource.getStatus() == 1);
            payload.put("metadata", Map.of(
                    "uploaded_by", String.valueOf(resource.getUploaded_by()),
                    "available", resource.getStatus() == 1
            ));
            pythonPptClient.updateResourceIndexMetadata(payload);
        } catch (Exception e) {
            log.warn("update public resource index metadata failed, resourceId={}", resource.getId(), e);
        }
    }

    private Map<String, Object> publicResourcePayload(Adm_Resource resource, boolean forceReparse) {
        Map<String, Object> metadata = new LinkedHashMap<>();
        metadata.put("subject", resource.getSubject());
        metadata.put("grade", resource.getGrade());
        metadata.put("resource_type", resource.getResource_type());
        metadata.put("description", resource.getDescription());
        String fileType = detectFileType(resource.getFile_url(), resource.getTitle(), resource.getResource_type());
        metadata.put("detected_file_type", fileType);

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("source_type", "public");
        payload.put("resource_id", String.valueOf(resource.getId()));
        payload.put("title", resource.getTitle());
        payload.put("file_url", resource.getFile_url());
        payload.put("file_type", fileType);
        payload.put("file_size", resource.getFile_size());
        payload.put("uploaded_by", String.valueOf(resource.getUploaded_by()));
        payload.put("owner_user_id", null);
        payload.put("available", resource.getStatus() == 1);
        payload.put("allow_ai", resource.getStatus() == 1);
        payload.put("metadata", metadata);
        payload.put("force_reparse", forceReparse);
        return payload;
    }

    private String detectFileType(String... values) {
        if (values == null) return "other";
        for (String value : values) {
            String direct = normalizeKnownFileType(value);
            if (!"other".equals(direct)) {
                return direct;
            }
            String ext = extensionFromValue(value);
            String fromExtension = normalizeKnownFileType(ext);
            if (!"other".equals(fromExtension)) {
                return fromExtension;
            }
        }
        return "other";
    }

    private String normalizeKnownFileType(String value) {
        if (value == null || value.isBlank()) return "other";
        String clean = value.trim().toLowerCase(Locale.ROOT);
        if (clean.contains("/")) {
            clean = clean.substring(clean.indexOf('/') + 1);
        }
        clean = clean.replace(".", "");
        return switch (clean) {
            case "doc", "docx" -> "word";
            case "pdf" -> "pdf";
            case "ppt", "pptx", "powerpoint" -> "ppt";
            case "txt", "text", "md", "markdown", "csv" -> "txt";
            case "jpg", "jpeg", "png", "gif", "bmp", "webp", "image" -> "image";
            case "mp3", "wav", "m4a", "aac", "ogg", "audio" -> "audio";
            case "mp4", "avi", "mov", "mkv", "webm", "wmv", "flv", "video" -> "video";
            default -> "other";
        };
    }

    private String extensionForFileType(String fileType, String... values) {
        for (String value : values) {
            String ext = extensionFromValue(value);
            if (!ext.isBlank() && !"other".equals(normalizeKnownFileType(ext))) {
                return "." + ext;
            }
        }
        return switch (fileType == null ? "other" : fileType) {
            case "word" -> ".docx";
            case "pdf" -> ".pdf";
            case "ppt" -> ".pptx";
            case "txt" -> ".txt";
            case "image" -> ".png";
            case "audio" -> ".mp3";
            case "video" -> ".mp4";
            default -> "";
        };
    }

    private String extensionFromValue(String value) {
        if (value == null || value.isBlank()) return "";
        String clean = value.split("\\?", 2)[0].split("#", 2)[0].toLowerCase(Locale.ROOT);
        int slash = Math.max(clean.lastIndexOf('/'), clean.lastIndexOf('\\'));
        String name = slash >= 0 ? clean.substring(slash + 1) : clean;
        int dot = name.lastIndexOf('.');
        if (dot < 0 || dot == name.length() - 1) return "";
        return name.substring(dot + 1);
    }

    private Map<String, Object> personalResourcePayload(Res_Material material, boolean forceReparse) {
        Map<String, Object> metadata = new LinkedHashMap<>();
        metadata.put("description", material.getDescription());
        metadata.put("categories", material.getCategories());
        metadata.put("tags", material.getTags());
        metadata.put("access_type", material.getAccess_type());
        metadata.put("authorized_users", material.getAuthorized_users());

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("source_type", "personal");
        payload.put("resource_id", String.valueOf(material.getId()));
        payload.put("title", material.getFile_name());
        payload.put("file_url", material.getFile_url());
        payload.put("file_type", material.getFile_type());
        payload.put("file_size", material.getFile_size());
        payload.put("uploaded_by", String.valueOf(material.getUser_id()));
        payload.put("owner_user_id", String.valueOf(material.getUser_id()));
        payload.put("available", material.getStatus() == 1 && material.getAllow_ai() == 1);
        payload.put("allow_ai", material.getAllow_ai() == 1);
        payload.put("metadata", metadata);
        payload.put("force_reparse", forceReparse);
        return payload;
    }

    @SuppressWarnings("unchecked")
    private String extractPythonStatus(Object data) {
        if (data instanceof Map<?, ?> map) {
            Object status = map.get("status");
            return status == null ? "" : String.valueOf(status);
        }
        return "";
    }

    @SuppressWarnings("unchecked")
    private String extractPythonError(Object data) {
        if (data instanceof Map<?, ?> map) {
            Object error = map.get("error_message");
            return error == null ? "" : String.valueOf(error);
        }
        return "";
    }

    @SuppressWarnings("unchecked")
    private void applyBootstrapStatuses(Map<String, Object> response) {
        Object data = response.get("data");
        if (!(data instanceof Map<?, ?> dataMap)) {
            return;
        }
        Object results = dataMap.get("results");
        if (!(results instanceof List<?> list)) {
            return;
        }
        for (Object item : list) {
            if (!(item instanceof Map<?, ?> result)) {
                continue;
            }
            String resourceKey = String.valueOf(result.get("resource_key"));
            String status = String.valueOf(result.get("status"));
            String mappedStatus = "failed".equals(status) ? "failed" : "completed";
            String error = result.get("error_message") == null ? null : String.valueOf(result.get("error_message"));
            if (resourceKey.startsWith("public:")) {
                resourceMapper.updateAiIndexStatus(Integer.valueOf(resourceKey.substring("public:".length())), mappedStatus, error);
            } else if (resourceKey.startsWith("personal:")) {
                materialMapper.updateAiIndexStatus(Integer.valueOf(resourceKey.substring("personal:".length())), mappedStatus, error);
            }
        }
    }

    private ResourceVO toResourceVO(Adm_Resource r) {
        ResourceVO vo = new ResourceVO();
        BeanUtil.copyProperties(r, vo);
        return vo;
    }
}


