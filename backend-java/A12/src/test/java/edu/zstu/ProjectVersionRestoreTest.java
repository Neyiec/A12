package edu.zstu;

import edu.zstu.entity.*;
import edu.zstu.mapper.*;
import edu.zstu.service.BusinessLogService;
import edu.zstu.service.impl.ProjectServiceImpl;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class ProjectVersionRestoreTest {
    private final WsProjectMapper projects = mock(WsProjectMapper.class);
    private final WsPageMapper pages = mock(WsPageMapper.class);
    private final WsVersionMapper versions = mock(WsVersionMapper.class);
    private final ProjectServiceImpl service = new ProjectServiceImpl(projects, pages, versions,
            mock(SysUserMapper.class), mock(BusinessLogService.class));

    private Ws_Project setup(String snapshot) {
        Ws_Project project = new Ws_Project();
        project.setId(7); project.setUser_id(1); project.setStatus("editing");
        project.setCurrent_version(9); project.setProject_name("当前课件");
        project.setPermissions("[2]");
        when(projects.findById(7)).thenReturn(project);
        Ws_Version version = new Ws_Version();
        version.setId(4); version.setProject_id(7); version.setVersion_number(2);
        version.setSnapshot_data(snapshot); when(versions.findById(4)).thenReturn(version);
        when(pages.findByProjectId(7)).thenReturn(List.of());
        when(projects.restoreContentWithVersion(any(), eq(9))).thenReturn(1);
        when(versions.findMaxVersionNumber(7)).thenReturn(3);
        return project;
    }

    @Test void restoreBacksUpThenRecreatesPagesWithoutRevertingPermissions() {
        Ws_Project project = setup("{\"project\":{\"project_name\":\"旧版\",\"permissions\":\"[99]\",\"status\":\"archived\"},\"pages\":[{\"page_order\":1,\"page_title\":\"旧页面\",\"page_content\":\"{html:old}\",\"page_version\":8}]}");
        service.restoreVersion("7", "4", 1);
        var order = inOrder(versions, pages, projects);
        order.verify(versions).insert(any());
        order.verify(pages).deleteByProjectId(7);
        ArgumentCaptor<Ws_Page> restored = ArgumentCaptor.forClass(Ws_Page.class);
        order.verify(pages).insert(restored.capture());
        order.verify(projects).restoreContentWithVersion(project, 9);
        assertEquals(7, restored.getValue().getProject_id());
        assertEquals(1, restored.getValue().getPage_version());
        assertEquals("旧页面", restored.getValue().getPage_title());
        assertEquals("[2]", project.getPermissions());
        assertEquals("editing", project.getStatus());
        assertEquals(10, project.getCurrent_version());
        ArgumentCaptor<Ws_Version> backup = ArgumentCaptor.forClass(Ws_Version.class);
        verify(versions).insert(backup.capture());
        assertTrue(backup.getValue().getSnapshot_data().contains("当前课件"));
    }

    @Test void rejectsForeignProjectVersionBeforeWriting() {
        setup("{\"pages\":[]}");
        versions.findById(4).setProject_id(8);
        assertThrows(RuntimeException.class, () -> service.restoreVersion("7", "4", 1));
        verify(versions, never()).insert(any()); verify(pages, never()).deleteByProjectId(any());
    }

    @Test void directRestoreReplacesPagesWithoutCreatingBackupVersion() {
        setup("{\"pages\":[{\"page_order\":1,\"page_title\":\"直接恢复\"}]}");
        service.restoreVersion("7", "4", 1, false);
        verify(versions, never()).insert(any());
        verify(versions, never()).findMaxVersionNumber(any());
        verify(pages).deleteByProjectId(7);
        verify(pages).insert(any());
        verify(projects).restoreContentWithVersion(any(), eq(9));
    }

    @Test void rejectsBrokenSnapshotBeforeWriting() {
        setup("{\"project\":{}}");
        assertThrows(RuntimeException.class, () -> service.restoreVersion("7", "4", 1));
        verify(versions, never()).insert(any()); verify(pages, never()).deleteByProjectId(any());
    }

    @Test void refusesArchivedProject() {
        setup("{\"pages\":[]}").setStatus("archived");
        assertThrows(RuntimeException.class, () -> service.restoreVersion("7", "4", 1));
        verify(versions, never()).insert(any());
    }

    @Test void rejectsConcurrentUpdate() {
        setup("{\"pages\":[]}");
        when(projects.restoreContentWithVersion(any(), eq(9))).thenReturn(0);
        assertThrows(RuntimeException.class, () -> service.restoreVersion("7", "4", 1));
    }

    @Test void oldNullMetadataClearsNewerLessonPlanAndUsesDedicatedRestoreUpdate() {
        Ws_Project project = setup("{\"project\":{\"project_name\":\"旧版\",\"snapshots\":null,\"edit_history\":null},\"pages\":[]}");
        project.setEdit_history("{\"lesson_plan\":{\"title\":\"新版教案\"}}");
        project.setSnapshots("[{\"new\":true}]");
        service.restoreVersion("7", "4", 1);
        assertNull(project.getEdit_history());
        assertNull(project.getSnapshots());
        verify(projects).restoreContentWithVersion(project, 9);
        verify(projects, never()).updateWithVersion(any(), any());
    }
}
