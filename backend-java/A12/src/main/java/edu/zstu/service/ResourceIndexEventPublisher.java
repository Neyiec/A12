package edu.zstu.service;

import lombok.RequiredArgsConstructor;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

import java.util.Map;

/** 业务资源变更事件；Python 独立消费，Java 不调用任何 AI 索引 API。 */
@Component
@RequiredArgsConstructor
public class ResourceIndexEventPublisher {
    public static final String STREAM = "a12:resource-index:events";
    private final StringRedisTemplate redisTemplate;

    public void publish(String action, String sourceType, Integer resourceId, boolean forceReparse) {
        if (resourceId == null) return;
        Runnable write = () -> redisTemplate.opsForStream().add(STREAM, Map.of(
                "action", action,
                "source_type", sourceType,
                "resource_id", String.valueOf(resourceId),
                "force_reparse", String.valueOf(forceReparse)
        ));
        if (TransactionSynchronizationManager.isActualTransactionActive()) {
            TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
                @Override public void afterCommit() { write.run(); }
            });
        } else {
            write.run();
        }
    }
}
