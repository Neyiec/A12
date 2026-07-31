package edu.zstu.service.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.json.JSONUtil;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import edu.zstu.dto.MaterialDTO;
import edu.zstu.dto.MaterialQueryDTO;
import edu.zstu.dto.ResourceBatchActionDTO;
import edu.zstu.dto.ResourceUploadConfirmDTO;
import edu.zstu.dto.UploadTokenDTO;
import edu.zstu.entity.Res_Material;
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
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Slf4j
@Service
public class ResourceServiceImpl implements ResourceService {

    private final ResMaterialMapper materialMapper;
    private final OssUtil ossUtil;
    private final BusinessLogService businessLogService;
    private final PythonPptClient pythonPptClient;

    public ResourceServiceImpl(ResMaterialMapper materialMapper, OssUtil ossUtil,
                               BusinessLogService businessLogService,
                               PythonPptClient pythonPptClient) {
        this.materialMapper = materialMapper;
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
            if (old == null || old.getUser_id() != userId) {
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
        if (m.getUser_id() != userId) throw new RuntimeException("无权访问该资源");
        return toMaterialVO(m);
    }

    @Override
    @Transactional
    public MaterialVO updateResource(Integer id, MaterialDTO dto, Integer userId) {
        log.info("updateResource userId={}, materialId={}, allowAi={}, accessType={}", userId, id, dto.getAllow_ai(), dto.getAccess_type());
        Res_Material m = materialMapper.findById(id);
        if (m == null || m.getStatus() != 1) throw new RuntimeException("资源不存在");
        if (m.getUser_id() != userId) throw new RuntimeException("无权修改该资源");
        BeanUtil.copyProperties(dto, m, "id", "user_id", "file_url", "file_type", "file_size", "status",
                "ai_index_status", "ai_indexed_at", "ai_index_error");
        materialMapper.update(m);
        log.info("updateResource success userId={}, materialId={}", userId, id);
        businessLogService.record("operation", "resource", "update", "material", id);
        syncOrUpdatePersonalIndex(m);
        return toMaterialVO(materialMapper.findById(id));
    }

    @Override
    @Transactional
    public void deleteResource(Integer id, Integer userId) {
        log.info("deleteResource userId={}, materialId={}", userId, id);
        Res_Material m = materialMapper.findById(id);
        if (m == null) throw new RuntimeException("资源不存在");
        if (m.getUser_id() != userId) throw new RuntimeException("无权删除该资源");
        materialMapper.softDelete(id);
        deletePersonalResourceIndex(id);
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
            if (m == null || m.getUser_id() != userId) throw new RuntimeException("资源不存在或无权操作: " + id);
            switch (dto.getAction()) {
                case "delete" -> {
                    materialMapper.softDelete(id);
                    deletePersonalResourceIndex(id);
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
        if (m.getUser_id() != userId) throw new RuntimeException("无权操作该资源");
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
        if (m.getUser_id() != userId) throw new RuntimeException("无权下载该资源");

        String objectKey = ossUtil.extractObjectKey(m.getFile_url());
        URL signedUrl = ossUtil.generateDownloadUrl(objectKey, 60);

        Map<String, Object> result = new HashMap<>();
        result.put("download_url", signedUrl.toString());
        result.put("expires_at", LocalDateTime.now().plusMinutes(60));
        log.info("getDownloadUrl success userId={}, materialId={}, objectKey={}", userId, id, objectKey);
        businessLogService.record("download", "resource", "download_url", "material", id);
        return result;
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


