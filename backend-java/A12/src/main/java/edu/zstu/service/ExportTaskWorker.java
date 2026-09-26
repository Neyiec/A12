package edu.zstu.service;

import edu.zstu.service.impl.ExportServiceImpl;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/** 消费 Redis 导出队列。多个 Java 实例部署时由任务锁保证同一任务只执行一次。 */
@Slf4j
@Component
public class ExportTaskWorker {
    private final RedisExportTaskQueue queue;
    private final ExportServiceImpl exportService;

    public ExportTaskWorker(RedisExportTaskQueue queue, ExportServiceImpl exportService) {
        this.queue = queue;
        this.exportService = exportService;
    }

    @Scheduled(fixedDelayString = "${a12.export.queue-poll-ms:500}")
    public void consumeOne() {
        String taskId = queue.claim();
        if (taskId == null || taskId.isBlank()) return;
        if (!queue.acquireTaskLock(taskId)) {
            queue.discardDuplicateClaim(taskId);
            return;
        }
        try {
            exportService.processQueuedTask(Integer.parseInt(taskId));
        } catch (Exception e) {
            log.warn("Queued export execution failed, taskId={}", taskId, e);
        } finally {
            queue.acknowledge(taskId);
        }
    }

    @Scheduled(initialDelay = 60_000L, fixedDelay = 60_000L)
    public void recoverStaleTasks() {
        int recovered = queue.recoverStaleClaims();
        if (recovered > 0) log.info("Recovered {} stale export task(s)", recovered);
    }
}
