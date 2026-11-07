package edu.zstu.utils;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JavaType;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.data.redis.core.Cursor;
import org.springframework.data.redis.core.ScanOptions;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.dao.DataAccessException;
import org.springframework.stereotype.Component;
import lombok.extern.slf4j.Slf4j;

import java.time.Duration;
import java.util.HashSet;
import java.util.Set;
import java.util.concurrent.ThreadLocalRandom;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.locks.ReentrantLock;
import java.util.function.Supplier;

@Slf4j
@Component
public class RedisCacheUtil {
    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper;
    private final ReentrantLock[] loadLocks = new ReentrantLock[128];

    public RedisCacheUtil(StringRedisTemplate redisTemplate, ObjectMapper objectMapper) {
        this.redisTemplate = redisTemplate;
        this.objectMapper = objectMapper;
        for (int i = 0; i < loadLocks.length; i++) loadLocks[i] = new ReentrantLock();
    }

    public <T> T getOrLoad(String key, TypeReference<T> type, Duration ttl, Supplier<T> loader) {
        return loadCached(key, objectMapper.constructType(type), ttl, loader);
    }

    public <T> T getOrLoad(String key, Class<T> type, Duration ttl, Supplier<T> loader) {
        return loadCached(key, objectMapper.constructType(type), ttl, loader);
    }

    private <T> T loadCached(String key, JavaType type, Duration ttl, Supplier<T> loader) {
        T cached;
        try {
            cached = read(key, type);
        } catch (DataAccessException e) {
            log.debug("redis cache read unavailable, type={}", e.getClass().getSimpleName());
            return loader.get();
        }
        if (cached != null) return cached;

        ReentrantLock lock = loadLocks[Math.floorMod(key.hashCode(), loadLocks.length)];
        try {
            if (!lock.tryLock(250, TimeUnit.MILLISECONDS)) return loader.get();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("缓存回源等待已中断", e);
        }
        try {
            try {
                cached = read(key, type);
            } catch (DataAccessException e) {
                log.debug("redis cache recheck unavailable, type={}", e.getClass().getSimpleName());
                return loader.get();
            }
            if (cached != null) return cached;
            T loaded = loader.get();
            long jitterMs = Math.max(0, ttl.toMillis() / 10);
            if (loaded != null) put(key, loaded, ttl.minusMillis(ThreadLocalRandom.current().nextLong(jitterMs + 1)));
            return loaded;
        } finally {
            lock.unlock();
        }
    }

    private <T> T read(String key, JavaType type) {
        String cached = redisTemplate.opsForValue().get(key);
        if (cached == null) return null;
        try {
            return objectMapper.readValue(cached, type);
        } catch (JsonProcessingException e) {
            log.debug("redis cache entry cannot be decoded, type={}", e.getClass().getSimpleName());
            return null;
        }
    }

    public void put(String key, Object value, Duration ttl) {
        try {
            redisTemplate.opsForValue().set(key, objectMapper.writeValueAsString(value), ttl);
            log.debug("redis cache put key={}, ttlSeconds={}", key, ttl.toSeconds());
        } catch (Exception ignored) {
            log.warn("redis cache put failed, key={}", key, ignored);
        }
    }

    public void delete(String key) {
        redisTemplate.delete(key);
    }

    public void deleteByPattern(String pattern) {
        Set<String> keys = keysByPattern(pattern);
        if (!keys.isEmpty()) {
            redisTemplate.delete(keys);
            log.info("redis cache deleteByPattern pattern={}, count={}", pattern, keys.size());
        }
    }

    public Set<String> keysByPattern(String pattern) {
        Set<String> keys = new HashSet<>();
        ScanOptions options = ScanOptions.scanOptions().match(pattern).count(500).build();
        try (Cursor<String> cursor = redisTemplate.scan(options)) {
            while (cursor.hasNext()) {
                keys.add(cursor.next());
            }
        }
        return keys;
    }
}
