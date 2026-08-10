package edu.zstu.service.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.json.JSONArray;
import cn.hutool.json.JSONUtil;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import edu.zstu.dto.MaterialDTO;
import edu.zstu.dto.MaterialQueryDTO;
import edu.zstu.dto.ResourceBatchActionDTO;
import edu.zstu.dto.ResourceTaxonomyDTO;
import edu.zstu.dto.ResourceUploadConfirmDTO;
import edu.zstu.dto.UploadTokenDTO;
import edu.zstu.entity.Res_Metadata_Dictionary;
import edu.zstu.entity.Res_Material;
import edu.zstu.mapper.ResMetadataDictionaryMapper;
import edu.zstu.mapper.ResMaterialMapper;
import edu.zstu.service.BusinessLogService;
import edu.zstu.service.PythonPptClient;
import edu.zstu.service.ResourceService;
import edu.zstu.utils.OssUtil;
import edu.zstu.utils.PageResult;
import edu.zstu.vo.MaterialVO;
import edu.zstu.vo.UploadTokenVO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.net.URL;
import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;

@Slf4j
@Service
public class ResourceServiceImpl implements ResourceService {

    private static final Set<String> ACCESS_TYPES = Set.of("private", "shared", "authorized");
    private static final Set<String> AI_INDEX_STATUSES = Set.of("pending", "indexing", "completed", "failed", "disabled");
    private static final Set<String> FILE_TYPES = Set.of("word", "pdf", "ppt", "txt", "image", "audio", "video", "other");

    private final ResMaterialMapper materialMapper;
    private final ResMetadataDictionaryMapper dictionaryMapper;
    private final OssUtil ossUtil;
    private final BusinessLogService businessLogService;
    private final PythonPptClient pythonPptClient;

    public ResourceServiceImpl(ResMaterialMapper materialMapper, ResMetadataDictionaryMapper dictionaryMapper, OssUtil ossUtil,
                               BusinessLogService businessLogService,
                               PythonPptClient pythonPptClient) {
        this.materialMapper = materialMapper;
        this.dictionaryMapper = dictionaryMapper;
        this.ossUtil = ossUtil;
        this.businessLogService = businessLogService;
        this.pythonPptClient = pythonPptClient;
    }

    @Override
    public UploadTokenVO createUploadToken(UploadTokenDTO dto, Integer userId) {
        log.info("createUploadToken userId={}, fileName={}", userId, dto.getFile_name());
        if (dto.getFile_name() == null || dto.getFile_name().isBlank()) {
            throw new RuntimeException("文件名不能为空");
        }
        String objectKey = "uploads/" + userId + "/" + UUID.randomUUID() + "/" + dto.getFile_name();
        URL signedUrl = ossUtil.generateUploadUrl(objectKey, 60);
        log.info("createUploadToken success userId={}, objectKey={}", userId, objectKey);

        UploadTokenVO vo = new UploadTokenVO();
        vo.setObject_key(objectKey);
        vo.setUpload_url(signedUrl.toString());
        vo.setExpires_at(LocalDateTime.now().plusMinutes(60));
        return vo;
    }

    @Override
    @Transactional
    public MaterialVO confirmUpload(ResourceUploadConfirmDTO dto, Integer userId) {
        log.info("confirmUpload userId={}, fileName={}, replaceTargetId={}", userId, dto.getFile_name(), dto.getReplace_target_id());
        if (!ossUtil.doesObjectExist(dto.getObject_key())) {
            throw new RuntimeException("文件上传尚未完成或文件不存在于OSS");
        }

        if (dto.getReplace_target_id() != null) {
            Res_Material old = materialMapper.findById(dto.getReplace_target_id());
            if (old == null || !Objects.equals(old.getUser_id(), userId)) {
                ossUtil.deleteObject(dto.getObject_key());
                throw new RuntimeException("要替换的资源不存在或无权操作");
            }
            ossUtil.deleteObject(ossUtil.extractObjectKey(old.getFile_url()));
            materialMapper.softDelete(dto.getReplace_target_id());
            deletePersonalResourceIndex(dto.getReplace_target_id());
        }

        String fileType = dto.getFile_type();
        if (fileType == null || fileType.isBlank()) {
            fileType = detectFileType(dto.getFile_name());
        }

        Res_Material material = new Res_Material();
        material.setUser_id(userId);
        material.setFile_name(dto.getFile_name());
        material.setFile_type(fileType);
        material.setFile_url(ossUtil.getObjectUrl(dto.getObject_key()));
        material.setFile_size(dto.getFile_size());
        material.setDescription(dto.getDescription());
        material.setAccess_type("private");
        material.setAllow_ai(0);
        material.setStatus(1);
        material.setAi_index_status("disabled");

        materialMapper.insert(material);
        log.info("confirmUpload success userId={}, materialId={}, fileType={}", userId, material.getId(), material.getFile_type());
        businessLogService.record("operation", "resource", "confirm_upload", "material", material.getId(),
                Map.of("file_name", material.getFile_name(), "file_type", material.getFile_type()));
        return toMaterialVO(material);
    }

    @Override
    public PageResult<MaterialVO> listResources(MaterialQueryDTO dto, Integer userId) {
        log.info("listResources userId={}, fileType={}, page={}, size={}", userId, dto.getFile_type(), dto.getPage(), dto.getSize());
        normalizeQuery(dto);
        dto.setUser_id(userId);
        PageHelper.startPage(dto.getPage(), dto.getSize());
        List<Res_Material> list = materialMapper.findByQuery(dto);
        PageInfo<Res_Material> info = new PageInfo<>(list);

        List<MaterialVO> records = info.getList().stream().map(this::toMaterialVO).toList();
        PageResult<MaterialVO> r = new PageResult<>();
        r.setTotal(info.getTotal());
        r.setPage(dto.getPage());
        r.setSize(dto.getSize());
        r.setRecords(records);
        return r;
    }

    @Override
    public MaterialVO getResource(Integer id, Integer userId) {
        log.info("getResource userId={}, materialId={}", userId, id);
        Res_Material m = materialMapper.findById(id);
        if (m == null || m.getStatus() != 1) throw new RuntimeException("资源不存在");
        if (!Objects.equals(m.getUser_id(), userId)) throw new RuntimeException("无权访问该资源");
        return toMaterialVO(m);
    }

    @Override
    @Transactional
    public MaterialVO updateResource(Integer id, MaterialDTO dto, Integer userId) {
        log.info("updateResource userId={}, materialId={}, allowAi={}, accessType={}", userId, id, dto.getAllow_ai(), dto.getAccess_type());
        Res_Material m = materialMapper.findById(id);
        if (m == null || m.getStatus() != 1) throw new RuntimeException("资源不存在");
        if (!Objects.equals(m.getUser_id(), userId)) throw new RuntimeException("无权修改该资源");
        validateMetadata(dto);
        applyMetadataUpdate(m, dto);
        materialMapper.update(m);
        Res_Material updated = materialMapper.findById(id);
        ensureDictionariesFromMaterial(updated);
        log.info("updateResource success userId={}, materialId={}", userId, id);
        businessLogService.record("operation", "resource", "update", "material", id);
        syncOrUpdatePersonalIndex(updated);
        return toMaterialVO(updated);
    }

    @Override
    @Transactional
    public void deleteResource(Integer id, Integer userId) {
        log.info("deleteResource userId={}, materialId={}", userId, id);
        Res_Material m = materialMapper.findById(id);
        if (m == null) throw new RuntimeException("资源不存在");
        if (!Objects.equals(m.getUser_id(), userId)) throw new RuntimeException("无权删除该资源");
        materialMapper.softDelete(id);
        deletePersonalResourceIndex(id);
        deleteOssObjectQuietly(m.getFile_url());
        log.info("deleteResource success userId={}, materialId={}", userId, id);
        businessLogService.record("operation", "resource", "delete", "material", id);
    }

    @Override
    @Transactional
    public void batchAction(ResourceBatchActionDTO dto, Integer userId) {
        log.info("batchAction userId={}, action={}, target={}", userId, dto.getAction(), dto.getTarget());
        if (dto.getAction() == null || dto.getAction().isBlank()) throw new RuntimeException("批量操作不能为空");
        List<Integer> ids = parseIds(dto.getResource_ids());
        for (Integer id : ids) {
            Res_Material m = materialMapper.findById(id);
            if (m == null || !Objects.equals(m.getUser_id(), userId)) throw new RuntimeException("资源不存在或无权操作: " + id);
            switch (dto.getAction()) {
                case "delete" -> {
                    materialMapper.softDelete(id);
                    deletePersonalResourceIndex(id);
                    deleteOssObjectQuietly(m.getFile_url());
                }
                case "allow_ai" -> {
                    m.setAllow_ai(1);
                    materialMapper.update(m);
                    syncPersonalResourceIndex(materialMapper.findById(id));
                }
                case "deny_ai" -> {
                    m.setAllow_ai(0);
                    materialMapper.update(m);
                    updatePersonalResourceAvailability(materialMapper.findById(id));
                }
                case "categorize" -> {
                    m.setCategories(normalizeTargetArray(dto.getTarget(), "target"));
                    materialMapper.update(m);
                    Res_Material updated = materialMapper.findById(id);
                    ensureDictionariesFromMaterial(updated);
                    syncOrUpdatePersonalIndex(updated);
                }
                case "tag" -> {
                    m.setTags(normalizeTargetArray(dto.getTarget(), "target"));
                    materialMapper.update(m);
                    Res_Material updated = materialMapper.findById(id);
                    ensureDictionariesFromMaterial(updated);
                    syncOrUpdatePersonalIndex(updated);
                }
                default -> throw new RuntimeException("不支持的批量操作: " + dto.getAction());
            }
        }
        log.info("batchAction success userId={}, action={}, count={}", userId, dto.getAction(), ids.size());
        businessLogService.record("operation", "resource", "batch_" + dto.getAction(), "material", null,
                Map.of("resource_ids", ids, "target", dto.getTarget() == null ? "" : dto.getTarget()));
    }

    @Override
    @Transactional
    public MaterialVO setPermission(Integer id, MaterialDTO dto, Integer userId) {
        log.info("setPermission userId={}, materialId={}, accessType={}, allowAi={}", userId, id, dto.getAccess_type(), dto.getAllow_ai());
        Res_Material m = materialMapper.findById(id);
        if (m == null || m.getStatus() != 1) throw new RuntimeException("资源不存在");
        if (!Objects.equals(m.getUser_id(), userId)) throw new RuntimeException("无权操作该资源");
        validatePermissionMetadata(dto);
        if (dto.getAccess_type() != null) m.setAccess_type(dto.getAccess_type());
        if (dto.getAuthorized_users() != null) m.setAuthorized_users(dto.getAuthorized_users());
        if (dto.getAllow_ai() != null) {
            m.setAllow_ai(dto.getAllow_ai());
        }
        materialMapper.update(m);
        syncOrUpdatePersonalIndex(materialMapper.findById(id));
        log.info("setPermission success userId={}, materialId={}, accessType={}, allowAi={}", userId, id, m.getAccess_type(), m.getAllow_ai());
        businessLogService.record("operation", "resource", "set_permission", "material", id,
                Map.of("access_type", m.getAccess_type(), "allow_ai", m.getAllow_ai()));
        return toMaterialVO(materialMapper.findById(id));
    }

    @Override
    public Map<String, Object> getDownloadUrl(Integer id, Integer userId) {
        log.info("getDownloadUrl userId={}, materialId={}", userId, id);
        Res_Material m = materialMapper.findById(id);
        if (m == null || m.getStatus() != 1) throw new RuntimeException("资源不存在");
        if (!Objects.equals(m.getUser_id(), userId)) throw new RuntimeException("无权下载该资源");

        String objectKey = ossUtil.extractObjectKey(m.getFile_url());
        URL signedUrl = ossUtil.generateDownloadUrl(objectKey, 60);

        Map<String, Object> result = new HashMap<>();
        result.put("download_url", signedUrl.toString());
        result.put("expires_at", LocalDateTime.now().plusMinutes(60));
        log.info("getDownloadUrl success userId={}, materialId={}, objectKey={}", userId, id, objectKey);
        businessLogService.record("download", "resource", "download_url", "material", id);
        return result;
    }

    @Override
    public List<Map<String, Object>> listTags(Integer userId) {
        return listDictionaryWithCounts(userId, "tag", true);
    }

    @Override
    public List<Map<String, Object>> listCategories(Integer userId) {
        return listDictionaryWithCounts(userId, "category", false);
    }

    @Override
    @Transactional
    public Map<String, Object> createTag(ResourceTaxonomyDTO dto, Integer userId) {
        return createDictionary(dto, userId, "tag", true);
    }

    @Override
    @Transactional
    public Map<String, Object> createCategory(ResourceTaxonomyDTO dto, Integer userId) {
        return createDictionary(dto, userId, "category", false);
    }

    @Override
    @Transactional
    public Map<String, Object> updateTag(Integer id, ResourceTaxonomyDTO dto, Integer userId) {
        return updateDictionary(id, dto, userId, "tag", true);
    }

    @Override
    @Transactional
    public Map<String, Object> updateCategory(Integer id, ResourceTaxonomyDTO dto, Integer userId) {
        return updateDictionary(id, dto, userId, "category", false);
    }

    @Override
    @Transactional
    public void deleteTag(Integer id, Integer userId) {
        deleteDictionary(id, userId, "tag");
    }

    @Override
    @Transactional
    public void deleteCategory(Integer id, Integer userId) {
        deleteDictionary(id, userId, "category");
    }

    private void syncOrUpdatePersonalIndex(Res_Material material) {
        if (material.getStatus() == 1 && material.getAllow_ai() == 1) {
            syncPersonalResourceIndex(material);
        } else {
            updatePersonalResourceAvailability(material);
        }
    }

    private void syncPersonalResourceIndex(Res_Material material) {
        if (material == null || material.getFile_url() == null || material.getFile_url().isBlank()) {
            return;
        }
        try {
            materialMapper.updateAiIndexStatus(material.getId(), "indexing", null);
            Map<String, Object> response = pythonPptClient.syncResourceIndex(personalResourcePayload(material, false));
            Object data = response.get("data");
            String status = extractPythonStatus(data);
            if ("failed".equals(status)) {
                materialMapper.updateAiIndexStatus(material.getId(), "failed", extractPythonError(data));
            } else {
                materialMapper.updateAiIndexStatus(material.getId(), "completed", null);
            }
        } catch (Exception e) {
            log.warn("sync personal resource index failed, materialId={}", material.getId(), e);
            materialMapper.updateAiIndexStatus(material.getId(), "failed", e.getMessage());
        }
    }

    private void updatePersonalResourceAvailability(Res_Material material) {
        if (material == null) return;
        try {
            boolean available = material.getStatus() == 1 && material.getAllow_ai() == 1;
            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("source_type", "personal");
            payload.put("resource_id", String.valueOf(material.getId()));
            payload.put("available", available);
            payload.put("allow_ai", material.getAllow_ai() == 1);
            payload.put("metadata", Map.of(
                    "owner_user_id", String.valueOf(material.getUser_id()),
                    "uploaded_by", String.valueOf(material.getUser_id()),
                    "available", available,
                    "allow_ai", material.getAllow_ai() == 1
            ));
            pythonPptClient.updateResourceIndexMetadata(payload);
            materialMapper.updateAiIndexStatus(material.getId(), available ? "completed" : "disabled", null);
        } catch (Exception e) {
            log.warn("update personal resource index metadata failed, materialId={}", material.getId(), e);
        }
    }

    private void deletePersonalResourceIndex(Integer id) {
        try {
            pythonPptClient.deleteResourceIndex("personal", id);
        } catch (Exception e) {
            log.warn("delete personal resource index failed, materialId={}", id, e);
        }
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

    private String extractPythonStatus(Object data) {
        if (data instanceof Map<?, ?> map) {
            Object status = map.get("status");
            return status == null ? "" : String.valueOf(status);
        }
        return "";
    }

    private String extractPythonError(Object data) {
        if (data instanceof Map<?, ?> map) {
            Object error = map.get("error_message");
            return error == null ? "" : String.valueOf(error);
        }
        return "";
    }

    private void normalizeQuery(MaterialQueryDTO dto) {
        if (dto == null) return;
        dto.setFile_type(blankToNull(dto.getFile_type()));
        dto.setCategory(blankToNull(dto.getCategory()));
        dto.setTag(blankToNull(dto.getTag()));
        dto.setAccess_type(blankToNull(dto.getAccess_type()));
        dto.setAi_index_status(blankToNull(dto.getAi_index_status()));
        dto.setKeyword(blankToNull(dto.getKeyword()));
        if (dto.getFile_type() != null && !FILE_TYPES.contains(dto.getFile_type())) {
            throw new RuntimeException("Unsupported file_type: " + dto.getFile_type());
        }
        if (dto.getAccess_type() != null && !ACCESS_TYPES.contains(dto.getAccess_type())) {
            throw new RuntimeException("Unsupported access_type: " + dto.getAccess_type());
        }
        if (dto.getAi_index_status() != null && !AI_INDEX_STATUSES.contains(dto.getAi_index_status())) {
            throw new RuntimeException("Unsupported ai_index_status: " + dto.getAi_index_status());
        }
        if (dto.getAllow_ai() != null && dto.getAllow_ai() != 0 && dto.getAllow_ai() != 1) {
            throw new RuntimeException("allow_ai must be 0 or 1");
        }
    }

    private void validateMetadata(MaterialDTO dto) {
        if (dto == null) throw new RuntimeException("metadata cannot be empty");
        validateJsonArrayField("categories", dto.getCategories(), true);
        validateJsonArrayField("tags", dto.getTags(), true);
        validatePermissionMetadata(dto);
    }

    private void validatePermissionMetadata(MaterialDTO dto) {
        if (dto == null) throw new RuntimeException("metadata cannot be empty");
        if (dto.getAccess_type() != null && !ACCESS_TYPES.contains(dto.getAccess_type())) {
            throw new RuntimeException("Unsupported access_type: " + dto.getAccess_type());
        }
        if (dto.getAllow_ai() != null && dto.getAllow_ai() != 0 && dto.getAllow_ai() != 1) {
            throw new RuntimeException("allow_ai must be 0 or 1");
        }
        validateJsonArrayField("authorized_users", dto.getAuthorized_users(), true);
    }

    private void applyMetadataUpdate(Res_Material material, MaterialDTO dto) {
        if (dto.getFile_name() != null) material.setFile_name(dto.getFile_name());
        if (dto.getThumbnail() != null) material.setThumbnail(dto.getThumbnail());
        if (dto.getDescription() != null) material.setDescription(dto.getDescription());
        if (dto.getCategories() != null) material.setCategories(dto.getCategories());
        if (dto.getTags() != null) material.setTags(dto.getTags());
        if (dto.getAccess_type() != null) material.setAccess_type(dto.getAccess_type());
        if (dto.getAuthorized_users() != null) material.setAuthorized_users(dto.getAuthorized_users());
        if (dto.getAllow_ai() != null) material.setAllow_ai(dto.getAllow_ai());
    }

    private void validateJsonArrayField(String field, String value, boolean optional) {
        if (value == null || value.isBlank()) {
            if (optional) return;
            throw new RuntimeException(field + " cannot be empty");
        }
        String trimmed = value.trim();
        if (!trimmed.startsWith("[")) {
            throw new RuntimeException(field + " must be a JSON array");
        }
        try {
            JSONUtil.parseArray(trimmed);
        } catch (Exception e) {
            throw new RuntimeException(field + " must be a valid JSON array: " + e.getMessage());
        }
    }

    private String normalizeTargetArray(String target, String field) {
        if (target == null || target.isBlank()) {
            throw new RuntimeException(field + " cannot be empty");
        }
        String trimmed = target.trim();
        if (trimmed.startsWith("[")) {
            validateJsonArrayField(field, trimmed, false);
            return trimmed;
        }
        JSONArray arr = new JSONArray();
        arr.add(trimmed);
        return arr.toString();
    }

    private List<Map<String, Object>> listDictionaryWithCounts(Integer userId, String dictType, boolean tags) {
        Map<String, Integer> counts = metadataCountMap(materialMapper.findByUserId(userId), tags);
        Map<String, Map<String, Object>> merged = new LinkedHashMap<>();
        for (Res_Metadata_Dictionary dictionary : dictionaryMapper.findByUserAndType(userId, dictType)) {
            Map<String, Object> item = dictionaryToMap(dictionary, counts.getOrDefault(dictionary.getName(), 0));
            item.put("managed", true);
            merged.put(dictionary.getName(), item);
        }
        for (Map.Entry<String, Integer> entry : counts.entrySet()) {
            merged.computeIfAbsent(entry.getKey(), name -> {
                Map<String, Object> item = new LinkedHashMap<>();
                item.put("id", null);
                item.put("name", name);
                item.put("type", dictType);
                item.put("count", entry.getValue());
                item.put("color", null);
                item.put("sort_order", 1000);
                item.put("managed", false);
                return item;
            });
        }
        return merged.values().stream()
                .sorted(Comparator.comparing((Map<String, Object> item) -> (Integer) item.getOrDefault("sort_order", 1000))
                        .thenComparing(item -> -((Integer) item.getOrDefault("count", 0)))
                        .thenComparing(item -> String.valueOf(item.get("name"))))
                .toList();
    }

    private Map<String, Object> createDictionary(ResourceTaxonomyDTO dto, Integer userId, String dictType, boolean tags) {
        String name = taxonomyName(dto);
        Res_Metadata_Dictionary dictionary = new Res_Metadata_Dictionary();
        dictionary.setUser_id(userId);
        dictionary.setDict_type(dictType);
        dictionary.setName(name);
        dictionary.setColor(blankToNull(dto.getColor()));
        dictionary.setSort_order(dto.getSort_order() == null ? 1000 : dto.getSort_order());
        dictionary.setUsage_count(0);
        dictionary.setStatus(1);
        dictionaryMapper.upsert(dictionary);
        Res_Metadata_Dictionary saved = dictionaryMapper.findByUserTypeName(userId, dictType, name);
        int count = metadataCountMap(materialMapper.findByUserId(userId), tags).getOrDefault(name, 0);
        return dictionaryToMap(saved, count);
    }

    private Map<String, Object> updateDictionary(Integer id, ResourceTaxonomyDTO dto, Integer userId, String dictType, boolean tags) {
        if (id == null) throw new RuntimeException("dictionary id is required");
        if (dto == null) throw new RuntimeException("dictionary data cannot be empty");
        Res_Metadata_Dictionary existing = dictionaryMapper.findById(id);
        if (existing == null || existing.getStatus() == null || existing.getStatus() != 1
                || !Objects.equals(existing.getUser_id(), userId)
                || !Objects.equals(existing.getDict_type(), dictType)) {
            throw new RuntimeException("dictionary item not found or no permission");
        }
        if (dto.getName() != null) existing.setName(taxonomyName(dto));
        if (dto.getColor() != null) existing.setColor(blankToNull(dto.getColor()));
        if (dto.getSort_order() != null) existing.setSort_order(dto.getSort_order());
        dictionaryMapper.update(existing);
        Res_Metadata_Dictionary saved = dictionaryMapper.findById(id);
        int count = metadataCountMap(materialMapper.findByUserId(userId), tags).getOrDefault(saved.getName(), 0);
        return dictionaryToMap(saved, count);
    }

    private void deleteDictionary(Integer id, Integer userId, String dictType) {
        if (id == null) throw new RuntimeException("dictionary id is required");
        if (dictionaryMapper.softDelete(id, userId, dictType) <= 0) {
            throw new RuntimeException("dictionary item not found or no permission");
        }
    }

    private void ensureDictionariesFromMaterial(Res_Material material) {
        if (material == null || material.getUser_id() == null) return;
        for (String category : metadataValues(material.getCategories())) {
            ensureDictionary(material.getUser_id(), "category", category);
        }
        for (String tag : metadataValues(material.getTags())) {
            ensureDictionary(material.getUser_id(), "tag", tag);
        }
    }

    private void ensureDictionary(Integer userId, String dictType, String name) {
        String normalized = blankToNull(name);
        if (normalized == null) return;
        Res_Metadata_Dictionary dictionary = new Res_Metadata_Dictionary();
        dictionary.setUser_id(userId);
        dictionary.setDict_type(dictType);
        dictionary.setName(normalized);
        dictionary.setSort_order(1000);
        dictionary.setUsage_count(0);
        dictionary.setStatus(1);
        dictionaryMapper.upsert(dictionary);
    }

    private String taxonomyName(ResourceTaxonomyDTO dto) {
        if (dto == null || dto.getName() == null || dto.getName().isBlank()) {
            throw new RuntimeException("name is required");
        }
        String name = dto.getName().trim();
        if (name.length() > 80) {
            throw new RuntimeException("name is too long");
        }
        return name;
    }

    private Map<String, Object> dictionaryToMap(Res_Metadata_Dictionary dictionary, int count) {
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("id", dictionary == null ? null : dictionary.getId());
        item.put("name", dictionary == null ? null : dictionary.getName());
        item.put("type", dictionary == null ? null : dictionary.getDict_type());
        item.put("count", count);
        item.put("color", dictionary == null ? null : dictionary.getColor());
        item.put("sort_order", dictionary == null || dictionary.getSort_order() == null ? 1000 : dictionary.getSort_order());
        item.put("managed", true);
        return item;
    }

    private Map<String, Integer> metadataCountMap(List<Res_Material> materials, boolean tags) {
        Map<String, Integer> counts = new LinkedHashMap<>();
        for (Res_Material material : materials) {
            String raw = tags ? material.getTags() : material.getCategories();
            for (String value : metadataValues(raw)) {
                counts.put(value, counts.getOrDefault(value, 0) + 1);
            }
        }
        return counts;
    }

    private void deleteOssObjectQuietly(String fileUrl) {
        if (fileUrl == null || fileUrl.isBlank()) return;
        try {
            ossUtil.deleteObject(ossUtil.extractObjectKey(fileUrl));
        } catch (Exception e) {
            log.warn("delete oss object failed, fileUrl={}", fileUrl, e);
        }
    }

    private List<Map<String, Object>> aggregateMetadataValues(List<Res_Material> materials, boolean tags) {
        Map<String, Integer> counts = new LinkedHashMap<>();
        for (Res_Material material : materials) {
            String raw = tags ? material.getTags() : material.getCategories();
            for (String value : metadataValues(raw)) {
                counts.put(value, counts.getOrDefault(value, 0) + 1);
            }
        }
        return counts.entrySet().stream()
                .sorted(Map.Entry.<String, Integer>comparingByValue(Comparator.reverseOrder()).thenComparing(Map.Entry.comparingByKey()))
                .map(entry -> {
                    Map<String, Object> item = new LinkedHashMap<>();
                    item.put("name", entry.getKey());
                    item.put("count", entry.getValue());
                    return item;
                })
                .toList();
    }

    private List<String> metadataValues(String raw) {
        if (raw == null || raw.isBlank()) return List.of();
        try {
            JSONArray array = JSONUtil.parseArray(raw);
            List<String> values = new ArrayList<>();
            for (Object item : array) {
                String value = String.valueOf(item == null ? "" : item).trim();
                if (!value.isBlank() && !values.contains(value)) values.add(value);
            }
            return values;
        } catch (Exception e) {
            return Arrays.stream(raw.split(","))
                    .map(String::trim)
                    .filter(value -> !value.isBlank())
                    .distinct()
                    .toList();
        }
    }

    private String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }

    private List<Integer> parseIds(String raw) {
        if (raw == null || raw.isBlank()) throw new RuntimeException("resource_ids 不能为空");
        try {
            if (raw.trim().startsWith("[")) {
                return JSONUtil.parseArray(raw).stream()
                        .map(v -> Integer.valueOf(String.valueOf(v)))
                        .toList();
            }
            return Arrays.stream(raw.split(","))
                    .map(String::trim)
                    .filter(s -> !s.isBlank())
                    .map(Integer::valueOf)
                    .toList();
        } catch (Exception e) {
            throw new RuntimeException("resource_ids 格式错误");
        }
    }

    private String detectFileType(String fileName) {
        if (fileName == null || !fileName.contains(".")) return "other";
        String ext = fileName.substring(fileName.lastIndexOf('.') + 1).toLowerCase();
        return switch (ext) {
            case "doc", "docx" -> "word";
            case "pdf" -> "pdf";
            case "ppt", "pptx" -> "ppt";
            case "txt", "md" -> "txt";
            case "jpg", "jpeg", "png", "gif", "bmp", "webp" -> "image";
            case "mp3", "wav", "aac", "ogg" -> "audio";
            case "mp4", "avi", "mov", "wmv", "flv" -> "video";
            default -> "other";
        };
    }

    private MaterialVO toMaterialVO(Res_Material m) {
        MaterialVO vo = new MaterialVO();
        BeanUtil.copyProperties(m, vo);
        return vo;
    }
}


