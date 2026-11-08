package edu.zstu.service;

import org.junit.jupiter.api.Test;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.StreamOperations;
import org.springframework.transaction.support.TransactionSynchronizationManager;

import static org.mockito.Mockito.*;

class ResourceIndexEventPublisherTest {
    @Test
    @SuppressWarnings("unchecked")
    void failedPublicationAfterCommitPersistsFailureInsteadOfLeavingIndexing() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        StreamOperations<String, Object, Object> stream = mock(StreamOperations.class);
        when(redis.opsForStream()).thenReturn(stream);
        when(stream.add(anyString(), anyMap())).thenThrow(new IllegalStateException("ERR unknown command XADD"));
        ResourceIndexFailureRecorder failures = mock(ResourceIndexFailureRecorder.class);
        ResourceIndexEventPublisher publisher = new ResourceIndexEventPublisher(redis, failures);
        TransactionSynchronizationManager.setActualTransactionActive(true);
        TransactionSynchronizationManager.initSynchronization();
        try {
            publisher.publish("sync", "public", 7, false);
            verifyNoInteractions(failures);
            TransactionSynchronizationManager.getSynchronizations().forEach(s -> s.afterCommit());
            verify(failures).record(eq("public"), eq(7), contains("Redis 5+"));
            publisher.publish("delete", "public", 7, false);
            TransactionSynchronizationManager.getSynchronizations().get(1).afterCommit();
            verifyNoMoreInteractions(failures);
        } finally {
            TransactionSynchronizationManager.clearSynchronization();
            TransactionSynchronizationManager.setActualTransactionActive(false);
        }
    }
}
