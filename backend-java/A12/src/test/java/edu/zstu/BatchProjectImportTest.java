package edu.zstu;

import edu.zstu.service.BatchProjectImportService;
import edu.zstu.service.ProjectService;
import edu.zstu.mapper.SysUserMapper;
import edu.zstu.entity.Sys_User;
import edu.zstu.vo.ProjectVO;
import edu.zstu.dto.PageDTO;
import org.springframework.jdbc.core.JdbcTemplate;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import java.util.*;
import static org.mockito.Mockito.*;
import static org.junit.jupiter.api.Assertions.*;

class BatchProjectImportTest {
    private final JdbcTemplate jdbc=mock(JdbcTemplate.class);
    private final ProjectService projects=mock(ProjectService.class);
    private final SysUserMapper users=mock(SysUserMapper.class);
    private final BatchProjectImportService importer=new BatchProjectImportService(jdbc,projects,users);
    private BatchProjectImportService.ImportRequest request() {
        return new BatchProjectImportService.ImportRequest("a".repeat(32),"b".repeat(32),"数学 · 01 二次函数",
            List.of(Map.of("title","定义","html","<html><body>可编辑内容</body></html>","notes","教师讲稿","metadata",Map.of("prompt_version",1))),Map.of());
    }
    private void active() {
        var user=new Sys_User();user.setId(7);user.setIs_active(1);when(users.findById(7)).thenReturn(user);
    }
    @Test void sameItemReturnsExistingProjectWithoutOverwritingEdits() {
        active();when(jdbc.queryForMap(anyString(),eq(7),anyString(),anyString())).thenReturn(Map.of("project_id",99));
        var existing=new ProjectVO();existing.setId(99);existing.setUser_id(7);
        when(projects.getProject("99",7)).thenReturn(existing);
        assertEquals(99,importer.save(7,request()).getId());
        verify(projects,never()).createProject(any(),anyInt());
        verify(projects,never()).createPage(anyString(),any(),anyInt());
        verify(projects,never()).saveVersion(anyString(),any(),anyInt());
    }
    @Test void newItemCopiesHtmlNotesAndProvenanceAndCreatesInitialSnapshot() {
        active();when(jdbc.queryForMap(anyString(),eq(7),anyString(),anyString())).thenReturn(Collections.singletonMap("project_id",null));
        var created=new ProjectVO();created.setId(88);created.setUser_id(7);
        when(projects.createProject(any(),eq(7))).thenReturn(created);when(projects.getProject("88",7)).thenReturn(created);
        importer.save(7,request());
        var page=ArgumentCaptor.forClass(PageDTO.class);verify(projects).createPage(eq("88"),page.capture(),eq(7));
        assertTrue(page.getValue().getPage_content().contains("可编辑内容"));
        assertTrue(page.getValue().getPage_content().contains("教师讲稿"));
        assertTrue(page.getValue().getPage_content().contains("prompt_version"));
        verify(projects).saveVersion(eq("88"),any(),eq(7));
    }
    @Test void validatesOwnerAndPayloadBeforeCreatingAnything() {
        assertThrows(IllegalArgumentException.class,()->importer.save(null,request()));
        assertThrows(IllegalArgumentException.class,()->importer.save(7,request()));
        active();var invalid=new BatchProjectImportService.ImportRequest("../bad","x","test",request().slides(),Map.of());
        assertThrows(IllegalArgumentException.class,()->importer.save(7,invalid));
        verifyNoInteractions(jdbc,projects);
    }
}
