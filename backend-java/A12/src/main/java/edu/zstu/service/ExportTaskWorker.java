package edu.zstu.service;

import edu.zstu.service.impl.ExportServiceImpl;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Slf4j
@Component
public class ExportTaskWorker {
    private final RedisExportTaskQueue queue;
    private final ExportServiceImpl exportService;

    public ExportTaskWorker(RedisExportTaskQueue queue, ExportServiceImpl exportService) {
        this.queue = queue; this.exportService = exportService;
    }

    @Scheduled(fixedDelayString = "${a12.export.queue-poll-ms:500}")
    public void consumeOne() {
        String taskId = queue.claim();
        if (taskId == null || taskId.isBlank()) return;
        if (!queue.acquireTaskLock(taskId)) { queue.discardDuplicateClaim(taskId); return; }
        try { exportService.processQueuedTask(Integer.parseInt(taskId)); }
        catch (Exception e) { log.warn("Queued export execution failed, taskId={}", taskId, e); }
        finally { queue.acknowledge(taskId); }
    }

    @Scheduled(initialDelay = 60_000L, fixedDelay = 60_000L)
    public void recoverStaleTasks() {
        int count = queue.recoverStaleClaims();
        if (count > 0) log.info("Recovered {} stale export task(s)", count);
    }
}
