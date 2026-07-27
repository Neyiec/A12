package edu.zstu.utils;

import edu.zstu.entity.Sys_Config;
import edu.zstu.mapper.SysConfigMapper;
import jakarta.annotation.PostConstruct;
import org.springframework.stereotype.Component;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.security.SecureRandom;
import java.time.LocalDateTime;
import java.util.HexFormat;

/**
 * 密码工具类
 * 使用 HMAC-SHA256 对密码进行哈希，密钥存储在 sys_config 表中
 * (config_group = security, config_key = password.secret)
 * 首次启动自动生成 32 字节随机密钥并持久化
 */
@Component
public class PasswordUtil {

    private static final String CONFIG_GROUP = "security";
    private static final String CONFIG_KEY = "password.secret";
    private static final String HMAC_ALGORITHM = "HmacSHA256";

    private final SysConfigMapper configMapper;
    private volatile String secretKey;

    public PasswordUtil(SysConfigMapper configMapper) {
        this.configMapper = configMapper;
    }

    @PostConstruct
    public void init() {
        Sys_Config config = configMapper.findByGroupAndKey(CONFIG_GROUP, CONFIG_KEY);
        if (config != null) {
            secretKey = config.getConfig_value();
        } else {
            SecureRandom random = new SecureRandom();
            byte[] bytes = new byte[32];
            random.nextBytes(bytes);
            secretKey = HexFormat.of().formatHex(bytes);

            Sys_Config newConfig = new Sys_Config();
            newConfig.setConfig_group(CONFIG_GROUP);
            newConfig.setConfig_key(CONFIG_KEY);
            newConfig.setConfig_value(secretKey);
            newConfig.setDescription("密码HMAC-SHA256密钥（自动生成）");
            newConfig.setUpdated_by(0);
            newConfig.setUpdated_at(LocalDateTime.now());
            configMapper.insert(newConfig);
        }
    }

    /**
     * 使用 HMAC-SHA256 对明文密码进行哈希
     */
    public String hash(String password) {
        try {
            Mac mac = Mac.getInstance(HMAC_ALGORITHM);
            SecretKeySpec keySpec = new SecretKeySpec(secretKey.getBytes(), HMAC_ALGORITHM);
            mac.init(keySpec);
            return HexFormat.of().formatHex(mac.doFinal(password.getBytes()));
        } catch (Exception e) {
            throw new RuntimeException("密码加密失败", e);
        }
    }
}
