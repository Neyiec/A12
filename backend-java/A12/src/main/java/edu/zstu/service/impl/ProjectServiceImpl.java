package edu.zstu.service.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.json.JSONArray;
import cn.hutool.json.JSONUtil;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import edu.zstu.dto.*;
import edu.zstu.entity.Sys_User;
import edu.zstu.entity.Ws_Page;
import edu.zstu.entity.Ws_Project;
import edu.zstu.entity.Ws_Version;
import edu.zstu.mapper.SysUserMapper;
import edu.zstu.mapper.WsPageMapper;
import edu.zstu.mapper.WsProjectMapper;
import edu.zstu.mapper.WsVersionMapper;
import edu.zstu.service.BusinessLogService;
import edu.zstu.service.ProjectService;
import edu.zstu.utils.PageResult;
import edu.zstu.vo.PageVO;
import edu.zstu.vo.ProjectVO;
import edu.zstu.vo.VersionVO;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Service
public class ProjectServiceImpl implements ProjectService {

    private final WsProjectMapper projectMapper;
    private final WsPageMapper pageMapper;
    private final WsVersionMapper versionMapper;
    private final SysUserMapper userMapper;
    private final BusinessLogService businessLogService;

    public ProjectServiceImpl(WsProjectMapper projectMapper, WsPageMapper pageMapper,
                              WsVersionMapper versionMapper, SysUserMapper userMapper,
                              BusinessLogService businessLogService) {
        this.projectMapper = projectMapper;
        this.pageMapper = pageMapper;
        this.versionMapper = versionMapper;
        this.userMapper = userMapper;
        this.businessLogService = businessLogService;
    }

    @Override
    @Transactional
    public ProjectVO createProject(ProjectCreateDTO dto, Integer userId) {
        log.info("createProject called");
        if (dto.getProject_name() == null || dto.getProject_name().isBlank())
            throw new RuntimeException("项目名称不能为空");
        if (dto.getProject_type() == null || dto.getProject_type().isBlank())
            throw new RuntimeException("项目类型不能为空");

        Ws_Project project = new Ws_Project();
        BeanUtil.copyProperties(dto, project);
        project.setUser_id(userId);
        project.setStatus(dto.getStatus() != null ? dto.getStatus() : "draft");
        project.setCurrent_version(1);
        if (projectMapper.insert(project) <= 0) throw new RuntimeException("创建项目失败");
        businessLogService.record("operation", "project", "create", "project", project.getId(),
                Map.of("project_name", project.getProject_name(), "project_type", project.getProject_type()));

        ProjectVO vo = new ProjectVO();
        BeanUtil.copyProperties(project, vo);
        return vo;
    }

    @Override
    public PageResult<ProjectVO> listProjects(ProjectQueryDTO dto, Integer userId) {
        log.info("listProjects called");
        dto.setUser_id(userId);
        PageHelper.startPage(dto.getPage(), dto.getSize());
        List<Ws_Project> list = projectMapper.findByQuery(dto);
        PageInfo<Ws_Project> info = new PageInfo<>(list);

        List<ProjectVO> records = info.getList().stream().map(p -> {
            ProjectVO vo = new ProjectVO(); BeanUtil.copyProperties(p, vo); return vo;
        }).toList();

        PageResult<ProjectVO> r = new PageResult<>();
        r.setTotal(info.getTotal()); r.setPage(dto.getPage()); r.setSize(dto.getSize()); r.setRecords(records);
        return r;
    }

    @Override
    public ProjectVO getProject(String id, Integer userId) {
        log.info("getProject called");
        Ws_Project project = projectMapper.findById(Integer.valueOf(id));
        if (project == null) throw new RuntimeException("项目不存在");
        checkPermission(project, userId);
        return toProjectVO(project);
    }

    @Override
    @Transactional
    public ProjectVO updateProject(String id, ProjectCreateDTO dto, Integer userId) {
        log.info("updateProject called");
        Ws_Project p = findProject(id);
        checkPermission(p, userId);
        checkEditable(p);
        if (dto.getCurrent_version() == null || dto.getCurrent_version() != p.getCurrent_version())
            throw new RuntimeException("版本冲突，请刷新后重试");
        if (dto.getProject_name() != null) p.setProject_name(dto.getProject_name());
        if (dto.getProject_type() != null) p.setProject_type(dto.getProject_type());
        if (dto.getStatus() != null) p.setStatus(dto.getStatus());
        if (dto.getSnapshots() != null) p.setSnapshots(dto.getSnapshots());
        if (dto.getEdit_history() != null) p.setEdit_history(dto.getEdit_history());
        if (dto.getPermissions() != null) p.setPermissions(dto.getPermissions());
        p.setCurrent_version(p.getCurrent_version() + 1);
        projectMapper.update(p);
        businessLogService.record("operation", "project", "update", "project", p.getId(),
                Map.of("current_version", p.getCurrent_version()));
        return toProjectVO(p);
    }

    @Override
    @Transactional
    public ProjectVO addPermission(String id, ProjectPermissionDTO dto, Integer userId) {
        log.info("addPermission called");
        Ws_Project p = findProject(id);
        // 仅项目拥有者可添加授权
        if (p.getUser_id() != userId) throw new RuntimeException("仅项目创建者可添加授权");
        if (dto.getUser_id() == null) throw new RuntimeException("用户ID不能为空");
        // 校验被授权用户存在
        Sys_User targetUser = userMapper.findById(dto.getUser_id());
        if (targetUser == null) throw new RuntimeException("指定用户不存在");
        // 解析现有权限列表
        JSONArray arr;
        if (p.getPermissions() != null && !p.getPermissions().isBlank()) {
            arr = JSONUtil.parseArray(p.getPermissions());
        } else {
            arr = new JSONArray();
        }
        // 去重添加
        if (!arr.contains(dto.getUser_id())) {
            arr.add(dto.getUser_id());
        }
        p.setPermissions(JSONUtil.toJsonStr(arr));
        projectMapper.update(p);
        businessLogService.record("operation", "project", "add_permission", "project", p.getId(),
                Map.of("authorized_user_id", dto.getUser_id()));
        return toProjectVO(p);
    }

    @Override
    @Transactional
    public ProjectVO copyProject(String id, ProjectCopyDTO dto, Integer userId) {
        log.info("copyProject called");
        Ws_Project src = findProject(id);
        checkPermission(src, userId);
        Ws_Project np = new Ws_Project();
        np.setUser_id(userId);
        np.setProject_name(dto.getNew_name() != null ? dto.getNew_name() : src.getProject_name() + " - 副本");
        np.setProject_type(src.getProject_type());
        np.setStatus("draft");
        np.setCurrent_version(1);
        np.setPermissions(src.getPermissions());
        projectMapper.insert(np);
        List<Ws_Page> pages = pageMapper.findByProjectId(src.getId());
        for (Ws_Page page : pages) {
            Ws_Page newPage = new Ws_Page();
            BeanUtil.copyProperties(page, newPage, "id", "project_id", "created_at", "updated_at");
            newPage.setProject_id(np.getId());
            pageMapper.insert(newPage);
        }
        businessLogService.record("operation", "project", "copy", "project", np.getId(),
                Map.of("source_project_id", src.getId()));
        return toProjectVO(np);
    }

    // ==================== API-22 ~ 31 ====================

    @Override
    @Transactional
    public ProjectVO archiveProject(String id, Integer userId) {
        log.info("archiveProject called");
        Ws_Project p = findProject(id);
        checkPermission(p, userId);
        projectMapper.updateStatus(p.getId(), "archived");
        p.setStatus("archived");
        businessLogService.record("operation", "project", "archive", "project", p.getId());
        return toProjectVO(p);
    }

    @Override
    @Transactional
    public ProjectVO restoreProject(String id, Integer userId) {
        log.info("restoreProject called");
        Ws_Project p = findProject(id);
        checkPermission(p, userId);
        projectMapper.updateStatus(p.getId(), "draft");
        p.setStatus("draft");
        businessLogService.record("operation", "project", "restore", "project", p.getId());
        return toProjectVO(p);
    }

    @Override
    @Transactional
    public void deleteProject(String id, Integer userId) {
        log.info("deleteProject called");
        Ws_Project p = findProject(id);
        checkPermission(p, userId);
        int projectId = p.getId();
        pageMapper.deleteByProjectId(projectId);
        versionMapper.deleteByProjectId(projectId);
        projectMapper.deleteById(projectId);
        businessLogService.record("operation", "project", "delete", "project", projectId);
    }

    @Override
    public PageVO aiRevision(String id, AiRevisionDTO dto, Integer userId) {
        log.info("aiRevision called");
        Ws_Project p = findProject(id);
        checkPermission(p, userId);
        checkEditable(p);
        // 暂不接入 AI，仅做校验返回空 PageVO
        return new PageVO();
    }

    @Override
    @Transactional
    public PageVO addComponent(String id, PageDTO dto, Integer userId) {
        log.info("addComponent called");
        Ws_Project p = findProject(id);
        checkPermission(p, userId);
        checkEditable(p);
        Ws_Page page = new Ws_Page();
        BeanUtil.copyProperties(dto, page);
        page.setProject_id(Integer.valueOf(id));
        pageMapper.insert(page);
        businessLogService.record("operation", "project", "add_component", "page", page.getId(),
                Map.of("project_id", Integer.valueOf(id)));
        PageVO vo = new PageVO(); BeanUtil.copyProperties(page, vo);
        return vo;
    }

    @Override
    @Transactional
    public PageVO updateComponent(String id, String componentId, PageDTO dto, Integer userId) {
        log.info("updateComponent called");
        Ws_Project p = findProject(id);
        checkPermission(p, userId);
        checkEditable(p);
        Ws_Page page = pageMapper.findById(Integer.valueOf(componentId));
        if (page == null) throw new RuntimeException("页面不存在");
        if (page.getProject_id() != Integer.valueOf(id)) throw new RuntimeException("页面不属于该项目");
        if (dto.getPage_content() != null) page.setPage_content(dto.getPage_content());
        if (dto.getComponents() != null) page.setComponents(dto.getComponents());
        pageMapper.update(page);
        businessLogService.record("operation", "project", "update_component", "page", page.getId(),
                Map.of("project_id", Integer.valueOf(id)));
        PageVO vo = new PageVO(); BeanUtil.copyProperties(page, vo);
        return vo;
    }

    @Override
    @Transactional
    public Map<String, Object> saveVersion(String id, VersionCreateDTO dto, Integer userId) {
        Ws_Project p = findProject(id);
        checkPermission(p, userId);
        checkEditable(p);
        int nextNum = versionMapper.findMaxVersionNumber(Integer.valueOf(id)) + 1;
        Ws_Version v = new Ws_Version();
        v.setProject_id(Integer.valueOf(id));
        v.setVersion_number(nextNum);
        v.setDescription(dto.getDescription());
        versionMapper.insert(v);
        businessLogService.record("operation", "project", "save_version", "project_version", v.getId(),
                Map.of("project_id", Integer.valueOf(id), "version_number", v.getVersion_number()));
        Map<String, Object> r = new HashMap<>();
        r.put("version_id", v.getId());
        r.put("version_number", v.getVersion_number());
        return r;
    }

    @Override
    public PageResult<VersionVO> listVersions(String id, PageQuery pageQuery, Integer userId) {
        log.info("listVersions called");
        Ws_Project p = findProject(id);
        checkPermission(p, userId);
        PageHelper.startPage(pageQuery.getPage(), pageQuery.getSize());
        List<Ws_Version> list = versionMapper.findByProjectId(Integer.valueOf(id));
        PageInfo<Ws_Version> info = new PageInfo<>(list);

        List<VersionVO> records = info.getList().stream().map(v -> {
            VersionVO vo = new VersionVO();
            vo.setVersion_id(v.getId());
            vo.setVersion_number(v.getVersion_number());
            vo.setDescription(v.getDescription());
            vo.setCreated_at(v.getCreated_at());
            return vo;
        }).toList();

        PageResult<VersionVO> r = new PageResult<>();
        r.setTotal(info.getTotal()); r.setPage(pageQuery.getPage());
        r.setSize(pageQuery.getSize()); r.setRecords(records);
        return r;
    }

    @Override
    public Map<String, Object> versionDiff(String id, String versionId, Integer compareVersionId, Integer userId) {
        Ws_Project p = findProject(id);
        checkPermission(p, userId);
        Ws_Version v1 = versionMapper.findById(Integer.valueOf(versionId));
        if (v1 == null) throw new RuntimeException("版本不存在");
        Map<String, Object> r = new HashMap<>();
        r.put("differences", new Object[]{});
        r.put("summary", compareVersionId != null
                ? "版本 " + v1.getVersion_number() + " 与版本 " + compareVersionId + " 的对比"
                : "版本 " + v1.getVersion_number() + " 与当前版本的对比");
        return r;
    }

    @Override
    @Transactional
    public ProjectVO restoreVersion(String id, String versionId, Integer userId) {
        log.info("restoreVersion called");
        Ws_Project p = findProject(id);
        checkPermission(p, userId);
        Ws_Version v = versionMapper.findById(Integer.valueOf(versionId));
        if (v == null) throw new RuntimeException("版本不存在");
        p.setCurrent_version(p.getCurrent_version() + 1);
        projectMapper.update(p);
        businessLogService.record("operation", "project", "restore_version", "project", p.getId(),
                Map.of("source_version_id", Integer.valueOf(versionId), "current_version", p.getCurrent_version()));
        return toProjectVO(p);
    }

    // ==================== 内部辅助 ====================

    private Ws_Project findProject(String id) {
        Ws_Project p = projectMapper.findById(Integer.valueOf(id));
        if (p == null) throw new RuntimeException("项目不存在");
        return p;
    }

    private void checkPermission(Ws_Project p, Integer userId) {
        // 项目拥有者直接通过
        if (p.getUser_id() == userId) return;
        // 被授权的用户也通过
        if (p.getPermissions() != null && !p.getPermissions().isBlank()) {
            JSONArray arr = JSONUtil.parseArray(p.getPermissions());
            if (arr.contains(userId)) return;
        }
        throw new RuntimeException("无权操作该项目");
    }

    private void checkEditable(Ws_Project p) {
        if (!"draft".equals(p.getStatus()) && !"editing".equals(p.getStatus())) {
            throw new RuntimeException("项目当前状态不可编辑");
        }
    }

    private ProjectVO toProjectVO(Ws_Project p) {
        ProjectVO vo = new ProjectVO(); BeanUtil.copyProperties(p, vo); return vo;
    }
}
