package edu.zstu;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.zstu.entity.Com_Content;
import edu.zstu.mapper.AdmAuditMapper;
import edu.zstu.mapper.ComContentMapper;
import edu.zstu.mapper.ComInteractionMapper;
import edu.zstu.service.BusinessLogService;
import edu.zstu.service.CommunityReviewEventPublisher;
import edu.zstu.service.ProjectService;
import edu.zstu.service.impl.CommunityServiceImpl;
import edu.zstu.utils.RedisCacheUtil;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.mock;

class CommunityReuseVersionTest {
    @SuppressWarnings("unchecked")
    @Test
    void historicalVersionUsesItsOwnSnapshotInsteadOfCurrentSlides() {
        var service = new CommunityServiceImpl(mock(ComContentMapper.class), mock(ComInteractionMapper.class),
                mock(edu.zstu.mapper.ComLikeMapper.class), mock(AdmAuditMapper.class), mock(ProjectService.class), mock(BusinessLogService.class),
                mock(RedisCacheUtil.class), mock(edu.zstu.utils.RedisRateLimiter.class), mock(StringRedisTemplate.class), new ObjectMapper(),
                mock(CommunityReviewEventPublisher.class));
        Com_Content content = new Com_Content();
        content.setVersion(3);
        content.setTitle("当前标题");
        content.setContent_data("{\"slides\":[{\"title\":\"当前版本\"}]}");
        content.setVersion_history("[{\"version_number\":3,\"title\":\"旧标题\","
                + "\"content_data\":\"{\\\"slides\\\":[{\\\"title\\\":\\\"旧版本\\\"}]}\"}]");

        Map<String, Object> selected = ReflectionTestUtils.invokeMethod(service, "contentAtVersion", content, 2);
        assertNotNull(selected);
        assertEquals("旧标题", selected.get("title"));
        assertTrue(String.valueOf(selected.get("content_data")).contains("旧版本"));
        assertThrows(RuntimeException.class,
                () -> ReflectionTestUtils.invokeMethod(service, "contentAtVersion", content, 1));

        content.setVersion_history("[{\"version_number\":2,\"snapshot_semantics\":\"prior\","
                + "\"title\":\"新语义快照\",\"content_data\":\"{}\"}]");
        Map<String, Object> newSnapshot = ReflectionTestUtils.invokeMethod(service, "contentAtVersion", content, 2);
        assertEquals("新语义快照", newSnapshot.get("title"));
    }
}
