package edu.zstu.filter;

import edu.zstu.utils.CurrentHolder;
import edu.zstu.utils.JwtUtil;
import io.jsonwebtoken.Claims;
import jakarta.servlet.ServletException;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.RedisConnectionFailureException;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class JwtFailSafeTest {
    @Test
    void redisOutageBlocksAccessAndDownstreamFailureClearsIdentity() throws Exception {
        JwtUtil jwt = mock(JwtUtil.class);
        Claims claims = mock(Claims.class);
        when(jwt.parseToken("test-token")).thenReturn(claims);
        when(claims.get("user_id", Integer.class)).thenReturn(7);
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        @SuppressWarnings("unchecked")
        ValueOperations<String, String> values = mock(ValueOperations.class);
        when(redis.opsForValue()).thenReturn(values);
        when(values.get("token:user:7"))
                .thenThrow(new RedisConnectionFailureException("offline"))
                .thenReturn("test-token");
        JwtAuthenticationFilter filter = new JwtAuthenticationFilter(jwt, redis);
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/v1/users/me");
        request.addHeader("Authorization", "Bearer test-token");
        MockHttpServletResponse unavailable = new MockHttpServletResponse();
        filter.doFilter(request, unavailable, (req, res) -> fail("must not allow an unverified session"));
        assertEquals(503, unavailable.getStatus());
        assertNull(CurrentHolder.getCurrentId());
        assertThrows(ServletException.class, () -> filter.doFilter(request, new MockHttpServletResponse(), (req, res) -> {
            assertEquals(7, CurrentHolder.getCurrentId());
            throw new ServletException("downstream failure");
        }));
        assertNull(CurrentHolder.getCurrentId());
    }
}
