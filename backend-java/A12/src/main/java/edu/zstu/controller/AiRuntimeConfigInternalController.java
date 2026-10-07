package edu.zstu.controller;

import edu.zstu.entity.Sys_Config;
import edu.zstu.mapper.SysConfigMapper;
import edu.zstu.utils.Result;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.Map;

/** 仅供 Python AI 服务读取已发布的运行配置；内部密钥由认证过滤器校验。 */
@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/internal/ai-runtime-config")
public class AiRuntimeConfigInternalController {
    private final SysConfigMapper configMapper;

    @GetMapping
    public Result<Map<String, Map<String, String>>> published() {
        Map<String, Map<String, String>> result = new LinkedHashMap<>();
        for (String group : new String[]{"teaching_subject", "image_generation"}) {
            Map<String, String> values = new LinkedHashMap<>();
            for (Sys_Config config : configMapper.findByGroup(group)) {
                if ("published".equals(config.getStatus())) {
                    values.put(config.getConfig_key(), config.getConfig_value());
                }
            }
            result.put(group, values);
        }
        return Result.success(result);
    }
}
