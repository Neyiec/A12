package edu.zstu.service.impl;

import cn.hutool.core.bean.BeanUtil;
import edu.zstu.dto.ExportPrecheckDTO;
import edu.zstu.dto.ExportTaskDTO;
import edu.zstu.dto.TaskQueryDTO;
import edu.zstu.entity.Exp_Task;
import edu.zstu.entity.Ws_Project;
import edu.zstu.mapper.ExpTaskMapper;
import edu.zstu.mapper.WsProjectMapper;
import edu.zstu.service.BusinessLogService;
import edu.zstu.service.ExportService;
import edu.zstu.utils.CurrentHolder;
import edu.zstu.utils.PageResult;
import edu.zstu.vo.ExportTaskVO;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Service
public class ExportServiceImpl implements ExportService {
    private final ExpTaskMapper taskMapper;
    private final WsProjectMapper projectMapper;
    private final BusinessLogService businessLogService;

    public ExportServiceImpl(ExpTaskMapper taskMapper, WsProjectMapper projectMapper,
                             BusinessLogService businessLogService) {
        this.taskMapper = taskMapper;
        this.projectMapper = projectMapper;
        this.businessLogService = businessLogService;
    }

    @Override
    public Map<String, Object> precheckExport(String id, ExportPrecheckDTO dto) {
        Ws_Project project = requireProject(parseId(id));
        assertProjectReadable(project);
        return Map.of("passed", true, "warnings", List.of(), "errors", List.of(),
                "snapshot_version", dto.getSnapshot_version(), "export_type", dto.getExport_type());
    }

    @Override
    @Transactional
    public ExportTaskVO createExportTask(ExportTaskDTO dto) {
        Integer userId = requireLogin();
        Ws_Project project = requireProject(dto.getProject_id());
        assertProjectReadable(project);
        if (dto.getExport_type() == null || dto.getExport_type().isBlank()) throw new RuntimeException("导出类型不能为空");

        Exp_Task task = new Exp_Task();
        task.setUser_id(userId);
        task.setProject_id(dto.getProject_id());
        task.setSnapshot_version(dto.getSnapshot_version() == null ? project.getCurrent_version() : dto.getSnapshot_version());
        task.setExport_type(dto.getExport_type());
        task.setStatus("success");
        task.setConfig(dto.getConfig() == null ? "{}" : dto.getConfig());
        task.setFile_name(project.getProject_name() + "." + normalizeExt(dto.getExport_type()));
        task.setFile_url("/exports/project-" + dto.getProject_id() + "-v" + task.getSnapshot_version() + "." + normalizeExt(dto.getExport_type()));
        task.setFile_size(0L);
        task.setFile_status("available");
        task.setQuality_report("{\"check_items\":[],\"error_count\":0,\"warning_count\":0,\"overall_result\":\"passed\"}");
        task.setCompleted_at(LocalDateTime.now());
        taskMapper.insert(task);
        businessLogService.record("operation", "export", "create_task", "export_task", task.getId(),
                Map.of("project_id", dto.getProject_id(), "export_type", dto.getExport_type()));
        return toVO(task);
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
    @Transactional
    public ExportTaskVO cancelExport(String id) {
        Exp_Task task = requireOwnedTask(id);
        if (!List.of("queued", "generating", "checking").contains(task.getStatus())) {
            throw new RuntimeException("当前状态不可取消");
        }
        task.setStatus("cancelled");
        task.setCompleted_at(LocalDateTime.now());
        taskMapper.update(task);
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
        businessLogService.record("browse", "export", "preview_url", "export_task", task.getId());
        return Map.of("preview_url", task.getFile_url(), "expires_at", LocalDateTime.now().plusMinutes(30));
    }

    @Override
    public Map<String, Object> createDownloadUrl(String id) {
        Exp_Task task = requireOwnedTask(id);
        String url = task.getDownload_url() == null ? task.getFile_url() : task.getDownload_url();
        businessLogService.record("download", "export", "download_url", "export_task", task.getId());
        return Map.of("download_url", url, "expires_at", LocalDateTime.now().plusMinutes(30));
    }

    private Exp_Task requireOwnedTask(String id) {
        Exp_Task task = taskMapper.findById(parseId(id));
        if (task == null) throw new RuntimeException("导出任务不存在");
        if (task.getUser_id() != requireLogin()) throw new RuntimeException("无权访问该导出任务");
        return task;
    }

    private Ws_Project requireProject(Integer id) {
        Ws_Project project = projectMapper.findById(id);
        if (project == null) throw new RuntimeException("项目不存在");
        return project;
    }

    private void assertProjectReadable(Ws_Project project) {
        Integer userId = requireLogin();
        if (project.getUser_id() == userId) return;
        String permissions = project.getPermissions();
        if (permissions != null && permissions.contains(String.valueOf(userId))) return;
        throw new RuntimeException("无权访问该项目");
    }

    private Integer requireLogin() {
        Integer userId = CurrentHolder.getCurrentId();
        if (userId == null) throw new RuntimeException("未登录");
        return userId;
    }

    private int parseId(String id) {
        try {
            return Integer.parseInt(id);
        } catch (NumberFormatException e) {
            throw new RuntimeException("ID格式错误");
        }
    }

    private String normalizeExt(String exportType) {
        return "word".equals(exportType) ? "docx" : exportType;
    }

    private ExportTaskVO toVO(Exp_Task task) {
        ExportTaskVO vo = new ExportTaskVO();
        BeanUtil.copyProperties(task, vo);
        return vo;
    }
}
