package edu.zstu.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

import java.util.Map;

/** 业务资源变更事件；Python 独立消费，Java 不调用任何 AI 索引 API。 */
@Component
@RequiredArgsConstructor
@Slf4j
public class ResourceIndexEventPublisher {
    public static final String STREAM = "a12:resource-index:events";
    private final StringRedisTemplate redisTemplate;
    private final ResourceIndexFailureRecorder failures;

    public void publish(String action, String sourceType, Integer resourceId, boolean forceReparse) {
        if (resourceId == null) return;
        Runnable write = () -> {
            try {
                redisTemplate.opsForStream().add(STREAM, Map.of(
                        "action", action,
                        "source_type", sourceType,
                        "resource_id", String.valueOf(resourceId),
                        "force_reparse", String.valueOf(forceReparse)
                ));
            } catch (RuntimeException e) {
                if ("sync".equals(action)) {
                    try {
                        failures.record(sourceType, resourceId,
                                "索引事件发布失败，请检查 Redis 连接及 Streams 支持（Redis 5+），恢复后重新同步索引");
                    } catch (RuntimeException recordError) {
                        log.error("无法保存资源索引失败状态 source={} id={}", sourceType, resourceId, recordError);
                    }
                }
                log.error("资源索引事件发布失败 source={} id={}；业务状态已保存，等待后台重建索引", sourceType, resourceId, e);
            }
        };
        if (TransactionSynchronizationManager.isActualTransactionActive()) {
            TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
                @Override public void afterCommit() { write.run(); }
            });
        } else {
            write.run();
        }
    }
}
