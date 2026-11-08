package edu.zstu;

import edu.zstu.config.CorsConfig;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import static org.junit.jupiter.api.Assertions.*;

class CorsConfigTest {
    @Test void bothLocalAdminOriginsPassPreflightAndUnrelatedOriginsStayBlocked() throws Exception {
        for(String origin:new String[]{"http://localhost:8888","http://127.0.0.1:8888","https://untrusted.invalid"}) {
            var request=new MockHttpServletRequest("OPTIONS","/api/v1/auth/login");
            request.addHeader("Origin",origin);request.addHeader("Access-Control-Request-Method","POST");
            request.addHeader("Access-Control-Request-Headers","content-type,authorization");
            var response=new MockHttpServletResponse();
            new CorsConfig().corsFilterRegistration().getFilter().doFilter(request,response,(a,b)->fail("Preflight should end in CORS filter"));
            if(origin.endsWith(":8888")) {
                assertEquals(200,response.getStatus());assertEquals(origin,response.getHeader("Access-Control-Allow-Origin"));
            } else assertEquals(403,response.getStatus());
        }
    }
}
