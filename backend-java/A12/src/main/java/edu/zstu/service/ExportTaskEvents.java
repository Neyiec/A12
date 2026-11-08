package edu.zstu.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

@Component
@RequiredArgsConstructor
@Slf4j
public class ExportTaskEvents {
    public static final String CHANNEL = "a12:events:export";
    private final StringRedisTemplate redis;

    public void changed(int owner, int taskId) {
        if (TransactionSynchronizationManager.isSynchronizationActive()) {
            TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
                @Override
                public void afterCommit() {
                    publish(owner, taskId);
                }
            });
        } else {
            publish(owner, taskId);
        }
    }

    private void publish(int owner, int taskId) {
        try {
            redis.convertAndSend(CHANNEL, owner + ":" + taskId);
        } catch (RuntimeException e) {
            log.warn("Export notification unavailable taskId={} type={}", taskId, e.getClass().getSimpleName());
        }
    }
}
