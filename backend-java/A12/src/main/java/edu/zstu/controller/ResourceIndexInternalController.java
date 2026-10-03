package edu.zstu.controller;

import edu.zstu.entity.Adm_Resource;
import edu.zstu.entity.Res_Material;
import edu.zstu.mapper.AdmResourceMapper;
import edu.zstu.mapper.ResMaterialMapper;
import edu.zstu.mapper.ComContentMapper;
import edu.zstu.entity.Com_Content;
import edu.zstu.utils.OssUtil;
import edu.zstu.utils.Result;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.Map;

/** Python 索引消费者读取当前业务状态；仅允许共享密钥认证的服务调用。 */
@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/internal/resource-index")
public class ResourceIndexInternalController {
    private final AdmResourceMapper publicResources;
    private final ResMaterialMapper personalResources;
    private final ComContentMapper communityContents;
    private final OssUtil oss;

    @GetMapping("/{sourceType}/{resourceId}")
    public Result<Map<String, Object>> payload(@PathVariable String sourceType, @PathVariable Integer resourceId) {
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("source_type", sourceType);
        data.put("resource_id", String.valueOf(resourceId));
        Map<String, Object> metadata = new LinkedHashMap<>();
        if ("public".equals(sourceType)) {
            Adm_Resource r = publicResources.findById(resourceId);
            if (r == null) return Result.error(404, "资源不存在");
            metadata.put("subject", r.getSubject());
            metadata.put("grade", r.getGrade());
            metadata.put("resource_type", r.getResource_type());
            metadata.put("description", r.getDescription());
            data.put("title", r.getTitle());
            data.put("file_type", detectedFileType(r.getFile_url(), r.getTitle(), r.getResource_type()));
            data.put("file_size", r.getFile_size());
            data.put("uploaded_by", String.valueOf(r.getUploaded_by()));
            data.put("owner_user_id", null);
            data.put("available", r.getStatus() == 1);
            data.put("allow_ai", r.getStatus() == 1);
            data.put("file_url", signedUrl(r.getFile_url()));
        } else if ("personal".equals(sourceType)) {
            Res_Material r = personalResources.findById(resourceId);
            if (r == null) return Result.error(404, "资源不存在");
            metadata.put("description", r.getDescription());
            metadata.put("categories", r.getCategories());
            metadata.put("tags", r.getTags());
            metadata.put("access_type", r.getAccess_type());
            metadata.put("authorized_users", r.getAuthorized_users());
            metadata.put("owner_user_id", String.valueOf(r.getUser_id()));
            data.put("title", r.getFile_name());
            data.put("file_type", r.getFile_type());
            data.put("file_size", r.getFile_size());
            data.put("uploaded_by", String.valueOf(r.getUser_id()));
            data.put("owner_user_id", String.valueOf(r.getUser_id()));
            data.put("available", r.getStatus() != null && r.getStatus() == 1 && r.getAllow_ai() != null && r.getAllow_ai() == 1);
            data.put("allow_ai", r.getAllow_ai() != null && r.getAllow_ai() == 1);
            data.put("file_url", signedUrl(r.getFile_url()));
        } else if ("community".equals(sourceType)) {
            Com_Content c = communityContents.findById(resourceId);
            if (c == null || !"public".equals(c.getStatus())) return Result.error(404, "社区内容未公开");
            metadata.put("subject", c.getSubject());
            metadata.put("grade", c.getGrade());
            metadata.put("lesson_type", c.getLesson_type());
            metadata.put("license", c.getLicense());
            metadata.put("version", c.getVersion());
            data.put("title", c.getTitle());
            data.put("description", c.getDescription());
            data.put("content_data", c.getContent_data());
            data.put("file_url", "community://" + resourceId + "/" + c.getVersion());
            data.put("file_type", "html");
            data.put("file_size", 0);
            data.put("uploaded_by", String.valueOf(c.getAuthor_id()));
            data.put("owner_user_id", null);
            data.put("available", true);
            data.put("allow_ai", c.getLicense() != null && c.getLicense().startsWith("CC BY"));
        } else {
            return Result.error(400, "无效的资源类型");
        }
        data.put("metadata", metadata);
        return Result.success(data);
    }

    @PostMapping("/{sourceType}/{resourceId}/status")
    public Result<Void> status(@PathVariable String sourceType, @PathVariable Integer resourceId,
                               @RequestBody Map<String, String> body) {
        String status = body.get("status");
        if (status == null || !java.util.Set.of("completed", "failed", "disabled").contains(status)) {
            return Result.error(400, "无效的索引状态");
        }
        String error = body.get("error");
        if (error != null && error.length() > 500) error = error.substring(0, 500);
        if ("public".equals(sourceType)) {
            if (publicResources.findById(resourceId) == null) return Result.error(404, "资源不存在");
            publicResources.updateAiIndexStatus(resourceId, status, error);
        } else if ("personal".equals(sourceType)) {
            if (personalResources.findById(resourceId) == null) return Result.error(404, "资源不存在");
            personalResources.updateAiIndexStatus(resourceId, status, error);
        } else {
            return Result.error(400, "无效的资源类型");
        }
        return Result.success();
    }

    private String signedUrl(String raw) {
        return raw == null || raw.isBlank() ? "" : oss.resolveDownloadUrl(raw, 60);
    }

    private String detectedFileType(String... candidates) {
        for (String value : candidates) {
            if (value == null) continue;
            String clean = value.split("\\?", 2)[0].toLowerCase(java.util.Locale.ROOT);
            if (clean.endsWith(".pdf") || clean.equals("pdf")) return "pdf";
            if (clean.endsWith(".docx") || clean.endsWith(".doc") || clean.equals("word")) return "word";
            if (clean.endsWith(".pptx") || clean.endsWith(".ppt") || clean.equals("ppt")) return "ppt";
            if (clean.endsWith(".txt") || clean.endsWith(".md") || clean.equals("txt")) return "txt";
            if (clean.matches(".*\\.(png|jpg|jpeg|webp)$") || clean.equals("image")) return "image";
            if (clean.matches(".*\\.(mp3|wav|m4a)$") || clean.equals("audio")) return "audio";
            if (clean.matches(".*\\.(mp4|mov|webm)$") || clean.equals("video")) return "video";
        }
        return "other";
    }
}
