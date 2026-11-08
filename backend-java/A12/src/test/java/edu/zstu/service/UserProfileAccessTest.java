package edu.zstu.service;
import edu.zstu.service.impl.UserServiceImpl;
import edu.zstu.mapper.*;
import edu.zstu.entity.*;
import edu.zstu.utils.*;
import org.junit.jupiter.api.*;
import org.springframework.data.redis.core.StringRedisTemplate;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
class UserProfileAccessTest {
    @AfterEach void clear(){CurrentHolder.remove();}
    @Test void currentUserIncludesActualRolesAndPermissions(){
        var users=mock(SysUserMapper.class);var roles=mock(SysRoleMapper.class);
        var user=new Sys_User();user.setId(1);user.setUsername("test");user.setIs_active(1);user.setEmail("teacher@example.test");
        var teacher=new Sys_Role();teacher.setRole_code("teacher");var admin=new Sys_Role();admin.setRole_code("admin");
        when(users.findById(1)).thenReturn(user);when(roles.findRolesByUserId(1)).thenReturn(List.of(teacher,admin));when(roles.findPermCodesByUserId(1)).thenReturn(List.of("audit:view"));
        CurrentHolder.setCurrentId(1);
        var service=new UserServiceImpl(users,mock(PasswordUtil.class),mock(JwtUtil.class),mock(BusinessLogService.class),mock(RedisCacheUtil.class),mock(StringRedisTemplate.class),roles);
        var profile=service.getCurrentUser();
        assertEquals("admin",profile.getUser_type());assertTrue(profile.getRoles().contains("teacher"));assertTrue(profile.getPermissions().contains("audit:view"));assertFalse(profile.getPermissions().contains("users:edit"));
        assertEquals("teacher@example.test",profile.getEmail());
    }
    @Test void administratorLabelIsIndependentOfRoleSortOrder(){
        assertEquals("admin",UserAccessFields.userType(List.of("teacher","admin")));
        assertEquals("admin",UserAccessFields.userType(List.of("custom","super_admin")));
        assertEquals("teacher",UserAccessFields.userType(List.of()));
        assertEquals("content_auditor",UserAccessFields.userType(List.of("content_auditor")));
    }
}
