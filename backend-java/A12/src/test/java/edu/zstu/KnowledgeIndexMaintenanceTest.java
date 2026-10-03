package edu.zstu;

import edu.zstu.entity.Com_Content;
import edu.zstu.mapper.AdmResourceMapper;
import edu.zstu.mapper.ComContentMapper;
import edu.zstu.service.KnowledgeIndexMaintenance;
import edu.zstu.service.ResourceIndexEventPublisher;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.mockito.Mockito.*;

class KnowledgeIndexMaintenanceTest {
    @Test
    void onlyPublicLicensedPptIsQueuedForAiSearch() {
        AdmResourceMapper resources = mock(AdmResourceMapper.class);
        ComContentMapper contents = mock(ComContentMapper.class);
        ResourceIndexEventPublisher events = mock(ResourceIndexEventPublisher.class);
        Com_Content licensed = new Com_Content();
        licensed.setId(1);
        licensed.setStatus("public");
        licensed.setLicense("CC BY-NC 4.0");
        Com_Content offline = new Com_Content();
        offline.setId(2);
        offline.setStatus("offline");
        offline.setLicense("CC BY 4.0");
        when(resources.findIndexRepairCandidates(0, 200)).thenReturn(List.of());
        when(contents.findPptIndexCandidates(0, 200)).thenReturn(List.of(licensed, offline));

        new KnowledgeIndexMaintenance(resources, contents, events).reconcile();

        verify(events).publish("sync", "community", 1, false);
        verify(events).publish("delete", "community", 2, false);
    }
}
