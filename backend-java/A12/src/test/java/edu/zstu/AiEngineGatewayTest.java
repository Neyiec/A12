package edu.zstu;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpServer;
import edu.zstu.controller.PythonProxyController;
import edu.zstu.filter.JwtAuthenticationFilter;
import edu.zstu.service.PythonPptClient;
import edu.zstu.utils.JwtUtil;
import edu.zstu.utils.OssUtil;
import io.jsonwebtoken.Claims;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/** 使用本地 HTTP 上游验证真实 Java 转发，不依赖数据库或收费模型。 */
class AiEngineGatewayTest {
    private HttpServer upstream;
    private MockMvc mvc;
    private final AtomicReference<String> path = new AtomicReference<>();
    private final AtomicReference<String> body = new AtomicReference<>();

    @BeforeEach
    @SuppressWarnings("unchecked")
    void setup() throws Exception {
        upstream = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        upstream.createContext("/", exchange -> {
            path.set(exchange.getRequestURI().toString());
            body.set(new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
            String endpoint = exchange.getRequestURI().getPath();
            String contentType = "application/json";
            String response = "{\"code\":200,\"data\":{\"ok\":true}}";
            int status = 200;
            if (endpoint.endsWith("outlines/chat/stream")) {
                contentType = "text/event-stream";
                response = "event: outline_delta\ndata: {\"slide\":{\"title\":\"测试\"}}\n\nevent: done\ndata: {\"status\":\"completed\"}\n\n";
            } else if (endpoint.endsWith("workspace/chat/stream")) {
                contentType = "text/event-stream";
                if (body.get().contains("force_error")) {
                    status = 503;
                    response = "{\"detail\":\"Model unavailable\"}";
                } else {
                    response = "data: {\"choices\":[{\"delta\":{\"content\":\"课堂建议\"}}]}\n\ndata: [DONE]\n\n";
                }
            } else if (endpoint.endsWith("export/pptx")) {
                contentType = "application/vnd.openxmlformats-officedocument.presentationml.presentation";
                exchange.getResponseHeaders().set("Content-Disposition", "attachment; filename=lesson.pptx");
                response = "PK-test-file";
            }
            exchange.getResponseHeaders().set("Content-Type", contentType);
            byte[] bytes = response.getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(status, bytes.length);
            exchange.getResponseBody().write(bytes);
            exchange.close();
        });
        upstream.start();
        PythonPptClient client = new PythonPptClient(new ObjectMapper(),
                "http://127.0.0.1:" + upstream.getAddress().getPort(), 2, 5);
        JwtUtil jwt = mock(JwtUtil.class);
        Claims claims = mock(Claims.class);
        when(claims.get("user_id", Integer.class)).thenReturn(42);
        when(jwt.parseToken("valid")).thenReturn(claims);
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        ValueOperations<String, String> values = mock(ValueOperations.class);
        when(redis.opsForValue()).thenReturn(values);
        when(values.get("token:user:42")).thenReturn("valid");
        mvc = MockMvcBuilders.standaloneSetup(new PythonProxyController(client, mock(OssUtil.class)))
                .addFilters(new JwtAuthenticationFilter(jwt, redis)).build();
    }

    @AfterEach
    void teardown() {
        upstream.stop(0);
        edu.zstu.utils.CurrentHolder.remove();
    }

    @Test
    void authenticatesNewAndLegacyGatewayAndForwardsJson() throws Exception {
        mvc.perform(get("/api/v1/ai/engine/templates")).andExpect(status().isUnauthorized());
        assertNull(path.get());
        for (String prefix : new String[]{"/api/v1/ai/engine", "/api/v1/python"}) {
            mvc.perform(get(prefix + "/templates").header("Authorization", "Bearer valid"))
                    .andExpect(status().isOk()).andExpect(jsonPath("$.data.ok").value(true));
            assertEquals("/api/v1/python/templates", path.get());
        }
    }

    @Test
    void overridesCallerIdentityForSessionsAndProfiles() throws Exception {
        mvc.perform(post("/api/v1/ai/engine/outlines/chat/sessions")
                .header("Authorization", "Bearer valid").contentType(MediaType.APPLICATION_JSON)
                .content("{\"user_id\":\"other-user\",\"title\":\"test\"}"))
                .andExpect(status().isOk());
        assertEquals("42", new ObjectMapper().readTree(body.get()).get("user_id").asText());
        mvc.perform(get("/api/v1/ai/engine/teacher-style/profile?user_id=other-user")
                .header("Authorization", "Bearer valid")).andExpect(status().isOk());
        assertEquals("/api/v1/python/teacher-style/profile?user_id=42", path.get());
    }

    @Test
    void forwardsMultipartAndBinaryDownload() throws Exception {
        mvc.perform(multipart("/api/v1/ai/engine/audio/asr")
                .file(new MockMultipartFile("file", "voice.wav", "audio/wav", "audio-bytes".getBytes(StandardCharsets.UTF_8)))
                .param("language", "zh").header("Authorization", "Bearer valid"))
                .andExpect(status().isOk());
        assertEquals("/api/v1/python/audio/asr", path.get());
        assertTrue(body.get().contains("audio-bytes"));
        assertTrue(body.get().contains("name=\"language\""));
        mvc.perform(post("/api/v1/ai/engine/presentations/export/pptx")
                .contentType(MediaType.APPLICATION_JSON).content("{}")
                .header("Authorization", "Bearer valid"))
                .andExpect(status().isOk()).andExpect(content().string("PK-test-file"))
                .andExpect(header().string("Content-Type", "application/vnd.openxmlformats-officedocument.presentationml.presentation"));
    }

    @Test
    void forwardsSseEventsAndReportsUpstreamErrorsWithoutSuccess() throws Exception {
        MvcResult result = mvc.perform(post("/api/v1/ai/engine/outlines/chat/stream")
                .contentType(MediaType.APPLICATION_JSON).content("{\"user_id\":\"forged\",\"message\":\"test\"}")
                .header("Authorization", "Bearer valid"))
                .andExpect(request().asyncStarted()).andReturn();
        result.getAsyncResult(5000);
        String events = result.getResponse().getContentAsString(StandardCharsets.UTF_8);
        assertTrue(events.contains("event:outline_delta"));
        assertTrue(events.contains("测试"), events);
        assertTrue(events.contains("event:done"));
        assertEquals("42", new ObjectMapper().readTree(body.get()).get("user_id").asText());

        MvcResult workspace = mvc.perform(post("/api/v1/ai/engine/workspace/chat/stream")
                .contentType(MediaType.APPLICATION_JSON).content("{\"user_id\":\"forged\",\"mode\":\"discussion\",\"messages\":[{\"role\":\"user\",\"content\":\"test\"}]}")
                .header("Authorization", "Bearer valid"))
                .andExpect(request().asyncStarted()).andReturn();
        workspace.getAsyncResult(5000);
        String workspaceEvents = workspace.getResponse().getContentAsString(StandardCharsets.UTF_8);
        assertTrue(workspaceEvents.contains("课堂建议"), workspaceEvents);
        assertTrue(workspaceEvents.contains("[DONE]"), workspaceEvents);
        assertEquals("42", new ObjectMapper().readTree(body.get()).get("user_id").asText());

        MvcResult failed = mvc.perform(post("/api/v1/ai/engine/workspace/chat/stream")
                .contentType(MediaType.APPLICATION_JSON).content("{\"messages\":[{\"role\":\"user\",\"content\":\"force_error\"}]}")
                .header("Authorization", "Bearer valid"))
                .andExpect(request().asyncStarted()).andReturn();
        failed.getAsyncResult(5000);
        String errorEvents = failed.getResponse().getContentAsString(StandardCharsets.UTF_8);
        assertTrue(errorEvents.contains("event:error"));
        assertTrue(errorEvents.contains("503"));
        assertFalse(errorEvents.contains("event:done"));
    }
}
