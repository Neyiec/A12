package edu.zstu.service;

import edu.zstu.entity.Adm_Resource;
import edu.zstu.entity.Com_Content;
import edu.zstu.mapper.AdmResourceMapper;
import edu.zstu.mapper.ComContentMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.util.List;

/** 每日补偿漏发的索引事件；只发业务事件，解析和向量化仍由 Python 执行。 */
@Component
@RequiredArgsConstructor
@Slf4j
public class KnowledgeIndexMaintenance {
    private final AdmResourceMapper resources;
    private final ComContentMapper contents;
    private final ResourceIndexEventPublisher events;

    @Scheduled(cron = "${a12.knowledge-index.reconcile-cron:0 30 3 * * *}")
    public void reconcile() {
        int resourceCursor = 0;
        int resourceCount = 0;
        while (true) {
            List<Adm_Resource> batch = resources.findIndexRepairCandidates(resourceCursor, 200);
            for (Adm_Resource item : batch) {
                events.publish("sync", "public", item.getId(), false);
                resourceCursor = item.getId();
                resourceCount++;
            }
            if (batch.size() < 200) break;
        }
        int contentCursor = 0;
        int contentCount = 0;
        while (true) {
            List<Com_Content> batch = contents.findPptIndexCandidates(contentCursor, 200);
            for (Com_Content item : batch) {
                boolean eligible = "public".equals(item.getStatus()) && item.getLicense() != null
                        && item.getLicense().startsWith("CC BY");
                events.publish(eligible ? "sync" : "delete", "community", item.getId(), false);
                contentCursor = item.getId();
                contentCount++;
            }
            if (batch.size() < 200) break;
        }
        log.info("知识索引补偿事件已发布：公共资源 {} 条，社区课件 {} 条", resourceCount, contentCount);
    }
}
