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
            newConfig.setStatus("published");
            configMapper.insert(newConfig);
        }
    }


    public String hash(String password) {
        try {
            Mac mac = Mac.getInstance(HMAC_ALGORITHM);
            SecretKeySpec keySpec = new SecretKeySpec(secretKey.getBytes(), HMAC_ALGORITHM);
            mac.init(keySpec);
            return HexFormat.of().formatHex(mac.doFinal(password.getBytes()));
        } catch (Exception e) {
            throw new RuntimeException("hash密码出错", e);
        }
    }
}
