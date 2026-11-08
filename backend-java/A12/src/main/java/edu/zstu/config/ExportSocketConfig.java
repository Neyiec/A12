package edu.zstu.config;

import edu.zstu.service.ExportTaskEvents;
import edu.zstu.websocket.ExportSocketHandler;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.listener.ChannelTopic;
import org.springframework.data.redis.listener.RedisMessageListenerContainer;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;

import java.nio.charset.StandardCharsets;

@Slf4j
@Configuration
@EnableWebSocket
@RequiredArgsConstructor
public class ExportSocketConfig implements WebSocketConfigurer {
    private final ExportSocketHandler handler;
    private final ObjectProvider<RedisMessageListenerContainer> subscribers;

    @Value("${a12.websocket.allowed-origins:http://localhost:5173,http://127.0.0.1:5173}")
    private String[] allowedOrigins;

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        registry.addHandler(handler, "/ws/export-events").setAllowedOrigins(allowedOrigins);
    }

    @Bean
    RedisMessageListenerContainer exportEventSubscriber(RedisConnectionFactory factory) {
        var container = new RedisMessageListenerContainer() {
            @Override
            public boolean isAutoStartup() {
                return false;
            }
        };
        container.setConnectionFactory(factory);
        container.setMaxSubscriptionRegistrationWaitingTime(1500);
        container.addMessageListener((message, pattern) ->
                        handler.broadcast(new String(message.getBody(), StandardCharsets.UTF_8)),
                new ChannelTopic(ExportTaskEvents.CHANNEL));
        return container;
    }

    @Scheduled(fixedDelay = 5000)
    void startSubscriber() {
        var subscriber = subscribers.getObject();
        if (subscriber.isRunning()) return;
        try {
            subscriber.start();
        } catch (RuntimeException e) {
            log.warn("Export notification subscriber unavailable type={}", e.getClass().getSimpleName());
        }
    }
}
