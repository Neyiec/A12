package edu.zstu;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.zstu.entity.Ws_Project;
import edu.zstu.entity.Ws_Version;
import edu.zstu.mapper.*;
import edu.zstu.service.BusinessLogService;
import edu.zstu.service.impl.ExportServiceImpl;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;
import java.util.List;
import java.util.Map;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class ExportSnapshotTest {
    @Test
    void selectedSnapshotOverridesLivePagesAndConfigSlides() {
        WsVersionMapper versions = mock(WsVersionMapper.class);
        WsPageMapper pages = mock(WsPageMapper.class);
        var service = new ExportServiceImpl(mock(ExpTaskMapper.class), mock(WsProjectMapper.class), pages,
                versions, mock(BusinessLogService.class), new ObjectMapper(), "target/test-exports", "/exports");
        Ws_Project project = new Ws_Project();
        project.setId(7);
        Ws_Version version = new Ws_Version();
        version.setVersion_number(2);
        version.setSnapshot_data("{\"pages\":[{\"page_order\":1,\"page_title\":\"旧版\",\"page_content\":\"{\\\"html\\\":\\\"<h1>快照内容</h1>\\\"}\"}]}");
        when(versions.findByProjectId(7)).thenReturn(List.of(version));
        List<Map<String, Object>> slides = ReflectionTestUtils.invokeMethod(service, "buildSlides", project,
                Map.of("slides", List.of(Map.of("html", "错误的当前内容"))), 2);
        assertNotNull(slides);
        assertEquals("<h1>快照内容</h1>", slides.get(0).get("html"));
        verifyNoInteractions(pages);
        assertThrows(RuntimeException.class, () -> ReflectionTestUtils.invokeMethod(service, "exportPages", project, 3));
    }
}
