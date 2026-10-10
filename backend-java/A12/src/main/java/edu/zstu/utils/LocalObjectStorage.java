package edu.zstu.utils;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.http.HttpStatus;
import java.nio.file.*;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.security.MessageDigest;
import java.util.Base64;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

/** 本地测试存储；只有持有临时签名的请求能读取或写入文件。 */
@Component
public class LocalObjectStorage {
    private final Path root;
    private final String baseUrl;
    private final byte[] secret = new byte[32];
    private final long maxBytes;
    public LocalObjectStorage(@Value("${a12.storage.local.directory:./data/uploads}") String directory,
                              @Value("${a12.storage.local.base-url:http://localhost:8088}") String baseUrl,
                              @Value("${a12.storage.local.max-bytes:104857600}") long maxBytes) {
        this.root = Path.of(directory).toAbsolutePath().normalize();
        this.baseUrl = baseUrl.replaceAll("/+$", "");
        this.maxBytes = maxBytes;
        new SecureRandom().nextBytes(secret);
    }
    public Path path(String key) {
        if (key == null || !key.startsWith("local/") || key.contains("\\") || key.contains("..") || key.contains(":"))
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "无效文件路径");
        Path result = root.resolve(key.substring(6)).normalize();
        if (result.equals(root) || !result.startsWith(root)) throw new ResponseStatusException(HttpStatus.BAD_REQUEST);
        for (Path p = result; p != null && p.startsWith(root); p = p.getParent()) {
            if (Files.isSymbolicLink(p)) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "不允许符号链接");
        }
        return result;
    }
    private String signature(String method, String key, long expiry) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(secret, "HmacSHA256"));
            return Base64.getUrlEncoder().withoutPadding().encodeToString(mac.doFinal(
                (method + "\n" + key + "\n" + expiry).getBytes(StandardCharsets.UTF_8)));
        } catch (Exception e) { throw new IllegalStateException(e); }
    }
    public URL signedUrl(String key, String method, long minutes) {
        path(key);
        long expiry = System.currentTimeMillis() + minutes * 60000;
        try { return new URL(objectUrl(key) + "&expires=" + expiry + "&signature=" + signature(method,key,expiry)); }
        catch (MalformedURLException e) { throw new IllegalStateException(e); }
    }
    public String objectUrl(String key) {
        return baseUrl + "/api/v1/storage/local-object?object_key=" + URLEncoder.encode(key, StandardCharsets.UTF_8);
    }
    public String extract(String url) {
        if (url == null || !url.startsWith(baseUrl + "/api/v1/storage/local-object?")) return null;
        for (String pair : url.substring(url.indexOf('?') + 1).split("&")) {
            if (pair.startsWith("object_key=")) return URLDecoder.decode(pair.substring(11), StandardCharsets.UTF_8);
        }
        return null;
    }
    public void verify(String key, String method, long expiry, String supplied) {
        path(key);
        if (expiry < System.currentTimeMillis() || supplied == null || !MessageDigest.isEqual(
                signature(method,key,expiry).getBytes(StandardCharsets.UTF_8), supplied.getBytes(StandardCharsets.UTF_8)))
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "文件签名无效或已过期");
    }
    public void write(String key, InputStream input) {
        Path target = path(key);
        Path temporary = null;
        try {
            Files.createDirectories(target.getParent());
            temporary = Files.createTempFile(target.getParent(), ".upload-", ".tmp");
            try (OutputStream output = Files.newOutputStream(temporary)) {
                byte[] buffer = new byte[65536]; long total = 0; int count;
                while ((count = input.read(buffer)) != -1) {
                    total += count;
                    if (total > maxBytes) throw new ResponseStatusException(HttpStatus.PAYLOAD_TOO_LARGE, "文件超过本地上传限制");
                    output.write(buffer,0,count);
                }
            }
            // 不覆盖已完成的上传；失败不会留下半个文件。
            Files.move(temporary,target);
        } catch (IOException e) { throw new ResponseStatusException(HttpStatus.BAD_REQUEST,"本地文件写入失败",e); }
        finally { if (temporary != null) try { Files.deleteIfExists(temporary); } catch (IOException ignored) {} }
    }
    public boolean exists(String key) { return Files.isRegularFile(path(key)); }
    public void delete(String key) {
        try { Files.deleteIfExists(path(key)); } catch (IOException e) { throw new IllegalStateException(e); }
    }
}
