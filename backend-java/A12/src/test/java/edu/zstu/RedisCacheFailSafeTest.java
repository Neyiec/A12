package edu.zstu;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.zstu.utils.RedisCacheUtil;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.RedisConnectionFailureException;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;

import java.time.Duration;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class RedisCacheFailSafeTest {
    private final StringRedisTemplate redis = mock(StringRedisTemplate.class);
    @SuppressWarnings("unchecked")
    private final ValueOperations<String, String> values = mock(ValueOperations.class);
    private final RedisCacheUtil cache = new RedisCacheUtil(redis, new ObjectMapper());
    private final Duration ttl = Duration.ofMinutes(1);

    @Test
    void redisReadFailureFallsBackButDatabaseFailureStillPropagates() {
        when(redis.opsForValue()).thenReturn(values);
        when(values.get("read")).thenThrow(new RedisConnectionFailureException("unavailable"));
        assertEquals("from-db", cache.getOrLoad("read", String.class, ttl, () -> "from-db"));
        assertThrows(IllegalStateException.class, () -> cache.getOrLoad("read", String.class, ttl, () -> {
            throw new IllegalStateException("database failed");
        }));
    }

    @Test
    void concurrentSameKeyMissReusesFirstLoad() throws Exception {
        when(redis.opsForValue()).thenReturn(values);
        AtomicReference<String> stored = new AtomicReference<>();
        CountDownLatch enteredLoader = new CountDownLatch(1);
        CountDownLatch secondRead = new CountDownLatch(1);
        when(values.get("shared")).thenAnswer(invocation -> {
            if (enteredLoader.getCount() == 0) secondRead.countDown();
            return stored.get();
        });
        doAnswer(invocation -> {
            stored.set(invocation.getArgument(1));
            return null;
        }).when(values).set(eq("shared"), anyString(), any(Duration.class));

        var pool = Executors.newFixedThreadPool(2);
        try {
            var first = pool.submit(() -> cache.getOrLoad("shared", String.class, ttl, () -> {
                enteredLoader.countDown();
                try {
                    assertTrue(secondRead.await(2, TimeUnit.SECONDS));
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    throw new AssertionError(e);
                }
                return "first";
            }));
            assertTrue(enteredLoader.await(2, TimeUnit.SECONDS));
            var second = pool.submit(() -> cache.getOrLoad("shared", String.class, ttl,
                    () -> fail("the second request should reuse the cached value")));
            assertEquals("first", first.get(2, TimeUnit.SECONDS));
            assertEquals("first", second.get(2, TimeUnit.SECONDS));
        } finally {
            pool.shutdownNow();
        }
    }
}
