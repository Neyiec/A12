package edu.zstu.service;

import edu.zstu.dto.*;
import edu.zstu.utils.PageResult;
import edu.zstu.vo.PageVO;
import edu.zstu.vo.ProjectVO;
import edu.zstu.vo.VersionVO;

import java.util.Map;

public interface ProjectService {
    ProjectVO createProject(ProjectCreateDTO dto, Integer userId);
    PageResult<ProjectVO> listProjects(ProjectQueryDTO dto, Integer userId);
    ProjectVO getProject(String id, Integer userId);
    ProjectVO updateProject(String id, ProjectCreateDTO dto, Integer userId);
    ProjectVO addPermission(String id, ProjectPermissionDTO dto, Integer userId);
    ProjectVO copyProject(String id, ProjectCopyDTO dto, Integer userId);
    ProjectVO archiveProject(String id, Integer userId);
    ProjectVO restoreProject(String id, Integer userId);
    void deleteProject(String id, Integer userId);
    PageVO aiRevision(String id, AiRevisionDTO dto, Integer userId);
    PageVO addComponent(String id, PageDTO dto, Integer userId);
    PageVO updateComponent(String id, String componentId, PageDTO dto, Integer userId);
    Map<String, Object> saveVersion(String id, VersionCreateDTO dto, Integer userId);
    PageResult<VersionVO> listVersions(String id, PageQuery pageQuery, Integer userId);
    Map<String, Object> versionDiff(String id, String versionId, Integer compareVersionId, Integer userId);
    ProjectVO restoreVersion(String id, String versionId, Integer userId);
}
