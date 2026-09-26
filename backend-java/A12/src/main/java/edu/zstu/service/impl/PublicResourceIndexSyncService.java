package edu.zstu.service.impl;

import edu.zstu.mapper.AdmResourceMapper;
import edu.zstu.service.PythonPptClient;
import edu.zstu.service.KafkaEventPublisher;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

import java.util.Map;
import java.util.concurrent.Executor;

/**
 * [数据交互说明]
 * - 导出:
 *   - `AdmResourceMapper`: 回写 MySQL `adm_resource.ai_index_status` / `ai_index_error`
 *   - `PythonPptClient`: HTTP 调用 Python 资源索引同步接口（下载/解析/向量化）
 * - 依赖:
 *   - 调用方（AdminResourceServiceImpl）在事务内组装好 public 载荷（含 60min 预签名 file_url）后派发
 * - 输入: 资源 ID + 已组装的 Python 同步载荷
 * - 输出: 异步完成索引同步并把最终状态（completed/failed）回写 MySQL；无返回值
 *
 * 公共资源 AI 索引异步同步服务（镜像个人素材侧 ResourceIndexSyncService 模式）。
 * 事务方法（completeUpload/updateResource/reparseResource）只把 ai_index_status 置为 indexing 后立即返回，
 * 本类在 resourceIndexExecutor 线程池中执行耗时的 Python 下载/解析/向量化调用，
 * 避免同步等待导致前端超时断连与事务连接长期占用（2026-09-15 修复）。
 */
@Slf4j
@Service
public class PublicResourceIndexSyncService {

    private final AdmResourceMapper resourceMapper;
    private final PythonPptClient pythonPptClient;
    private final KafkaEventPublisher kafkaEventPublisher;
    private final Executor resourceIndexExecutor;

    public PublicResourceIndexSyncService(AdmResourceMapper resourceMapper, PythonPptClient pythonPptClient,
                                          KafkaEventPublisher kafkaEventPublisher,
                                          @Qualifier("resourceIndexExecutor") Executor resourceIndexExecutor) {
        this.resourceMapper = resourceMapper;
        this.pythonPptClient = pythonPptClient;
        this.kafkaEventPublisher = kafkaEventPublisher;
        this.resourceIndexExecutor = resourceIndexExecutor;
    }

    /**
     * 异步同步公共资源索引。
     * 前置条件：调用方已在事务内把 MySQL `ai_index_status` 标记为 indexing 并组装好载荷。
     * Python 侧返回 failed 时把 error_message 写入 `ai_index_error`。
     * @param resourceId 资源 ID（= adm_resource.id）
     * @param payload    AdminResourceServiceImpl.publicResourcePayload 组装的同步载荷
     */
    public void syncPublicResourceIndex(Integer resourceId, Map<String, Object> payload) {
        dispatchAfterCommit(() -> doSyncPublicResourceIndex(resourceId, payload));
    }

    private void doSyncPublicResourceIndex(Integer resourceId, Map<String, Object> payload) {
        resourceMapper.updateAiIndexStatus(resourceId, "indexing", null);
        try {
            log.info("async sync public resource index start, resourceId={}", resourceId);
            if (kafkaEventPublisher.publishResourceIndex(payload).accepted()) {
                log.info("public resource index event published, resourceId={}", resourceId);
                return;
            }
            Map<String, Object> response = pythonPptClient.syncResourceIndex(payload);
            Object data = response.get("data");
            String status = extractPythonStatus(data);
            if ("failed".equals(status)) {
                resourceMapper.updateAiIndexStatus(resourceId, "failed", extractPythonError(data));
                log.warn("async sync public resource index failed, resourceId={}, error={}", resourceId, extractPythonError(data));
            } else {
                resourceMapper.updateAiIndexStatus(resourceId, "completed", null);
                log.info("async sync public resource index completed, resourceId={}", resourceId);
            }
        } catch (Exception e) {
            log.warn("async sync public resource index failed, resourceId={}", resourceId, e);
            resourceMapper.updateAiIndexStatus(resourceId, "failed", e.getMessage());
        }
    }

    private void dispatchAfterCommit(Runnable task) {
        Runnable dispatch = () -> resourceIndexExecutor.execute(task);
        if (TransactionSynchronizationManager.isActualTransactionActive()) {
            TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
                @Override public void afterCommit() { dispatch.run(); }
            });
        } else {
            dispatch.run();
        }
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
