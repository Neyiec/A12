package edu.zstu;

import edu.zstu.dto.PageDTO;
import edu.zstu.entity.Ws_Page;
import edu.zstu.entity.Ws_Project;
import edu.zstu.mapper.*;
import edu.zstu.service.BusinessLogService;
import edu.zstu.service.impl.ProjectServiceImpl;
import edu.zstu.utils.PageTitleUtil;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class PageTitleTest {
    @Test void handlesBoundariesAndUnicode() {
        assertNull(PageTitleUtil.forStorage(null));
        assertEquals("短标题", PageTitleUtil.forStorage(" 短标题 "));
        assertEquals("字".repeat(200), PageTitleUtil.forStorage("字".repeat(200)));
        assertEquals("😀".repeat(199) + "…", PageTitleUtil.forStorage("😀".repeat(201)));
    }
    @Test void createAndUpdateBoundMetadataButPreserveFullPageContent() {
        WsProjectMapper projects = mock(WsProjectMapper.class);
        WsPageMapper pages = mock(WsPageMapper.class);
        ProjectServiceImpl service = new ProjectServiceImpl(projects, pages, mock(WsVersionMapper.class),
                mock(SysUserMapper.class), mock(BusinessLogService.class));
        Ws_Project project = new Ws_Project();
        project.setId(7); project.setUser_id(1); project.setStatus("editing"); project.setCurrent_version(1);
        when(projects.findById(7)).thenReturn(project);
        Ws_Page stored = new Ws_Page(); stored.setId(8); stored.setProject_id(7);
        when(pages.findById(any())).thenReturn(stored);
        when(pages.updateWithVersion(any(), eq(1))).thenReturn(1);
        PageDTO dto = new PageDTO();
        String full = "正文".repeat(200);
        dto.setPage_title(full); dto.setPage_order(1); dto.setPage_content("{\"title\":\"" + full + "\"}");
        dto.setComponents("[]"); dto.setExpected_page_version(1);
        service.createPage("7", dto, 1);
        service.savePage("7", "8", dto, 1);
        verify(pages).insert(argThat(p -> p.getPage_title().length() == 200 && p.getPage_content().contains(full)));
        verify(pages).updateWithVersion(argThat(p -> p.getPage_title().length() == 200 && p.getPage_content().contains(full)), eq(1));
    }
}
