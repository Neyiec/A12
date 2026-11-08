package edu.zstu.filter;

import edu.zstu.mapper.SysRoleMapper;
import edu.zstu.utils.CurrentHolder;
import edu.zstu.utils.RedisCacheUtil;
import com.fasterxml.jackson.core.type.TypeReference;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import jakarta.servlet.FilterChain;
import java.util.List;
import static org.mockito.Mockito.*;
import static org.junit.jupiter.api.Assertions.*;

class QuestionBankAuthorizationTest {
    @AfterEach void cleanup(){CurrentHolder.remove();}
    @Test void noLoginCannotAccessAdminQuestions() throws Exception {
        var filter=new AdminAuthFilter(mock(SysRoleMapper.class),mock(RedisCacheUtil.class));
        var response=new MockHttpServletResponse();var chain=mock(FilterChain.class);
        filter.doFilter(new MockHttpServletRequest("GET","/api/v1/admin/questions"),response,chain);
        assertEquals(403,response.getStatus());verifyNoInteractions(chain);
    }
    private void check(String method,String path,List<String> permissions,boolean allowed) throws Exception {
        CurrentHolder.setCurrentId(1);var cache=mock(RedisCacheUtil.class);
        when(cache.getOrLoad(anyString(),org.mockito.ArgumentMatchers.<TypeReference<List<String>>>any(),any(),any())).thenReturn(permissions);
        var filter=new AdminAuthFilter(mock(SysRoleMapper.class),cache);var response=new MockHttpServletResponse();var chain=mock(FilterChain.class);
        var request=new MockHttpServletRequest(method,path);filter.doFilter(request,response,chain);
        if(allowed)verify(chain).doFilter(request,response);else{assertEquals(403,response.getStatus());verifyNoInteractions(chain);}
    }
    @Test void ordinaryTeacherCannotListCreateOrReview() throws Exception {
        check("GET","/api/v1/admin/questions",List.of(),false);
        check("POST","/api/v1/admin/questions",List.of(),false);
        check("POST","/api/v1/admin/questions/1/review",List.of(),false);
    }
    @Test void viewPermissionCannotPublishOrReview() throws Exception {
        check("GET","/api/v1/admin/questions",List.of("audit:view"),true);
        check("GET","/api/v1/admin/questions/1",List.of("audit:view"),true);
        check("POST","/api/v1/admin/questions",List.of("audit:view"),false);
        check("POST","/api/v1/admin/questions/1/review",List.of("audit:view"),false);
    }
    @Test void creatorAndReviewerHaveSeparatePermissions() throws Exception {
        check("POST","/api/v1/admin/questions",List.of("resources:edit"),true);
        check("POST","/api/v1/admin/questions/1/review",List.of("audit:audit"),true);
        check("POST","/api/v1/admin/questions/1/review",List.of("resources:edit"),false);
    }
}
