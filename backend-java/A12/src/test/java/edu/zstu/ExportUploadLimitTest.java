package edu.zstu;

import org.junit.jupiter.api.Test;
import org.springframework.boot.context.properties.bind.Bindable;
import org.springframework.boot.context.properties.bind.Binder;
import org.springframework.boot.env.YamlPropertySourceLoader;
import org.springframework.boot.autoconfigure.web.servlet.MultipartProperties;
import org.springframework.core.env.StandardEnvironment;
import org.springframework.core.io.ClassPathResource;
import static org.junit.jupiter.api.Assertions.*;

class ExportUploadLimitTest {
    @Test
    void exportMultipartLimitMatchesServiceAndLeavesRoomForHeaders() throws Exception {
        var environment = new StandardEnvironment();
        for (var source : new YamlPropertySourceLoader().load("application", new ClassPathResource("application.yaml"))) {
            environment.getPropertySources().addLast(source);
        }
        var properties = Binder.get(environment).bind("spring.servlet.multipart", Bindable.of(MultipartProperties.class)).get();
        assertEquals(100L * 1024 * 1024, properties.getMaxFileSize().toBytes());
        assertTrue(properties.getMaxRequestSize().toBytes() > properties.getMaxFileSize().toBytes());
    }
}
