package edu.zstu.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

import java.util.Map;

/** 仅发布业务事件；AI 审核由 Python 消费，事件在事务提交后写入。 */
@Component
@RequiredArgsConstructor
@Slf4j
public class CommunityReviewEventPublisher {
    public static final String STREAM = "a12:community-review:events";
    private final StringRedisTemplate redisTemplate;

    public void publish(int auditId, int contentVersion) {
        Runnable write = () -> {
            try {
                redisTemplate.opsForStream().add(STREAM, Map.of(
                        "audit_id", String.valueOf(auditId),
                        "content_version", String.valueOf(contentVersion)
                ));
            } catch (RuntimeException e) {
                // 投稿事务已经成功；事件不可用时保持人工待审，不能误报投稿失败或自动放行。
                log.error("社区 AI 审核事件发布失败 auditId={}，保留人工待审", auditId, e);
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
