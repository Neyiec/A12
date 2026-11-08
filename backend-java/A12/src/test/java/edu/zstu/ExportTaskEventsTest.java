package edu.zstu;

import edu.zstu.service.ExportTaskEvents;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.transaction.support.TransactionSynchronizationManager;

import static org.mockito.Mockito.*;

class ExportTaskEventsTest {
    @Test
    void listenersOnlySeeCommittedTaskChanges() {
        var redis = mock(StringRedisTemplate.class);
        var events = new ExportTaskEvents(redis);
        TransactionSynchronizationManager.initSynchronization();
        try {
            events.changed(7, 31);
            verifyNoInteractions(redis);
            TransactionSynchronizationManager.getSynchronizations().forEach(sync -> sync.afterCommit());
            verify(redis).convertAndSend(ExportTaskEvents.CHANNEL, "7:31");
        } finally {
            TransactionSynchronizationManager.clearSynchronization();
        }
    }
}
