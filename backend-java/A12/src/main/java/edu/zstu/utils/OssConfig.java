package edu.zstu.utils;

import com.aliyun.oss.ClientBuilderConfiguration;
import com.aliyun.oss.OSS;
import com.aliyun.oss.OSSClientBuilder;
import com.aliyun.oss.common.comm.SignVersion;
import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Data
@Configuration
@ConfigurationProperties(prefix = "aliyun.oss")
public class OssConfig {
    private String endpoint;
    private String accessKeyId;
    private String accessKeySecret;
    private String bucketName;

    @Bean
    public OSS ossClient() {
        String region = "cn-hangzhou";

        ClientBuilderConfiguration clientBuilderConfiguration = new ClientBuilderConfiguration();
        clientBuilderConfiguration.setSignatureVersion(SignVersion.V4);

        return OSSClientBuilder.create()
                .endpoint(endpoint)
                .credentialsProvider(new com.aliyun.oss.common.auth.DefaultCredentialProvider(accessKeyId, accessKeySecret))
                .clientConfiguration(clientBuilderConfiguration)
                .region(region)
                .build();
    }
}
