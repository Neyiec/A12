package edu.zstu.utils;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.data.redis.core.Cursor;
import org.springframework.data.redis.core.ScanOptions;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;
import lombok.extern.slf4j.Slf4j;

import java.time.Duration;
import java.util.HashSet;
import java.util.Set;
import java.util.function.Supplier;

@Slf4j
@Component
public class RedisCacheUtil {
    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper;

    public RedisCacheUtil(StringRedisTemplate redisTemplate, ObjectMapper objectMapper) {
        this.redisTemplate = redisTemplate;
        this.objectMapper = objectMapper;
    }

    public <T> T getOrLoad(String key, TypeReference<T> type, Duration ttl, Supplier<T> loader) {
        String cached = redisTemplate.opsForValue().get(key);
        if (cached != null) {
            try {
                return objectMapper.readValue(cached, type);
            } catch (Exception ignored) {
                log.warn("redis cache deserialize failed, key={}", key, ignored);
                redisTemplate.delete(key);
            }
        }
        T value = loader.get();
        put(key, value, ttl);
        return value;
    }

    public <T> T getOrLoad(String key, Class<T> type, Duration ttl, Supplier<T> loader) {
        String cached = redisTemplate.opsForValue().get(key);
        if (cached != null) {
            try {
                return objectMapper.readValue(cached, type);
            } catch (Exception ignored) {
                log.warn("redis cache deserialize failed, key={}", key, ignored);
                redisTemplate.delete(key);
            }
        }
        T value = loader.get();
        put(key, value, ttl);
        return value;
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
