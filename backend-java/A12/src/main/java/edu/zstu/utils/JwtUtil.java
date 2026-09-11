package edu.zstu.utils;

import cn.hutool.core.util.RandomUtil;
import edu.zstu.entity.Sys_Config;
import edu.zstu.mapper.SysConfigMapper;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtBuilder;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import jakarta.annotation.PostConstruct;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.util.Date;
import java.util.Map;
import java.util.UUID;

/**
 * JWT 工具类
 * 生成和解析登录令牌，密钥存储在 sys_config 表
 * (config_group = security, config_key = jwt.secret)
 * 首次启动自动生成 32 字节随机密钥并持久化
 * JWT 与 Redis 会话均使用固定 12 小时有效期
 */
@Component
public class JwtUtil {

    public static final long TOKEN_VALIDITY_HOURS = 12;

    private static final String CONFIG_GROUP = "security";
    private static final String CONFIG_KEY = "jwt.secret";
    private final SysConfigMapper configMapper;
    private SecretKey secretKey;

    public JwtUtil(SysConfigMapper configMapper) {
        this.configMapper = configMapper;
    }


    @PostConstruct
    public void init() {
        Sys_Config config = configMapper.findByGroupAndKey(CONFIG_GROUP, CONFIG_KEY);
        String keyStr;
        if (config != null) {
            keyStr = config.getConfig_value();
        } else {
            keyStr = RandomUtil.randomString(64);

            Sys_Config newConfig = new Sys_Config();
            newConfig.setConfig_group(CONFIG_GROUP);
            newConfig.setConfig_key(CONFIG_KEY);
            newConfig.setConfig_value(keyStr);
            newConfig.setDescription("JWT HMAC-SHA256签名密钥（自动生成）");
            newConfig.setUpdated_by(0);
            newConfig.setUpdated_at(LocalDateTime.now());
            newConfig.setStatus("published");
            configMapper.insert(newConfig);
        }
        this.secretKey = Keys.hmacShaKeyFor(keyStr.getBytes(StandardCharsets.UTF_8));
    }

    /**
     * 生成带固定 12 小时 exp 的 JWT 令牌
     */
    public String generateToken(Map<String, Object> claims) {
        var builder = Jwts.builder();
        claims.forEach(builder::claim);
        builder.id(UUID.randomUUID().toString());
        builder.issuedAt(new Date());
        builder.expiration(new Date(System.currentTimeMillis() + TOKEN_VALIDITY_HOURS * 60 * 60 * 1000));
        return builder.signWith(secretKey).compact();
    }

    /**
     * 解析 JWT 令牌，只校验签名；返回全部 Claims，签名无效返回 null
     */
    public Claims parseToken(String token) {
        try {
            return Jwts.parser()
                    .verifyWith(secretKey)
                    .build()
                    .parseSignedClaims(token)
                    .getPayload();

        } catch (Exception e) {
            return null;
        }
    }
}
