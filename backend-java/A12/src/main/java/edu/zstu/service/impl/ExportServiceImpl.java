package edu.zstu.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.zstu.dto.ExportPrecheckDTO;
import edu.zstu.dto.ExportTaskDTO;
import edu.zstu.dto.TaskQueryDTO;
import edu.zstu.entity.Exp_Task;
import edu.zstu.entity.Ws_Page;
import edu.zstu.entity.Ws_Project;
import edu.zstu.mapper.ExpTaskMapper;
import edu.zstu.mapper.WsPageMapper;
import edu.zstu.mapper.WsProjectMapper;
import edu.zstu.service.BusinessLogService;
import edu.zstu.service.ExportService;
import edu.zstu.service.ExportProgressService;
import edu.zstu.service.PythonPptClient;
import edu.zstu.service.RedisExportTaskQueue;
import edu.zstu.utils.CurrentHolder;
import edu.zstu.utils.PageResult;
import edu.zstu.vo.ExportTaskVO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import java.util.concurrent.Executor;

@Slf4j
@Service
public class ExportServiceImpl implements ExportService {
    private final ExpTaskMapper taskMapper;
    private final WsProjectMapper projectMapper;
    private final WsPageMapper pageMapper;
    private final BusinessLogService businessLogService;
    private final PythonPptClient pythonPptClient;
    private final ObjectMapper objectMapper;
    private final Path exportDir;
    private final String publicPrefix;
    private final RedisExportTaskQueue exportTaskQueue;
    private final ExportProgressService progressService;
    private final Executor exportTaskExecutor;

    public ExportServiceImpl(ExpTaskMapper taskMapper,
                             WsProjectMapper projectMapper,
                             WsPageMapper pageMapper,
                             BusinessLogService businessLogService,
                             PythonPptClient pythonPptClient,
                             ObjectMapper objectMapper,
                             RedisExportTaskQueue exportTaskQueue,
                             ExportProgressService progressService,
                             @Qualifier("exportTaskExecutor") Executor exportTaskExecutor,
                             @Value("${a12.export.local-dir:data/exports}") String exportDir,
                             @Value("${a12.export.public-prefix:/exports}") String publicPrefix) {
        this.taskMapper = taskMapper;
        this.projectMapper = projectMapper;
        this.pageMapper = pageMapper;
        this.businessLogService = businessLogService;
        this.pythonPptClient = pythonPptClient;
        this.objectMapper = objectMapper;
        this.exportTaskQueue = exportTaskQueue;
        this.progressService = progressService;
        this.exportTaskExecutor = exportTaskExecutor;
        this.exportDir = Path.of(exportDir).toAbsolutePath().normalize();
        this.publicPrefix = publicPrefix == null || publicPrefix.isBlank() ? "/exports" : publicPrefix.replaceAll("/+$", "");
    }

    @Override
    public Map<String, Object> precheckExport(String id, ExportPrecheckDTO dto) {
        Ws_Project project = requireProject(parseId(id));
        assertProjectReadable(project);
        String exportType = normalizeType(dto.getExport_type());
        List<Ws_Page> pages = pageMapper.findByProjectId(project.getId());
        List<String> errors = new ArrayList<>();
        List<String> warnings = new ArrayList<>();
        if (!List.of("pptx", "word", "docx", "package").contains(exportType)) {
            errors.add("Unsupported export_type: " + dto.getExport_type());
        }
        if (pages.isEmpty()) {
            warnings.add("Project has no saved pages; export must provide slides or lesson_plan in config.");
        }
        return Map.of(
                "passed", errors.isEmpty(),
                "warnings", warnings,
                "errors", errors,
                "snapshot_version", dto.getSnapshot_version(),
                "export_type", exportType,
                "page_count", pages.size()
        );
    }

    @Override
    @Transactional
    public ExportTaskVO createExportTask(ExportTaskDTO dto) {
        Integer userId = requireLogin();
        Ws_Project project = requireProject(dto.getProject_id());
        assertProjectReadable(project);
        String exportType = normalizeType(dto.getExport_type());
        if (!List.of("pptx", "word", "docx", "package").contains(exportType)) {
            throw new RuntimeException("Unsupported export_type: " + dto.getExport_type());
        }

        Exp_Task task = new Exp_Task();
        task.setUser_id(userId);
        task.setProject_id(dto.getProject_id());
        task.setSnapshot_version(dto.getSnapshot_version() == null ? project.getCurrent_version() : dto.getSnapshot_version());
        task.setExport_type(exportType);
        task.setStatus("queued");
        task.setConfig(dto.getConfig() == null ? "{}" : dto.getConfig());
        task.setProgress(0);
        task.setRetry_count(0);
        task.setWorker_id("redis-export-queue");
        task.setStarted_at(null);
        task.setFile_status("generating");
        task.setQuality_report("{}");
        taskMapper.insert(task);

        dispatchAfterCommit(task.getId());
        progressService.publish(task.getId(), "queued", 0, "导出任务已进入队列");
        businessLogService.record("operation", "export", "create_task", "export_task", task.getId(),
                Map.of("project_id", dto.getProject_id(), "export_type", exportType, "status", task.getStatus()));
        return toVO(taskMapper.findById(task.getId()));
    }

    @Transactional
    public void processQueuedTask(int taskId) {
        Exp_Task task = taskMapper.findById(taskId);
        if (task == null || !"queued".equals(task.getStatus())) return;
        Ws_Project project = requireProject(task.getProject_id());
        task.setStatus("generating"); task.setProgress(10); task.setStarted_at(LocalDateTime.now());
        task.setWorker_id("redis-export-worker"); taskMapper.update(task);
        progressService.publish(taskId, "generating", 10, "正在准备课件页面和导出参数");
        try {
            progressService.publish(taskId, "generating", 35, "正在调用 Python 导出引擎");
            ExportedFile exported = generateFile(project, task, parseConfig(task.getConfig()));
            Exp_Task latest = taskMapper.findById(taskId);
            if (latest == null || "cancelled".equals(latest.getStatus())) return;
            task.setStatus("checking"); task.setProgress(90); taskMapper.update(task);
            progressService.publish(taskId, "checking", 90, "正在检查文件结构与质量报告");
            task.setStatus("success");
            task.setProgress(100);
            task.setFile_name(exported.filename());
            task.setFile_url(exported.publicUrl());
            task.setDownload_url(exported.publicUrl());
            task.setUrl_expire_at(LocalDateTime.now().plusDays(7));
            task.setFile_size(exported.size());
            task.setFile_status("available");
            task.setQuality_report(buildQualityReport(true, List.of(), exported, task));
            task.setError_msg("");
            task.setCompleted_at(LocalDateTime.now());
            taskMapper.update(task);
            progressService.publish(taskId, "success", 100, "导出完成");
        } catch (Exception e) {
            log.warn("Queued export generation failed taskId={}", taskId, e);
            task.setStatus("failed");
            task.setProgress(100);
            task.setFile_status("unavailable");
            task.setError_msg(e.getMessage());
            task.setQuality_report(buildFailureReport(e));
            task.setCompleted_at(LocalDateTime.now());
            taskMapper.update(task);
            progressService.publish(taskId, "failed", 100, e.getMessage() == null ? "导出失败" : e.getMessage());
        }
    }

    private void dispatchAfterCommit(int taskId) {
        Runnable dispatch = () -> {
            if (!exportTaskQueue.enqueue(taskId)) exportTaskExecutor.execute(() -> processQueuedTask(taskId));
        };
        if (TransactionSynchronizationManager.isActualTransactionActive()) {
            TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
                @Override public void afterCommit() { dispatch.run(); }
            });
        } else dispatch.run();
    }

    @Override
    public PageResult<ExportTaskVO> listExportTasks(TaskQueryDTO dto) {
        Integer userId = requireLogin();
        int page = dto.getPage() <= 0 ? 1 : dto.getPage();
        int size = dto.getSize() <= 0 ? 10 : dto.getSize();
        List<ExportTaskVO> all = taskMapper.findByUserId(userId).stream()
                .filter(t -> dto.getStatus() == null || dto.getStatus().isBlank() || dto.getStatus().equals(t.getStatus()))
                .map(this::toVO)
                .toList();
        int from = Math.min((page - 1) * size, all.size());
        int to = Math.min(from + size, all.size());
        return new PageResult<>(all.size(), page, size, all.subList(from, to));
    }

    @Override
    public ExportTaskVO getExportTask(String id) {
        return toVO(requireOwnedTask(id));
    }

    @Override
    public SseEmitter streamProgress(String id, String lastEventId) {
        Exp_Task task = requireOwnedTask(id);
        return progressService.stream(task.getId(), lastEventId);
    }

    @Override
    @Transactional
    public ExportTaskVO cancelExport(String id) {
        Exp_Task task = requireOwnedTask(id);
        if (!List.of("queued", "generating", "checking").contains(task.getStatus())) {
            throw new RuntimeException("Current export task cannot be cancelled");
        }
        task.setStatus("cancelled");
        task.setProgress(0);
        task.setFile_status("unavailable");
        task.setCompleted_at(LocalDateTime.now());
        taskMapper.update(task);
        progressService.publish(task.getId(), "cancelled", 0, "任务已取消");
        businessLogService.record("operation", "export", "cancel_task", "export_task", task.getId());
        return toVO(taskMapper.findById(task.getId()));
    }

    @Override
    @Transactional
    public ExportTaskVO retryExport(String id) {
        Exp_Task old = requireOwnedTask(id);
        ExportTaskDTO dto = new ExportTaskDTO(old.getProject_id(), old.getSnapshot_version(), old.getExport_type(), old.getConfig());
        ExportTaskVO task = createExportTask(dto);
        businessLogService.record("operation", "export", "retry_task", "export_task", task.getId(),
                Map.of("source_task_id", old.getId()));
        return task;
    }

    @Override
    public Map<String, Object> getQualityReport(String id) {
        Exp_Task task = requireOwnedTask(id);
        return Map.of("quality_report", task.getQuality_report() == null ? "{}" : task.getQuality_report());
    }

    @Override
    public ExportTaskVO getArtifact(String id) {
        return getExportTask(id);
    }

    @Override
    public Map<String, Object> createPreviewUrl(String id) {
        Exp_Task task = requireOwnedTask(id);
        if (!"available".equals(task.getFile_status())) {
            throw new RuntimeException("Export file is not available");
        }
        businessLogService.record("browse", "export", "preview_url", "export_task", task.getId());
        return Map.of("preview_url", task.getFile_url(), "expires_at", LocalDateTime.now().plusMinutes(30));
    }

    @Override
    public Map<String, Object> createDownloadUrl(String id) {
        Exp_Task task = requireOwnedTask(id);
        if (!"available".equals(task.getFile_status())) {
            throw new RuntimeException("Export file is not available");
        }
        // 返回带鉴权、可真正流式下载文件的接口地址（API-56A）。
        // 原先的 /exports 静态路径没有任何资源映射，浏览器下载到的只是 SPA 页面，导致成果文件损坏。
        businessLogService.record("download", "export", "download_url", "export_task", task.getId());
        return Map.of(
                "download_url", "/api/v1/export-artifacts/" + task.getId() + "/file",
                "expires_at", task.getUrl_expire_at()
        );
    }

    @Override
    public ExportFileResult getExportFile(String id) {
        Exp_Task task = requireOwnedTask(id);
        if (!"available".equals(task.getFile_status())) {
            throw new RuntimeException("导出文件不可用");
        }
        LocalDateTime expireAt = task.getUrl_expire_at();
        if (expireAt != null && LocalDateTime.now().isAfter(expireAt)) {
            throw new RuntimeException("下载链接已过期，请重新生成");
        }
        String name = task.getFile_name();
        if (name == null || name.isBlank()) {
            throw new RuntimeException("导出文件信息缺失");
        }
        Path file = exportDir.resolve(name).normalize();
        if (!file.startsWith(exportDir) || !Files.isRegularFile(file)) {
            throw new RuntimeException("导出文件不存在，可能已被清理");
        }
        try {
            // 内容类型仅按实际文件名后缀判定，避免 export_type 为 package 时把实际是 .pptx 的成果误报成 .zip。
            return new ExportFileResult(name, contentTypeFor(name), Files.readAllBytes(file));
        } catch (IOException e) {
            throw new RuntimeException("读取导出文件失败: " + e.getMessage(), e);
        }
    }

    private ExportedFile generateFile(Ws_Project project, Exp_Task task, Map<String, Object> config) throws Exception {
        List<Map<String, Object>> slides = buildSlides(project, config);
        String exportType = task.getExport_type();
        PythonPptClient.PythonFileResult result;
        if ("word".equals(exportType) || "docx".equals(exportType)) {
            Map<String, Object> lessonPlan = lessonPlanFromConfigOrGenerate(project, task, config, slides);
            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("title", stringValue(config.get("title"), project.getProject_name()));
            payload.put("filename", stringValue(config.get("filename"), defaultFilename(project, task, "docx")));
            payload.put("lesson_plan", lessonPlan);
            result = pythonPptClient.exportLessonPlanFile(payload);
        } else {
            if (slides.isEmpty()) {
                throw new RuntimeException("No slides available for PPT export");
            }
            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("title", stringValue(config.get("title"), project.getProject_name()));
            payload.put("filename", stringValue(config.get("filename"), defaultFilename(project, task, "pptx")));
            payload.put("slides", slides);
            payload.put("fidelity", stringValue(config.get("fidelity"), "dom_editable"));
            payload.put("package_static_assets", !Boolean.FALSE.equals(config.get("package_static_assets")));
            result = pythonPptClient.exportPresentationFile(payload);
        }
        return saveExportFile(result, project, task);
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> lessonPlanFromConfigOrGenerate(Ws_Project project, Exp_Task task,
                                                               Map<String, Object> config,
                                                               List<Map<String, Object>> slides) {
        Object existing = config.get("lesson_plan");
        if (existing instanceof Map<?, ?> map) {
            return new LinkedHashMap<>((Map<String, Object>) map);
        }
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("title", stringValue(config.get("title"), project.getProject_name()));
        payload.put("subject", stringValue(config.get("subject"), ""));
        payload.put("grade", stringValue(config.get("grade"), ""));
        payload.put("duration_minutes", config.get("duration_minutes"));
        payload.put("teaching_goals", stringValue(config.get("teaching_goals"), ""));
        payload.put("outline", config.getOrDefault("outline", Map.of("slides", slides)));
        payload.put("slides", slides);
        payload.put("requirements", stringValue(config.get("requirements"), ""));
        payload.put("reference_text", stringValue(config.get("reference_text"), ""));
        payload.put("user_id", String.valueOf(task.getUser_id()));
        Map<String, Object> response = pythonPptClient.generateLessonPlan(payload);
        Object data = response.get("data");
        if (data instanceof Map<?, ?> dataMap && dataMap.get("lesson_plan") instanceof Map<?, ?> planMap) {
            return new LinkedHashMap<>((Map<String, Object>) planMap);
        }
        throw new RuntimeException("Python lesson plan generation returned invalid data");
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> buildSlides(Ws_Project project, Map<String, Object> config) {
        Object configSlides = config.get("slides");
        if (configSlides instanceof List<?> list && !list.isEmpty()) {
            return list.stream()
                    .filter(Map.class::isInstance)
                    .map(item -> (Map<String, Object>) new LinkedHashMap<>((Map<String, Object>) item))
                    .toList();
        }
        List<Ws_Page> pages = pageMapper.findByProjectId(project.getId());
        List<Map<String, Object>> slides = new ArrayList<>();
        for (Ws_Page page : pages) {
            Map<String, Object> slide = parseJsonObject(page.getPage_content());
            slide.putIfAbsent("title", page.getPage_title());
            slide.putIfAbsent("page_order", page.getPage_order());
            slide.putIfAbsent("page_type", page.getPage_type());
            if (!slide.containsKey("html") && !slide.containsKey("html_content")) {
                slide.put("html", fallbackSlideHtml(page, slide));
            }
            List<Object> components = parseJsonList(page.getComponents());
            if (!components.isEmpty()) {
                slide.putIfAbsent("components", components);
            }
            slides.add(slide);
        }
        return slides;
    }

    private ExportedFile saveExportFile(PythonPptClient.PythonFileResult result, Ws_Project project, Exp_Task task) throws Exception {
        if (result.bytes == null || result.bytes.length == 0) {
            throw new RuntimeException("Python export returned empty file");
        }
        Files.createDirectories(exportDir);
        String filename = sanitizeFilename(result.filename == null || result.filename.isBlank()
                ? defaultFilename(project, task, extensionFromContentType(result.contentType, task.getExport_type()))
                : result.filename);
        filename = uniqueFilename(filename);
        Path output = exportDir.resolve(filename).normalize();
        if (!output.startsWith(exportDir)) {
            throw new RuntimeException("Invalid export filename");
        }
        Files.write(output, result.bytes);
        return new ExportedFile(filename, publicPrefix + "/" + filename, result.bytes.length, result.contentType);
    }

    private String fallbackSlideHtml(Ws_Page page, Map<String, Object> content) {
        String title = escapeHtml(page.getPage_title() == null ? "Slide " + page.getPage_order() : page.getPage_title());
        String body = escapeHtml(content.isEmpty() ? "" : toJson(content));
        return "<!doctype html><html><head><meta charset=\"UTF-8\"><style>"
                + "body{margin:0;font-family:Microsoft YaHei,Arial,sans-serif;background:#f8fafc;color:#111827}"
                + ".slide{width:1280px;height:720px;padding:64px;box-sizing:border-box}"
                + "h1{font-size:46px;margin:0 0 32px}pre{font-size:20px;white-space:pre-wrap;line-height:1.45}"
                + "</style></head><body><section class=\"slide\"><h1>"
                + title + "</h1><pre>" + body + "</pre></section></body></html>";
    }

    private Map<String, Object> parseConfig(String config) {
        if (config == null || config.isBlank()) {
            return new LinkedHashMap<>();
        }
        return parseJsonObject(config);
    }

    private Map<String, Object> parseJsonObject(String json) {
        if (json == null || json.isBlank()) {
            return new LinkedHashMap<>();
        }
        try {
            Object parsed = objectMapper.readValue(json, new TypeReference<Object>() {});
            if (parsed instanceof Map<?, ?> map) {
                @SuppressWarnings("unchecked")
                Map<String, Object> result = new LinkedHashMap<>((Map<String, Object>) map);
                return result;
            }
        } catch (Exception ignored) {
        }
        return new LinkedHashMap<>();
    }

    private List<Object> parseJsonList(String json) {
        if (json == null || json.isBlank()) {
            return List.of();
        }
        try {
            Object parsed = objectMapper.readValue(json, new TypeReference<Object>() {});
            if (parsed instanceof List<?> list) {
                return new ArrayList<>(list);
            }
        } catch (Exception ignored) {
        }
        return List.of();
    }

    private String buildQualityReport(boolean passed, List<String> warnings, ExportedFile exported, Exp_Task task) {
        Map<String, Object> report = new LinkedHashMap<>();
        report.put("overall_result", passed ? "passed" : "failed");
        report.put("error_count", 0);
        report.put("warning_count", warnings.size());
        report.put("warnings", warnings);
        report.put("file_name", exported.filename());
        report.put("file_size", exported.size());
        report.put("content_type", exported.contentType());
        report.put("export_type", task.getExport_type());
        report.put("generated_by", "redis-export-worker");
        return toJson(report);
    }

    private String buildFailureReport(Exception e) {
        return toJson(Map.of(
                "overall_result", "failed",
                "error_count", 1,
                "warning_count", 0,
                "errors", List.of(e.getMessage() == null ? e.getClass().getSimpleName() : e.getMessage())
        ));
    }

    private Exp_Task requireOwnedTask(String id) {
        Exp_Task task = taskMapper.findById(parseId(id));
        if (task == null) throw new RuntimeException("Export task not found");
        if (!Objects.equals(task.getUser_id(), requireLogin())) throw new RuntimeException("No permission to access this export task");
        return task;
    }

    private Ws_Project requireProject(Integer id) {
        Ws_Project project = projectMapper.findById(id);
        if (project == null) throw new RuntimeException("Project not found");
        return project;
    }

    private void assertProjectReadable(Ws_Project project) {
        Integer userId = requireLogin();
        if (Objects.equals(project.getUser_id(), userId)) return;
        String permissions = project.getPermissions();
        if (permissions != null && permissions.contains(String.valueOf(userId))) return;
        throw new RuntimeException("No permission to access this project");
    }

    private Integer requireLogin() {
        Integer userId = CurrentHolder.getCurrentId();
        if (userId == null) throw new RuntimeException("Not logged in");
        return userId;
    }

    private int parseId(String id) {
        try {
            return Integer.parseInt(id);
        } catch (NumberFormatException e) {
            throw new RuntimeException("Invalid ID");
        }
    }

    private String normalizeType(String exportType) {
        if (exportType == null || exportType.isBlank()) {
            throw new RuntimeException("export_type cannot be empty");
        }
        String value = exportType.trim().toLowerCase();
        if ("doc".equals(value)) return "docx";
        return value;
    }

    private String extensionFromContentType(String contentType, String exportType) {
        if ("application/zip".equals(contentType)) return "zip";
        if ("word".equals(exportType) || "docx".equals(exportType)) return "docx";
        return "pptx";
    }

    private String contentTypeFor(String filename) {
        String lower = filename == null ? "" : filename.toLowerCase();
        if (lower.endsWith(".zip")) return "application/zip";
        if (lower.endsWith(".pptx")) return "application/vnd.openxmlformats-officedocument.presentationml.presentation";
        if (lower.endsWith(".docx")) return "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
        return "application/octet-stream";
    }

    private String defaultFilename(Ws_Project project, Exp_Task task, String extension) {
        return sanitizeFilename(project.getProject_name() + "-v" + task.getSnapshot_version() + "." + extension);
    }

    private String uniqueFilename(String filename) {
        String clean = sanitizeFilename(filename);
        Path path = exportDir.resolve(clean);
        if (!Files.exists(path)) {
            return clean;
        }
        String stem = clean;
        String suffix = "";
        int dot = clean.lastIndexOf('.');
        if (dot > 0) {
            stem = clean.substring(0, dot);
            suffix = clean.substring(dot);
        }
        return stem + "-" + UUID.randomUUID().toString().substring(0, 8) + suffix;
    }

    private String sanitizeFilename(String filename) {
        String clean = filename == null || filename.isBlank() ? "export.bin" : filename.trim();
        return clean.replaceAll("[\\\\/:*?\"<>|\\r\\n]+", "_");
    }

    private String stringValue(Object value, String fallback) {
        return value == null || String.valueOf(value).isBlank() ? fallback : String.valueOf(value);
    }

    private String escapeHtml(String value) {
        return value == null ? "" : value
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\"", "&quot;");
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (Exception e) {
            return "{}";
        }
    }

    private ExportTaskVO toVO(Exp_Task task) {
        ExportTaskVO vo = new ExportTaskVO();
        BeanUtil.copyProperties(task, vo);
        return vo;
    }

    private record ExportedFile(String filename, String publicUrl, long size, String contentType) {
    }
}
