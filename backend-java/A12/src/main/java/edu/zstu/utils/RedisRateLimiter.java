package edu.zstu.utils;

import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.time.Duration;

@Component
public class RedisRateLimiter {
    private final StringRedisTemplate redisTemplate;

    public RedisRateLimiter(StringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    public void assertWithinLimit(String key, int maxRequests, Duration window, String message) {
        Long count = redisTemplate.opsForValue().increment(key);
        if (count != null && count == 1) {
            redisTemplate.expire(key, window);
        }
        if (count != null && count > maxRequests) {
            throw new RuntimeException(message);
        }
    }

    public void assertCooldown(String key, Duration cooldown, String message) {
        Boolean allowed = redisTemplate.opsForValue().setIfAbsent(key, "1", cooldown);
        if (!Boolean.TRUE.equals(allowed)) {
            throw new RuntimeException(message);
        }
    }
}
