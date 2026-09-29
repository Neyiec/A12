package edu.zstu.service.impl;

import edu.zstu.entity.Res_Material;
import edu.zstu.service.ResourceIndexEventPublisher;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

/** 历史调用点只发布资源业务事件，向量化由 Python 消费者完成。 */
@Service
@RequiredArgsConstructor
public class ResourceIndexSyncService {
    private final ResourceIndexEventPublisher events;

    public void syncPersonalResourceIndex(Res_Material material) {
        syncPersonalResourceIndex(material, false);
    }

    public void syncPersonalResourceIndex(Res_Material material, boolean forceReparse) {
        if (material != null) events.publish("sync", "personal", material.getId(), forceReparse);
    }

    public void updatePersonalResourceAvailability(Res_Material material) {
        if (material != null) events.publish("metadata", "personal", material.getId(), false);
    }
}
