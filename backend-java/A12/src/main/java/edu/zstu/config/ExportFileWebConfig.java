package edu.zstu.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

import java.nio.file.Path;

@Configuration
public class ExportFileWebConfig implements WebMvcConfigurer {
    private final Path exportDir;
    private final String publicPrefix;

    public ExportFileWebConfig(@Value("${a12.export.local-dir:data/exports}") String exportDir,
                               @Value("${a12.export.public-prefix:/exports}") String publicPrefix) {
        this.exportDir = Path.of(exportDir).toAbsolutePath().normalize();
        this.publicPrefix = publicPrefix == null || publicPrefix.isBlank() ? "/exports" : publicPrefix.replaceAll("/+$", "");
    }

    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        registry.addResourceHandler(publicPrefix + "/**")
                .addResourceLocations(exportDir.toUri().toString())
                .setCachePeriod(3600);
    }
}
