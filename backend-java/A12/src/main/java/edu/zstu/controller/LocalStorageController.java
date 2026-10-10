package edu.zstu.controller;

import edu.zstu.utils.LocalObjectStorage;
import org.springframework.web.bind.annotation.*;
import org.springframework.core.io.FileSystemResource;
import org.springframework.http.*;
import jakarta.servlet.http.HttpServletRequest;
import java.io.IOException;

@RestController
@RequestMapping("/api/v1/storage/local-object")
public class LocalStorageController {
    private final LocalObjectStorage storage;
    public LocalStorageController(LocalObjectStorage storage) { this.storage = storage; }
    @PutMapping
    public ResponseEntity<Void> upload(@RequestParam("object_key") String key, @RequestParam long expires,
                                      @RequestParam String signature, HttpServletRequest request) throws IOException {
        storage.verify(key,"PUT",expires,signature);
        storage.write(key, request.getInputStream());
        return ResponseEntity.noContent().build();
    }
    @GetMapping
    public ResponseEntity<FileSystemResource> download(@RequestParam("object_key") String key,
                                                      @RequestParam long expires, @RequestParam String signature) {
        storage.verify(key,"GET",expires,signature);
        if (!storage.exists(key)) return ResponseEntity.notFound().build();
        return ResponseEntity.ok().contentType(MediaType.APPLICATION_OCTET_STREAM)
            .header(HttpHeaders.CONTENT_DISPOSITION,"attachment")
            .header(HttpHeaders.CACHE_CONTROL,"private, no-store")
            .header("X-Content-Type-Options","nosniff")
            .body(new FileSystemResource(storage.path(key)));
    }
}
