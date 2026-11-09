package edu.zstu.service.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.json.JSONArray;
import cn.hutool.json.JSONObject;
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
import edu.zstu.utils.PageTitleUtil;
import edu.zstu.vo.PageVO;
import edu.zstu.vo.ProjectVO;
import edu.zstu.vo.SubjectComponentValidateVO;
import edu.zstu.vo.VersionVO;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Service
public class ProjectServiceImpl implements ProjectService {

    /** 与前端 subjectToolOptions / Python subject_tools.SUBJECT_TOOL_TYPES 保持一致的 10 种学科工具类型。 */
    private static final Set<String> SUBJECT_COMPONENT_TYPES = Set.of(
            "math_formula",
            "geometry",
            "coordinate_system",
            "solid_geometry",
            "chinese_tianzige",
            "english_four_line",
            "chemical_formula",
            "mermaid_diagram",
            "chart",
            "table"
    );

    private static final Set<String> SOLID_SHAPES = Set.of("cube", "cuboid", "pyramid", "cylinder", "cone", "sphere");
    private static final List<String> SOLID_DIMENSION_KEYS = List.of("length", "width", "height", "radius");
    private static final Map<String, Object> SOLID_DEFAULT_DIMENSIONS = Map.of("length", 4, "width", 3, "height", 5, "radius", 2);

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
        log.info("createProject userId={}, projectName={}, projectType={}", userId, dto.getProject_name(), dto.getProject_type());
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
        log.info("createProject success userId={}, projectId={}", userId, project.getId());
        businessLogService.record("operation", "project", "create", "project", project.getId(),
                Map.of("project_name", project.getProject_name(), "project_type", project.getProject_type()));

        ProjectVO vo = new ProjectVO();
        BeanUtil.copyProperties(project, vo);
        return vo;
    }

    @Override
    public PageResult<ProjectVO> listProjects(ProjectQueryDTO dto, Integer userId) {
        log.info("listProjects userId={}, status={}, page={}, size={}", userId, dto.getStatus(), dto.getPage(), dto.getSize());
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
        log.info("getProject userId={}, projectId={}", userId, id);
        Ws_Project project = projectMapper.findById(Integer.valueOf(id));
        if (project == null) throw new RuntimeException("项目不存在");
        checkPermission(project, userId);
        return toProjectVO(project);
    }

    @Override
    @Transactional
    public ProjectVO updateProject(String id, ProjectCreateDTO dto, Integer userId) {
        log.info("updateProject userId={}, projectId={}, requestVersion={}", userId, id, dto.getCurrent_version());
        Ws_Project p = findProject(id);
        checkPermission(p, userId);
        checkEditable(p);
        if (dto.getCurrent_version() == null || dto.getCurrent_version() != p.getCurrent_version())
            throw new RuntimeException("版本冲突，请刷新后重试");
        int expectedVersion = p.getCurrent_version();
        if (dto.getProject_name() != null) p.setProject_name(dto.getProject_name());
        if (dto.getProject_type() != null) p.setProject_type(dto.getProject_type());
        if (dto.getStatus() != null) p.setStatus(dto.getStatus());
        if (dto.getSnapshots() != null) p.setSnapshots(dto.getSnapshots());
        if (dto.getEdit_history() != null) p.setEdit_history(dto.getEdit_history());
        if (dto.getPermissions() != null) p.setPermissions(dto.getPermissions());
        p.setCurrent_version(expectedVersion + 1);
        if (projectMapper.updateWithVersion(p, expectedVersion) <= 0) {
            throw new RuntimeException("鐗堟湰鍐茬獊锛岃鍒锋柊鍚庨噸璇?");
        }
        log.info("updateProject success userId={}, projectId={}, newVersion={}", userId, p.getId(), p.getCurrent_version());
        businessLogService.record("operation", "project", "update", "project", p.getId(),
                Map.of("current_version", p.getCurrent_version()));
        return toProjectVO(p);
    }

    @Override
    @Transactional
    public ProjectVO addPermission(String id, ProjectPermissionDTO dto, Integer userId) {
        log.info("addPermission userId={}, projectId={}, targetUserId={}", userId, id, dto.getUser_id());
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
        log.info("copyProject userId={}, sourceProjectId={}, newName={}", userId, id, dto.getNew_name());
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
        log.info("copyProject success userId={}, sourceProjectId={}, newProjectId={}", userId, src.getId(), np.getId());
        businessLogService.record("operation", "project", "copy", "project", np.getId(),
                Map.of("source_project_id", src.getId()));
        return toProjectVO(np);
    }

    // ==================== API-22 ~ 31 ====================

    @Override
    @Transactional
    public ProjectVO archiveProject(String id, Integer userId) {
        log.info("archiveProject userId={}, projectId={}", userId, id);
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
        log.info("restoreProject userId={}, projectId={}", userId, id);
        Ws_Project p = projectMapper.findByIdIncludingDeleted(Integer.valueOf(id));
        if (p == null) throw new RuntimeException("椤圭洰涓嶅瓨鍦?");
        checkPermission(p, userId);
        projectMapper.restoreById(p.getId(), "draft");
        p.setStatus("draft");
        p.setDeleted_at(null);
        businessLogService.record("operation", "project", "restore", "project", p.getId());
        return toProjectVO(p);
    }

    @Override
    @Transactional
    public void deleteProject(String id, Integer userId) {
        log.info("deleteProject userId={}, projectId={}", userId, id);
        Ws_Project p = findProject(id);
        checkPermission(p, userId);
        int projectId = p.getId();
        projectMapper.softDeleteById(projectId);
        businessLogService.record("operation", "project", "delete", "project", projectId);
    }

    @Override
    public PageVO aiRevision(String id, AiRevisionDTO dto, Integer userId) {
        log.info("aiRevision userId={}, projectId={}", userId, id);
        Ws_Project p = findProject(id);
        checkPermission(p, userId);
        checkEditable(p);
        // 暂不接入 AI，仅做校验返回空 PageVO
        return new PageVO();
    }


    @Override
    public List<PageVO> listPages(String id, Integer userId) {
        Ws_Project p = findProject(id);
        checkPermission(p, userId);
        return pageMapper.findByProjectId(p.getId()).stream().map(this::toPageVO).toList();
    }

    @Override
    public PageVO getPage(String id, String pageId, Integer userId) {
        Ws_Project p = findProject(id);
        checkPermission(p, userId);
        Ws_Page page = requireProjectPage(p.getId(), Integer.valueOf(pageId));
        return toPageVO(page);
    }

    @Override
    @Transactional
    public PageVO createPage(String id, PageDTO dto, Integer userId) {
        Ws_Project p = findProject(id);
        checkPermission(p, userId);
        checkEditable(p);
        validatePageJson(dto);
        Ws_Page page = new Ws_Page();
        page.setProject_id(p.getId());
        page.setPage_order(dto.getPage_order() == null ? nextPageOrder(p.getId()) : dto.getPage_order());
        page.setPage_type(defaultString(dto.getPage_type(), "content"));
        page.setPage_title(PageTitleUtil.forStorage(dto.getPage_title()));
        page.setPage_content(defaultString(dto.getPage_content(), "{}"));
        page.setComponents(defaultString(dto.getComponents(), "[]"));
        page.setPage_version(1);
        page.setClient_version(dto.getClient_version());
        page.setAutosave(Boolean.TRUE.equals(dto.getAutosave()));
        page.setDirty(Boolean.TRUE.equals(dto.getDirty()));
        pageMapper.insert(page);
        bumpProjectVersion(p);
        businessLogService.record("operation", "project", "create_page", "page", page.getId(), Map.of("project_id", p.getId()));
        return toPageVO(pageMapper.findById(page.getId()));
    }

    @Override
    @Transactional
    public PageVO savePage(String id, String pageId, PageDTO dto, Integer userId) {
        Ws_Project p = findProject(id);
        checkPermission(p, userId);
        checkEditable(p);
        validatePageJson(dto);
        Ws_Page current = requireProjectPage(p.getId(), Integer.valueOf(pageId));
        Integer expectedVersion = dto.getExpected_page_version();
        if (expectedVersion == null) {
            throw new RuntimeException("expected_page_version is required to avoid overwriting concurrent edits");
        }
        Ws_Page page = new Ws_Page();
        page.setId(current.getId());
        page.setPage_order(dto.getPage_order());
        page.setPage_type(dto.getPage_type());
        page.setPage_title(PageTitleUtil.forStorage(dto.getPage_title()));
        page.setPage_content(dto.getPage_content());
        page.setComponents(dto.getComponents());
        page.setClient_version(dto.getClient_version());
        page.setAutosave(Boolean.TRUE.equals(dto.getAutosave()));
        page.setDirty(Boolean.TRUE.equals(dto.getDirty()));
        if (pageMapper.updateWithVersion(page, expectedVersion) <= 0) {
            throw new RuntimeException("Version conflict, please refresh and retry");
        }
        bumpProjectVersion(p);
        businessLogService.record("operation", "project", Boolean.TRUE.equals(dto.getAutosave()) ? "autosave_page" : "save_page", "page", current.getId(), Map.of("project_id", p.getId()));
        return toPageVO(pageMapper.findById(current.getId()));
    }

    @Override
    @Transactional
    public List<PageVO> batchSavePages(String id, PageBatchSaveDTO dto, Integer userId) {
        Ws_Project p = findProject(id);
        checkPermission(p, userId);
        checkEditable(p);
        if (dto == null || dto.getPages() == null) throw new RuntimeException("pages cannot be empty");
        if (dto.getCurrent_version() != null && !Objects.equals(dto.getCurrent_version(), p.getCurrent_version())) {
            throw new RuntimeException("Version conflict, please refresh and retry");
        }
        List<PageVO> saved = new ArrayList<>();
        for (PageDTO pageDto : dto.getPages()) {
            if (pageDto.getClient_version() == null) pageDto.setClient_version(dto.getClient_version());
            if (pageDto.getAutosave() == null) pageDto.setAutosave(dto.getAutosave());
            if (pageDto.getPage_id() == null) {
                saved.add(createPage(id, pageDto, userId));
            } else {
                saved.add(savePage(id, String.valueOf(pageDto.getPage_id()), pageDto, userId));
            }
        }
        return saved;
    }

    @Override
    @Transactional
    public void deletePage(String id, String pageId, Integer userId) {
        Ws_Project p = findProject(id);
        checkPermission(p, userId);
        checkEditable(p);
        Ws_Page page = requireProjectPage(p.getId(), Integer.valueOf(pageId));
        pageMapper.deleteByIdAndProjectId(page.getId(), p.getId());
        bumpProjectVersion(p);
        businessLogService.record("operation", "project", "delete_page", "page", page.getId(), Map.of("project_id", p.getId()));
    }

    @Override
    public SubjectComponentValidateVO validateComponent(SubjectComponentDTO dto, Integer userId) {
        if (userId == null) throw new RuntimeException("unauthorized");
        return validateSubjectComponent(dto, true);
    }

    @Override
    @Transactional
    public PageVO addComponent(String id, PageDTO dto, Integer userId) {
        log.info("addComponent userId={}, projectId={}, pageType={}", userId, id, dto.getPage_type());
        return createPage(id, dto, userId);
    }

    @Override
    @Transactional
    public PageVO updateComponent(String id, String componentId, PageDTO dto, Integer userId) {
        log.info("updateComponent userId={}, projectId={}, componentId={}", userId, id, componentId);
        Ws_Page page = requireProjectPage(Integer.valueOf(id), Integer.valueOf(componentId));
        if (dto.getExpected_page_version() == null) {
            dto.setExpected_page_version(page.getPage_version() == null ? 1 : page.getPage_version());
        }
        return savePage(id, componentId, dto, userId);
    }

    @Override
    @Transactional
    public Map<String, Object> saveVersion(String id, VersionCreateDTO dto, Integer userId) {
        log.info("saveVersion userId={}, projectId={}", userId, id);
        Ws_Project p = findProject(id);
        checkPermission(p, userId);
        checkEditable(p);
        int nextNum = versionMapper.findMaxVersionNumber(Integer.valueOf(id)) + 1;
        Ws_Version v = new Ws_Version();
        v.setProject_id(Integer.valueOf(id));
        v.setVersion_number(nextNum);
        v.setDescription(dto.getDescription());
        v.setSnapshot_data(buildProjectSnapshot(p));
        v.setCreated_by(userId);
        versionMapper.insert(v);
        log.info("saveVersion success userId={}, projectId={}, versionId={}, versionNumber={}", userId, id, v.getId(), v.getVersion_number());
        businessLogService.record("operation", "project", "save_version", "project_version", v.getId(),
                Map.of("project_id", Integer.valueOf(id), "version_number", v.getVersion_number()));
        Map<String, Object> r = new HashMap<>();
        r.put("version_id", v.getId());
        r.put("version_number", v.getVersion_number());
        return r;
    }

    @Override
    public PageResult<VersionVO> listVersions(String id, PageQuery pageQuery, Integer userId) {
        log.info("listVersions userId={}, projectId={}, page={}, size={}", userId, id, pageQuery.getPage(), pageQuery.getSize());
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
            vo.setSnapshot_data(v.getSnapshot_data());
            vo.setCreated_by(v.getCreated_by());
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
        log.info("versionDiff userId={}, projectId={}, versionId={}, compareVersionId={}", userId, id, versionId, compareVersionId);
        Ws_Project p = findProject(id);
        checkPermission(p, userId);
        Ws_Version v1 = versionMapper.findById(Integer.valueOf(versionId));
        if (v1 == null || v1.getProject_id() != p.getId()) throw new RuntimeException("版本不存在或不属于当前项目");
        if (compareVersionId != null) {
            Ws_Version comparison = versionMapper.findById(compareVersionId);
            if (comparison == null || comparison.getProject_id() != p.getId())
                throw new RuntimeException("对比版本不属于当前项目");
        }
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
        return restoreVersion(id, versionId, userId, true);
    }

    @Override
    @Transactional
    public ProjectVO restoreVersion(String id, String versionId, Integer userId, boolean backup) {
        log.info("restoreVersion userId={}, projectId={}, versionId={}", userId, id, versionId);
        Ws_Project p = findProject(id);
        checkPermission(p, userId);
        checkEditable(p);
        Ws_Version v = versionMapper.findById(Integer.valueOf(versionId));
        if (v == null || v.getProject_id() != p.getId()) throw new RuntimeException("版本不存在或不属于当前项目");
        // Validate the complete target before any backup or destructive page replacement.
        validateVersionSnapshot(v.getSnapshot_data());
        if (backup) {
            VersionCreateDTO backupRequest = new VersionCreateDTO();
            backupRequest.setDescription("恢复快照 v" + v.getVersion_number() + " 前的自动备份");
            saveVersion(id, backupRequest, userId);
        }
        int expectedVersion = p.getCurrent_version();
        restoreSnapshot(p, v.getSnapshot_data());
        p.setCurrent_version(expectedVersion + 1);
        if (projectMapper.restoreContentWithVersion(p, expectedVersion) != 1)
            throw new RuntimeException("版本冲突，请刷新后重试恢复");
        businessLogService.record("operation", "project", "restore_version", "project", p.getId(),
                Map.of("source_version_id", Integer.valueOf(versionId), "current_version", p.getCurrent_version(), "backup_created", backup));
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
        ProjectVO vo = new ProjectVO();
        BeanUtil.copyProperties(p, vo);
        vo.setPages(pageMapper.findByProjectId(p.getId()).stream().map(this::toPageVO).toList());
        return vo;
    }

    private PageVO toPageVO(Ws_Page page) {
        PageVO vo = new PageVO();
        BeanUtil.copyProperties(page, vo);
        return vo;
    }

    private Ws_Page requireProjectPage(Integer projectId, Integer pageId) {
        Ws_Page page = pageMapper.findById(pageId);
        if (page == null) throw new RuntimeException("页面不存在");
        if (!Objects.equals(page.getProject_id(), projectId)) throw new RuntimeException("页面不属于该项目");
        return page;
    }

    private int nextPageOrder(Integer projectId) {
        return pageMapper.findByProjectId(projectId).stream()
                .map(Ws_Page::getPage_order)
                .filter(Objects::nonNull)
                .max(Integer::compareTo)
                .orElse(0) + 1;
    }

    private void bumpProjectVersion(Ws_Project project) {
        project.setCurrent_version(project.getCurrent_version() + 1);
        projectMapper.update(project);
    }

    private void validatePageJson(PageDTO dto) {
        if (dto == null) throw new RuntimeException("Page data cannot be empty");
        validateJsonField("page_content", dto.getPage_content(), true, true);
        validateJsonField("components", dto.getComponents(), true, false);
        validatePageComponents(dto.getComponents());
    }

    private void validateJsonField(String field, String value, boolean optional, boolean objectExpected) {
        if (value == null || value.isBlank()) {
            if (optional) return;
            throw new RuntimeException(field + " cannot be empty");
        }
        String trimmed = value.trim();
        if (objectExpected && !trimmed.startsWith("{")) {
            throw new RuntimeException(field + " must be a JSON object");
        }
        if (!objectExpected && !trimmed.startsWith("[")) {
            throw new RuntimeException(field + " must be a JSON array");
        }
        try {
            JSONUtil.parse(value);
        } catch (Exception e) {
            throw new RuntimeException(field + " must be valid JSON: " + e.getMessage());
        }
    }

    private void validatePageComponents(String componentsJson) {
        if (componentsJson == null || componentsJson.isBlank()) return;
        JSONArray components = JSONUtil.parseArray(componentsJson);
        for (int i = 0; i < components.size(); i++) {
            Object item = components.get(i);
            if (!(item instanceof JSONObject)) {
                continue;
            }
            JSONObject obj = (JSONObject) item;
            String type = obj.getStr("type");
            if (type == null || !SUBJECT_COMPONENT_TYPES.contains(type)) {
                continue;
            }
            SubjectComponentDTO component = new SubjectComponentDTO(
                    obj.getStr("component_id", obj.getStr("id")),
                    type,
                    jsonObjectToMap(obj.getJSONObject("data")),
                    jsonObjectToMap(obj.getJSONObject("render")),
                    jsonObjectToMap(obj.getJSONObject("style"))
            );
            SubjectComponentValidateVO result = validateSubjectComponent(component, false);
            if (!Boolean.TRUE.equals(result.getValid())) {
                throw new RuntimeException("components[" + i + "] invalid: " + String.join("; ", result.getErrors()));
            }
        }
    }

    private SubjectComponentValidateVO validateSubjectComponent(SubjectComponentDTO dto, boolean rejectUnknownType) {
        List<String> errors = new ArrayList<>();
        List<String> warnings = new ArrayList<>();
        Map<String, Object> renderHint = new LinkedHashMap<>();
        SubjectComponentDTO normalized = new SubjectComponentDTO();

        if (dto == null) {
            return new SubjectComponentValidateVO(false, null, renderHint, List.of("component cannot be empty"), warnings);
        }

        String type = dto.getType() == null ? "" : dto.getType().trim();
        normalized.setComponent_id(dto.getComponent_id());
        normalized.setType(type);
        normalized.setData(new LinkedHashMap<>(dto.getData() == null ? Map.of() : dto.getData()));
        normalized.setRender(new LinkedHashMap<>(dto.getRender() == null ? Map.of() : dto.getRender()));
        normalized.setStyle(new LinkedHashMap<>(dto.getStyle() == null ? Map.of() : dto.getStyle()));

        if (type.isBlank()) {
            errors.add("type is required");
            return new SubjectComponentValidateVO(false, normalized, renderHint, errors, warnings);
        }
        if (!SUBJECT_COMPONENT_TYPES.contains(type)) {
            if (rejectUnknownType) {
                errors.add("unsupported component type: " + type);
            }
            return new SubjectComponentValidateVO(errors.isEmpty(), normalized, renderHint, errors, warnings);
        }

        Map<String, Object> data = normalized.getData();
        switch (type) {
            case "math_formula" -> validateMathFormula(data, renderHint, errors, warnings);
            case "chemical_formula" -> validateChemicalFormula(data, renderHint, errors, warnings);
            case "mermaid_diagram" -> validateMermaidDiagram(data, renderHint, errors, warnings);
            case "chart" -> validateChart(data, renderHint, errors, warnings);
            case "table" -> validateTable(data, renderHint, errors, warnings);
            case "geometry" -> validateGeometry(data, renderHint, errors, warnings);
            case "coordinate_system" -> validateCoordinateSystem(data, renderHint, errors, warnings);
            case "solid_geometry" -> validateSolidGeometry(data, renderHint, errors, warnings);
            case "chinese_tianzige" -> validateChineseTianzige(data, renderHint, errors, warnings);
            case "english_four_line" -> validateEnglishFourLine(data, renderHint, errors, warnings);
            default -> errors.add("unsupported component type: " + type);
        }

        return new SubjectComponentValidateVO(errors.isEmpty(), normalized, renderHint, errors, warnings);
    }

    private void validateMathFormula(Map<String, Object> data, Map<String, Object> renderHint,
                                     List<String> errors, List<String> warnings) {
        String latex = stringValue(data.get("latex"));
        if (latex.isBlank()) {
            errors.add("data.latex is required for math_formula");
        }
        if (!data.containsKey("display_mode")) {
            data.put("display_mode", true);
        }
        renderHint.put("engine", "katex");
        renderHint.put("input", "latex");
        renderHint.put("output", List.of("html", "svg"));
        if (latex.contains("<script")) {
            errors.add("data.latex contains unsafe script content");
        }
        if (latex.length() > 2000) {
            warnings.add("data.latex is very long; frontend rendering may be slow");
        }
    }

    private void validateChemicalFormula(Map<String, Object> data, Map<String, Object> renderHint,
                                         List<String> errors, List<String> warnings) {
        String formula = stringValue(data.get("formula"));
        String smiles = stringValue(data.get("smiles"));
        String molfile = stringValue(data.get("molfile"));
        if (formula.isBlank() && smiles.isBlank() && molfile.isBlank()) {
            errors.add("one of data.formula, data.smiles or data.molfile is required for chemical_formula");
        }
        renderHint.put("engine", "kekule");
        renderHint.put("input", List.of("formula", "smiles", "molfile"));
        renderHint.put("output", List.of("svg", "canvas"));
        if (!formula.isBlank() && formula.length() > 200) {
            warnings.add("data.formula is unusually long");
        }
        if (!molfile.isBlank() && molfile.length() > 20000) {
            warnings.add("data.molfile is very large; consider storing it as an external resource");
        }
    }

    private void validateMermaidDiagram(Map<String, Object> data, Map<String, Object> renderHint,
                                        List<String> errors, List<String> warnings) {
        String mermaid = stringValue(data.get("mermaid"));
        if (mermaid.isBlank()) {
            errors.add("data.mermaid is required for mermaid_diagram");
        } else {
            String lower = mermaid.trim().toLowerCase(Locale.ROOT);
            boolean supported = lower.startsWith("flowchart") || lower.startsWith("graph")
                    || lower.startsWith("sequencediagram") || lower.startsWith("classdiagram")
                    || lower.startsWith("statediagram") || lower.startsWith("timeline")
                    || lower.startsWith("mindmap") || lower.startsWith("pie")
                    || lower.startsWith("erdiagram") || lower.startsWith("journey")
                    || lower.startsWith("gantt");
            if (!supported) {
                warnings.add("data.mermaid does not start with a common Mermaid diagram declaration");
            }
        }
        renderHint.put("engine", "mermaid");
        renderHint.put("input", "mermaid");
        renderHint.put("output", List.of("svg"));
    }

    private void validateChart(Map<String, Object> data, Map<String, Object> renderHint,
                               List<String> errors, List<String> warnings) {
        Object option = data.get("option");
        if (option == null) {
            errors.add("data.option is required for chart");
        } else if (option instanceof String optionText) {
            try {
                JSONUtil.parseObj(optionText);
            } catch (Exception e) {
                errors.add("data.option must be a JSON object or object string");
            }
        } else if (!(option instanceof Map) && !(option instanceof JSONObject)) {
            errors.add("data.option must be a JSON object");
        }
        renderHint.put("engine", "echarts");
        renderHint.put("input", "option");
        renderHint.put("output", List.of("canvas", "svg"));
        if (!data.containsKey("responsive")) {
            data.put("responsive", true);
        }
    }

    private void validateTable(Map<String, Object> data, Map<String, Object> renderHint,
                               List<String> errors, List<String> warnings) {
        Object rows = data.get("rows");
        Object columns = data.get("columns");
        if (!(rows instanceof List) && !(columns instanceof List)) {
            errors.add("data.rows or data.columns is required for table");
        }
        renderHint.put("engine", "html_table");
        renderHint.put("input", List.of("columns", "rows"));
        renderHint.put("output", List.of("html"));
    }

    private void validateGeometry(Map<String, Object> data, Map<String, Object> renderHint,
                                  List<String> errors, List<String> warnings) {
        Object construction = data.get("construction");
        Object commands = data.get("commands");
        if (construction == null && !(commands instanceof List)) {
            errors.add("data.construction or data.commands is required for geometry");
        }
        renderHint.put("engine", "jsxgraph");
        renderHint.put("input", List.of("construction", "commands"));
        renderHint.put("output", List.of("svg", "html"));
    }

    private void validateCoordinateSystem(Map<String, Object> data, Map<String, Object> renderHint,
                                          List<String> errors, List<String> warnings) {
        Object points = data.get("points");
        if (points != null && !(points instanceof List)) {
            errors.add("data.points must be an array for coordinate_system");
        }
        int xRange = intValue(data.get("xRange"), 5);
        int yRange = intValue(data.get("yRange"), 4);
        if (xRange < 2 || xRange > 10) {
            warnings.add("data.xRange is clamped to the 2-10 range");
        }
        if (yRange < 2 || yRange > 10) {
            warnings.add("data.yRange is clamped to the 2-10 range");
        }
        data.put("xRange", Math.max(2, Math.min(10, xRange)));
        data.put("yRange", Math.max(2, Math.min(10, yRange)));
        data.putIfAbsent("showGrid", true);
        data.putIfAbsent("connectPoints", false);
        data.putIfAbsent("segments", List.of());
        if (!data.containsKey("points")) {
            Map<String, Object> first = new LinkedHashMap<>();
            first.put("label", "A");
            first.put("x", 2);
            first.put("y", 3);
            Map<String, Object> second = new LinkedHashMap<>();
            second.put("label", "B");
            second.put("x", -2);
            second.put("y", -1);
            data.put("points", new ArrayList<>(List.of(first, second)));
        }
        renderHint.put("engine", "svg");
        renderHint.put("input", List.of("xRange", "yRange", "showGrid", "connectPoints", "points", "segments"));
        renderHint.put("output", List.of("svg"));
    }

    private void validateSolidGeometry(Map<String, Object> data, Map<String, Object> renderHint,
                                       List<String> errors, List<String> warnings) {
        String solid = stringValue(data.get("solid")).toLowerCase(Locale.ROOT);
        if (!solid.isBlank() && !SOLID_SHAPES.contains(solid)) {
            warnings.add("data.solid should be one of cube/cuboid/pyramid/cylinder/cone/sphere; fallback to cube");
            solid = "";
        }
        data.put("solid", solid.isBlank() ? "cube" : solid);

        Object dimensions = data.get("dimensions");
        if (dimensions != null && !(dimensions instanceof Map) && !(dimensions instanceof JSONObject)) {
            errors.add("data.dimensions must be an object for solid_geometry");
        }
        Map<String, Object> sourceDimensions = new LinkedHashMap<>();
        if (dimensions instanceof Map<?, ?> map) {
            map.forEach((key, value) -> sourceDimensions.put(String.valueOf(key), value));
        } else if (dimensions instanceof JSONObject object) {
            sourceDimensions.putAll(jsonObjectToMap(object));
        }
        Map<String, Object> normalizedDimensions = new LinkedHashMap<>();
        for (String key : SOLID_DIMENSION_KEYS) {
            double fallback = doubleValue(SOLID_DEFAULT_DIMENSIONS.get(key), 1);
            double value = doubleValue(sourceDimensions.get(key), fallback);
            if (value <= 0) {
                value = fallback;
            }
            normalizedDimensions.put(key, Math.round(Math.min(20, Math.max(1, value)) * 10) / 10d);
        }
        data.put("dimensions", normalizedDimensions);
        data.putIfAbsent("show_hidden_edges", true);
        data.putIfAbsent("show_dimensions", true);
        renderHint.put("engine", "svg");
        renderHint.put("input", List.of("solid", "dimensions", "show_hidden_edges", "show_dimensions"));
        renderHint.put("output", List.of("svg"));
    }

    private void validateChineseTianzige(Map<String, Object> data, Map<String, Object> renderHint,
                                         List<String> errors, List<String> warnings) {
        Object entries = data.get("entries");
        if (entries != null && !(entries instanceof List)) {
            errors.add("data.entries must be an array for chinese_tianzige");
        }
        if (entries == null && stringValue(data.get("text")).isBlank()) {
            errors.add("data.entries or data.text is required for chinese_tianzige");
        }
        data.putIfAbsent("show_pinyin", true);
        renderHint.put("engine", "html_grid");
        renderHint.put("input", List.of("entries", "show_pinyin"));
        renderHint.put("output", List.of("html"));
    }

    private void validateEnglishFourLine(Map<String, Object> data, Map<String, Object> renderHint,
                                         List<String> errors, List<String> warnings) {
        String text = stringValue(data.get("text"));
        if (text.isBlank()) {
            errors.add("data.text is required for english_four_line");
        } else if (text.length() > 1000) {
            warnings.add("data.text is very long; the four-line grid may overflow");
        }
        renderHint.put("engine", "html_grid");
        renderHint.put("input", "text");
        renderHint.put("output", List.of("html"));
    }

    private Map<String, Object> jsonObjectToMap(JSONObject object) {
        Map<String, Object> map = new LinkedHashMap<>();
        if (object == null) return map;
        object.forEach((key, value) -> map.put(String.valueOf(key), value));
        return map;
    }

    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private int intValue(Object value, int fallback) {
        if (value instanceof Number number) {
            return (int) Math.round(number.doubleValue());
        }
        try {
            return (int) Math.round(Double.parseDouble(stringValue(value)));
        } catch (NumberFormatException e) {
            return fallback;
        }
    }

    private double doubleValue(Object value, double fallback) {
        if (value instanceof Number number) {
            return number.doubleValue();
        }
        try {
            return Double.parseDouble(stringValue(value));
        } catch (NumberFormatException e) {
            return fallback;
        }
    }

    private String defaultString(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value;
    }

    private String buildProjectSnapshot(Ws_Project project) {
        Map<String, Object> projectData = new LinkedHashMap<>();
        projectData.put("project_name", project.getProject_name());
        projectData.put("project_type", project.getProject_type());
        projectData.put("status", project.getStatus());
        projectData.put("current_version", project.getCurrent_version());
        projectData.put("snapshots", project.getSnapshots());
        projectData.put("edit_history", project.getEdit_history());
        projectData.put("permissions", project.getPermissions());

        Map<String, Object> snapshot = new LinkedHashMap<>();
        snapshot.put("project", projectData);
        snapshot.put("pages", pageMapper.findByProjectId(project.getId()));
        return JSONUtil.toJsonStr(snapshot);
    }

    private void restoreSnapshot(Ws_Project project, String snapshotData) {
        if (snapshotData == null || snapshotData.isBlank()) return;
        var snapshot = JSONUtil.parseObj(snapshotData);
        var projectSnapshot = snapshot.getJSONObject("project");
        if (projectSnapshot != null) {
            project.setProject_name(projectSnapshot.getStr("project_name", project.getProject_name()));
            project.setProject_type(projectSnapshot.getStr("project_type", project.getProject_type()));
            project.setSnapshots(projectSnapshot.getStr("snapshots"));
            project.setEdit_history(projectSnapshot.getStr("edit_history"));
            // Restoring content must not revert collaborators or the project's lifecycle.
        }

        var pages = snapshot.getJSONArray("pages");
        if (pages == null) return;
        pageMapper.deleteByProjectId(project.getId());
        for (Object item : pages) {
            Ws_Page page = JSONUtil.toBean(JSONUtil.parseObj(item), Ws_Page.class);
            page.setId(0);
            page.setProject_id(project.getId());
            page.setPage_version(1);
            page.setPage_title(PageTitleUtil.forStorage(page.getPage_title()));
            pageMapper.insert(page);
        }
    }

    private void validateVersionSnapshot(String data) {
        if (data == null || data.isBlank()) throw new RuntimeException("快照内容为空，无法恢复");
        try {
            JSONObject snapshot = JSONUtil.parseObj(data);
            JSONArray pages = snapshot.getJSONArray("pages");
            if (pages == null) throw new RuntimeException("快照缺少页面数据，无法恢复");
            Set<Integer> orders = new HashSet<>();
            for (Object item : pages) {
                Ws_Page page = JSONUtil.toBean(JSONUtil.parseObj(item), Ws_Page.class);
                if (page.getPage_order() == null || page.getPage_order() < 1 || !orders.add(page.getPage_order()))
                    throw new RuntimeException("快照页面顺序无效，无法恢复");
            }
        } catch (RuntimeException ex) {
            throw new RuntimeException("快照数据无效，未修改当前课件", ex);
        }
    }
}

