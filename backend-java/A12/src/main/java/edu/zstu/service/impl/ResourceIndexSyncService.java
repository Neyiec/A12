package edu.zstu.service.impl;

import edu.zstu.entity.Res_Material;
import edu.zstu.mapper.ResMaterialMapper;
import edu.zstu.service.PythonPptClient;
import edu.zstu.utils.OssUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * [数据交互说明]
 * - 导出:
 *   - `ResMaterialMapper`: 回写 MySQL `res_material.ai_index_status` / `ai_index_error`
 *   - `PythonPptClient`: HTTP 调用 Python 资源索引同步/元数据接口
 * - 依赖:
 *   - `OssUtil`: 生成 60 分钟 OSS 预签名下载 URL
 * - 输入: 接收 `ResourceServiceImpl` 事务方法传入的已更新 `Res_Material` 实体（内存对象，不回查库）
 * - 输出: 异步完成索引同步并把最终状态（completed/failed）回写 MySQL；无返回值
 *
 * 个人素材 AI 索引异步同步服务。
 * 事务方法（setPermission/updateResource/batchAction）只做状态标记后立即返回，
 * 本类在 resourceIndexExecutor 线程池中执行耗时的 Python 下载/解析/向量化调用，
 * 避免阻塞前端 HTTP 响应。
 */
@Slf4j
@Service
public class ResourceIndexSyncService {

    private final ResMaterialMapper materialMapper;
    private final PythonPptClient pythonPptClient;
    private final OssUtil ossUtil;

    public ResourceIndexSyncService(ResMaterialMapper materialMapper, PythonPptClient pythonPptClient, OssUtil ossUtil) {
        this.materialMapper = materialMapper;
        this.pythonPptClient = pythonPptClient;
        this.ossUtil = ossUtil;
    }

    /**
     * 异步同步个人素材索引（启用 AI 引用时调用）。
     * 前置条件：调用方已把 MySQL `ai_index_status` 标记为 indexing 并提交事务。
     * Python 侧返回 failed 时把错误信息写入 `ai_index_error`。
     */
    @Async("resourceIndexExecutor")
    public void syncPersonalResourceIndex(Res_Material material) {
        syncPersonalResourceIndex(material, false);
    }

    /**
     * 异步同步个人素材索引（可指定 force_reparse）。
     * force_reparse=true 用于管理端「重解析/重试」：绕过 file_fingerprint 短路，强制重新解析并重建向量。
     */
    @Async("resourceIndexExecutor")
    public void syncPersonalResourceIndex(Res_Material material, boolean forceReparse) {
        if (material == null || material.getFile_url() == null || material.getFile_url().isBlank()) {
            return;
        }

        try {
            Map<String, Object> response = pythonPptClient.syncResourceIndex(personalResourcePayload(material, forceReparse));
            Object data = response.get("data");
            String status = extractPythonStatus(data);
            if ("failed".equals(status)) {
                materialMapper.updateAiIndexStatus(material.getId(), "failed", extractPythonError(data));
            } else {
                materialMapper.updateAiIndexStatus(material.getId(), "completed", null);
            }
        } catch (Exception e) {
            log.warn("async sync personal resource index failed, materialId={}", material.getId(), e);
            materialMapper.updateAiIndexStatus(material.getId(), "failed", e.getMessage());
        }
    }

    /**
     * 异步更新个人素材索引可用性（关闭 AI 引用等场景）。
     * 仅 PATCH Python 元数据（available/allow_ai），不触发重新解析；MySQL 状态由调用方提前置为 disabled。
     */
    @Async("resourceIndexExecutor")
    public void updatePersonalResourceAvailability(Res_Material material) {
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
        } catch (Exception e) {
            log.warn("async update personal resource index metadata failed, materialId={}", material.getId(), e);
        }
    }

    /** 构建 Python 资源索引同步载荷（file_url 为 60 分钟预签名下载 URL） */
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

    /** 从 Python 响应 data 中提取 status 字段 */
    private String extractPythonStatus(Object data) {
        if (data instanceof Map<?, ?> map) {
            Object status = map.get("status");
            return status == null ? "" : String.valueOf(status);
        }
        return "";
    }

    /** 从 Python 响应 data 中提取 error_message 字段 */
    private String extractPythonError(Object data) {
        if (data instanceof Map<?, ?> map) {
            Object error = map.get("error_message");
            return error == null ? "" : String.valueOf(error);
        }
        return "";
    }
}
