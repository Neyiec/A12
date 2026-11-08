package edu.zstu.controller;
import edu.zstu.mapper.SysRoleMapper;
import edu.zstu.utils.CurrentHolder;
import org.junit.jupiter.api.*;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
class MenuControllerTest {
    @AfterEach void clear(){CurrentHolder.remove();}
    @Test void menuRequiresLogin(){assertEquals(401,new MenuController(mock(SysRoleMapper.class)).routers("teacher").getCode());}
    @Test void teacherMenusContainWorkspaceAndQuestions(){
        CurrentHolder.setCurrentId(1);var result=new MenuController(mock(SysRoleMapper.class)).routers("teacher");
        assertEquals(200,result.getCode());assertTrue(result.getData().toString().contains("/main/questions"));
        assertFalse(result.getData().toString().contains("/main/users"));
    }
    @Test void adminMenuDoesNotInventPermissions(){
        CurrentHolder.setCurrentId(1);var roles=mock(SysRoleMapper.class);when(roles.findPermCodesByUserId(1)).thenReturn(List.of("audit:view"));
        var result=new MenuController(roles).routers("admin");assertTrue(result.getData().toString().contains("/main/questions"));assertFalse(result.getData().toString().contains("/main/users"));
    }
    @Test void questionCreatorCanOpenEntryWithoutReviewerRights(){
        CurrentHolder.setCurrentId(1);var roles=mock(SysRoleMapper.class);when(roles.findPermCodesByUserId(1)).thenReturn(List.of("resources:edit"));
        var result=new MenuController(roles).routers("admin");assertTrue(result.getData().toString().contains("/main/questions"));assertFalse(result.getData().toString().contains("/main/audit"));
    }
}
