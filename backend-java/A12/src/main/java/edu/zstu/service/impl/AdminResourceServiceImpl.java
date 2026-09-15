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
    private final PublicResourceIndexSyncService publicResourceIndexSyncService;
    private final ResourceIndexSyncService resourceIndexSyncService;

    public AdminResourceServiceImpl(AdmResourceMapper resourceMapper, ResMaterialMapper materialMapper,
                                    OssUtil ossUtil, BusinessLogService businessLogService,
                                    PythonPptClient pythonPptClient,
                                    PublicResourceIndexSyncService publicResourceIndexSyncService,
                                    ResourceIndexSyncService resourceIndexSyncService) {
        this.resourceMapper = resourceMapper;
        this.materialMapper = materialMapper;
        this.ossUtil = ossUtil;
        this.businessLogService = businessLogService;
        this.pythonPptClient = pythonPptClient;
        this.publicResourceIndexSyncService = publicResourceIndexSyncService;
        this.resourceIndexSyncService = resourceIndexSyncService;
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
        URL signedUrl = ossUtil.generateUploadUrl(objectKey, dto.getFile_type(),120);
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
        // 索引同步异步化：仅标记 indexing 后立即返回，Python 解析在 resourceIndexExecutor 线程池执行（前端轮询状态）
        Adm_Resource synced = resourceMapper.findById(id);
        resourceMapper.updateAiIndexStatus(id, "indexing", null);
        publicResourceIndexSyncService.syncPublicResourceIndex(id, publicResourcePayload(synced, false));
        return toResourceVO(resourceMapper.findById(id));
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
            // 索引同步异步化：编辑启用态资源同样只标记 indexing 后立即返回
            resourceMapper.updateAiIndexStatus(id, "indexing", null);
            publicResourceIndexSyncService.syncPublicResourceIndex(id,
                    publicResourcePayload(resourceMapper.findById(id), false));
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
    @Transactional
    public ResourceVO deleteResource(Integer id, Integer adminId) {
        log.info("deleteResource resourceId={}, adminId={}", id, adminId);
        Adm_Resource resource = resourceMapper.findById(id);
        if (resource == null) throw new RuntimeException("资源不存在");

        // 先清理 Python 侧向量索引（失败则抛出回滚，避免留下孤儿向量），再删 MySQL 行
        try {
            pythonPptClient.deleteResourceIndex("public", id);
        } catch (Exception e) {
            log.warn("delete public resource index failed, resourceId={}", id, e);
            throw new RuntimeException("清理 AI 索引失败，请稍后重试: " + e.getMessage());
        }
        resourceMapper.deleteById(id);
        // OSS 对象删除尽力而为：失败不影响记录删除（残留对象可由桶生命周期策略清理）
        try {
            ossUtil.deleteObject(ossUtil.extractObjectKey(resource.getFile_url()));
        } catch (Exception e) {
            log.warn("delete oss object failed, resourceId={}", id, e);
        }
        log.info("deleteResource success resourceId={}", id);
        businessLogService.record("operation", "admin_resource", "delete", "resource", id,
                Map.of("title", String.valueOf(resource.getTitle())));
        return toResourceVO(resource);
    }

    @Override
    @Transactional
    public ResourceVO reparseResource(Integer id, Integer adminId) {
        log.info("reparseResource resourceId={}, adminId={}", id, adminId);
        Adm_Resource resource = resourceMapper.findById(id);
        if (resource == null) throw new RuntimeException("资源不存在");
        if (resource.getStatus() != 1) throw new RuntimeException("仅启用状态的资源可重新解析");
        if (resource.getFile_url() == null || resource.getFile_url().isBlank()) {
            throw new RuntimeException("资源文件缺失，无法解析");
        }
        // force_reparse=true：绕过 file_fingerprint 短路，强制重新解析并重建向量
        // 索引同步异步化：标记 indexing 后立即返回，前端轮询 processing-status 获取最终状态
        resourceMapper.updateAiIndexStatus(id, "indexing", null);
        publicResourceIndexSyncService.syncPublicResourceIndex(id,
                publicResourcePayload(resourceMapper.findById(id), true));
        return toResourceVO(resourceMapper.findById(id));
    }

    @Override
    public Map<String, Object> getDownloadUrl(Integer id) {
        log.info("getDownloadUrl resourceId={}", id);
        Adm_Resource resource = resourceMapper.findById(id);
        if (resource == null) throw new RuntimeException("资源不存在");
        if (resource.getFile_url() == null || resource.getFile_url().isBlank()) {
            throw new RuntimeException("资源文件缺失，无法下载");
        }
        // 私有读桶：下发 60 分钟预签名 GET URL，前端直接触发浏览器下载
        String downloadUrl = ossUtil.resolveDownloadUrl(resource.getFile_url(), 60);
        Map<String, Object> result = new HashMap<>();
        result.put("download_url", downloadUrl);
        result.put("expires_minutes", 60);
        return result;
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

    @Override
    public Map<String, Object> aiIndexOverview() {
        log.info("aiIndexOverview");
        return unwrapPythonData(pythonPptClient.resourceIndexOverview());
    }

    @Override
    public Map<String, Object> aiIndexTasks(String sourceType, String parseStatus, String keyword, int page, int size) {
        log.info("aiIndexTasks sourceType={}, parseStatus={}, keyword={}, page={}, size={}",
                sourceType, parseStatus, keyword, page, size);
        int limit = Math.max(1, Math.min(size, 200));
        int safePage = Math.max(page, 1);
        int offset = (safePage - 1) * limit;
        Map<String, Object> data = unwrapPythonData(pythonPptClient.listResourceIndexResources(
                sourceType, null, limit, offset, parseStatus, keyword));
        // PG 行仅终态落库（completed/failed），进行中的 indexing 状态以 MySQL ai_index_status 为准（按域批量查询，禁止逐行）
        enrichTasksWithMysqlIndexStatus(data);
        return data;
    }

    @Override
    public Map<String, Object> aiIndexResource(String sourceType, String resourceId, Integer chunkLimit) {
        log.info("aiIndexResource sourceType={}, resourceId={}, chunkLimit={}", sourceType, resourceId, chunkLimit);
        try {
            return unwrapPythonData(pythonPptClient.getResourceIndexResource(sourceType, resourceId, chunkLimit));
        } catch (RuntimeException e) {
            if (e.getMessage() != null && e.getMessage().contains("HTTP 404")) {
                throw new RuntimeException("该资源尚未建立索引或索引已被移除");
            }
            throw e;
        }
    }

    @Override
    public Map<String, Object> aiIndexSearch(String query, String sourceType, Integer topK) {
        log.info("aiIndexSearch sourceType={}, topK={}, queryLength={}", sourceType, topK,
                query == null ? 0 : query.length());
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("query", query);
        if (sourceType != null && !sourceType.isBlank()) {
            payload.put("source_type", sourceType);
        }
        payload.put("top_k", topK == null ? 10 : Math.max(1, Math.min(topK, 30)));
        return unwrapPythonData(pythonPptClient.searchResourceIndex(payload));
    }

    @Override
    public Map<String, Object> aiIndexReparse(String sourceType, Integer resourceId, Integer adminId) {
        log.info("aiIndexReparse sourceType={}, resourceId={}, adminId={}", sourceType, resourceId, adminId);
        Map<String, Object> result = new LinkedHashMap<>();
        if ("personal".equals(sourceType)) {
            Res_Material material = materialMapper.findById(resourceId);
            if (material == null) throw new RuntimeException("素材不存在");
            if (material.getAllow_ai() == null || material.getAllow_ai() != 1) {
                throw new RuntimeException("素材未开启 AI 引用，无法重新解析");
            }
            if (material.getFile_url() == null || material.getFile_url().isBlank()) {
                throw new RuntimeException("素材文件缺失，无法解析");
            }
            // 异步化：仅标记 indexing 后立即返回，Python 解析在 resourceIndexExecutor 线程池执行
            materialMapper.updateAiIndexStatus(resourceId, "indexing", null);
            resourceIndexSyncService.syncPersonalResourceIndex(materialMapper.findById(resourceId), true);
            result.put("source_type", "personal");
            result.put("resource_id", String.valueOf(resourceId));
            result.put("status", "indexing");
            return result;
        }
        if (!"public".equals(sourceType)) {
            throw new RuntimeException("无效的资源来源类型: " + sourceType);
        }
        ResourceVO vo = reparseResource(resourceId, adminId);
        result.put("source_type", "public");
        result.put("resource_id", String.valueOf(resourceId));
        result.put("status", vo.getAi_index_status());
        return result;
    }

    /** 解包 Python Result 信封中的 data（无 data 时返回空 Map） */
    @SuppressWarnings("unchecked")
    private Map<String, Object> unwrapPythonData(Map<String, Object> response) {
        if (response == null) {
            return new LinkedHashMap<>();
        }
        Object data = response.get("data");
        return data instanceof Map ? (Map<String, Object>) data : new LinkedHashMap<>();
    }

    private Integer parseResourceId(Object value) {
        if (value == null) return null;
        try {
            return Integer.valueOf(String.valueOf(value));
        } catch (NumberFormatException e) {
            return null;
        }
    }

    @SuppressWarnings("unchecked")
    private void enrichTasksWithMysqlIndexStatus(Map<String, Object> data) {
        Object itemsObj = data.get("items");
        if (!(itemsObj instanceof List<?> items) || items.isEmpty()) {
            return;
        }
        List<Integer> publicIds = new ArrayList<>();
        List<Integer> personalIds = new ArrayList<>();
        for (Object item : items) {
            if (item instanceof Map<?, ?> row) {
                Integer id = parseResourceId(row.get("resource_id"));
                if (id == null) continue;
                if ("public".equals(row.get("source_type"))) {
                    publicIds.add(id);
                } else if ("personal".equals(row.get("source_type"))) {
                    personalIds.add(id);
                }
            }
        }
        Map<Integer, String> statusMap = new HashMap<>();
        if (!publicIds.isEmpty()) {
            for (Adm_Resource r : resourceMapper.findByIds(publicIds)) {
                statusMap.put(r.getId(), r.getAi_index_status());
            }
        }
        if (!personalIds.isEmpty()) {
            for (Res_Material m : materialMapper.findByIds(personalIds)) {
                statusMap.put(m.getId(), m.getAi_index_status());
            }
        }
        for (Object item : items) {
            if (item instanceof Map) {
                Map<String, Object> row = (Map<String, Object>) item;
                String pgStatus = row.get("parse_status") == null ? "" : String.valueOf(row.get("parse_status"));
                Integer id = parseResourceId(row.get("resource_id"));
                String mysqlStatus = id == null ? null : statusMap.get(id);
                row.put("effective_status", "indexing".equals(mysqlStatus) ? "indexing" : pgStatus);
            }
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
        // Python 侧需要实时下载文件做解析，必须传带签名的临时下载 URL（裸 URL 在私有读 bucket 下会 403）
        payload.put("file_url", ossUtil.resolveDownloadUrl(resource.getFile_url(), 60));
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
        // Python 侧需要实时下载文件做解析，必须传带签名的临时下载 URL（裸 URL 在私有读 bucket 下会 403）
        payload.put("file_url", ossUtil.resolveDownloadUrl(material.getFile_url(), 60));
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


