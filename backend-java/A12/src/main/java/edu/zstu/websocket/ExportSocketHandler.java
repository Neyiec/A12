package edu.zstu.websocket;

import edu.zstu.utils.JwtUtil;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.listener.RedisMessageListenerContainer;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.ConcurrentWebSocketSessionDecorator;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.io.IOException;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Component
@RequiredArgsConstructor
public class ExportSocketHandler extends TextWebSocketHandler {
    private static final CloseStatus RETRY = new CloseStatus(1013, "Push unavailable");
    private final JwtUtil jwt;
    private final StringRedisTemplate redis;
    private final ObjectProvider<RedisMessageListenerContainer> subscriber;
    private final Map<String, Client> clients = new ConcurrentHashMap<>();

    private static class Client {
        final WebSocketSession socket;
        volatile long lastActivity = System.nanoTime();
        volatile Integer owner;
        String token;

        Client(WebSocketSession socket) {
            this.socket = new ConcurrentWebSocketSessionDecorator(socket, 3000, 16 * 1024);
        }
    }

    @Override
    public void afterConnectionEstablished(WebSocketSession session) {
        session.setTextMessageSizeLimit(4096);
        clients.put(session.getId(), new Client(session));
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) {
        Client client = clients.get(session.getId());
        if (client == null) return;
        String payload = message.getPayload();
        boolean opening = client.owner == null;
        String token = opening && payload.startsWith("auth ") ? payload.substring(5) : client.token;
        if ((opening && !payload.startsWith("auth ")) || (!opening && !"ping".equals(payload))) {
            close(client, CloseStatus.POLICY_VIOLATION);
            return;
        }
        var claims = token == null ? null : jwt.parseToken(token);
        Integer owner = claims == null ? null : claims.get("user_id", Integer.class);
        if (owner == null) {
            close(client, CloseStatus.POLICY_VIOLATION);
            return;
        }
        try {
            if (!token.equals(redis.opsForValue().get("token:user:" + owner))) {
                close(client, CloseStatus.POLICY_VIOLATION);
                return;
            }
            if (!subscriber.getObject().isListening()) {
                close(client, RETRY);
                return;
            }
            client.token = token;
            client.lastActivity = System.nanoTime();
            client.owner = owner;
            send(client, opening ? "{\"type\":\"ready\"}" : "{\"type\":\"pong\"}");
        } catch (RuntimeException e) {
            close(client, RETRY);
        }
    }

    public void broadcast(String payload) {
        String[] parts = payload.split(":", 2);
        if (parts.length != 2) return;
        try {
            int owner = Integer.parseInt(parts[0]);
            int task = Integer.parseInt(parts[1]);
            if (owner <= 0 || task <= 0) return;
            for (Client client : clients.values()) {
                if (!Integer.valueOf(owner).equals(client.owner)) continue;
                // 已退出或被替换的旧会话不得接收后续事件。
                try {
                    if (jwt.parseToken(client.token) == null
                            || !client.token.equals(redis.opsForValue().get("token:user:" + owner))) {
                        close(client, CloseStatus.POLICY_VIOLATION);
                    } else {
                        send(client, "{\"type\":\"export_changed\",\"taskId\":" + task + "}");
                    }
                } catch (RuntimeException e) {
                    close(client, RETRY);
                }
            }
        } catch (NumberFormatException ignored) {
            // 忽略不符合内部事件格式的消息。
        }
    }

    @Scheduled(fixedDelay = 5000)
    void removeIdleClients() {
        long now = System.nanoTime();
        for (Client client : clients.values()) {
            long seconds = (now - client.lastActivity) / 1_000_000_000L;
            if (seconds > (client.owner == null ? 10 : 55)) close(client, CloseStatus.GOING_AWAY);
        }
    }

    private void send(Client client, String message) {
        try {
            client.socket.sendMessage(new TextMessage(message));
        } catch (IOException | RuntimeException e) {
            close(client, RETRY);
        }
    }

    private void close(Client client, CloseStatus status) {
        clients.remove(client.socket.getId(), client);
        try {
            client.socket.close(status);
        } catch (IOException ignored) {
            // 客户端可能已断开。
        }
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        clients.remove(session.getId());
    }
}
