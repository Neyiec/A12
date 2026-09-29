package edu.zstu.service.impl;

import edu.zstu.mapper.AdmResourceMapper;
import edu.zstu.service.ResourceIndexEventPublisher;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.Map;

/** 公共资源只发布业务事件；Python 自行取得授权文件并建立索引。 */
@Service
@RequiredArgsConstructor
public class PublicResourceIndexSyncService {
    private final AdmResourceMapper resourceMapper;
    private final ResourceIndexEventPublisher events;

    public void syncPublicResourceIndex(Integer resourceId, Map<String, Object> payload) {
        resourceMapper.updateAiIndexStatus(resourceId, "indexing", null);
        events.publish("sync", "public", resourceId, Boolean.TRUE.equals(payload.get("force_reparse")));
    }
}
