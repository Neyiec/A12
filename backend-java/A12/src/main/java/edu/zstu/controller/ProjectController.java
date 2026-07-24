package edu.zstu.controller;

import edu.zstu.dto.PageDTO;
import edu.zstu.dto.PageQuery;
import edu.zstu.dto.ProjectCopyDTO;
import edu.zstu.dto.ProjectCreateDTO;
import edu.zstu.dto.ProjectQueryDTO;
import edu.zstu.dto.AiRevisionDTO;
import edu.zstu.dto.VersionCreateDTO;
import edu.zstu.utils.Result;
import edu.zstu.vo.PageVO;
import edu.zstu.vo.ProjectVO;
import org.springframework.web.bind.annotation.*;

/**
 * 项目模块 Controller
 * API-17~31：项目的 CRUD、组件、版本管理
 *
 * <p>负责教学项目的创建、查询、修改、复制、归档、删除，以及项目内的页面组件管理
 * 和版本控制（保存版本、版本比对、版本恢复）。</p>
 */
@RestController
@RequestMapping("/api/v1/projects")
public class ProjectController {

    /**
     * API-17 创建项目
     *
     * <p>创建个人教学项目或社区派生项目。</p>
     *
     * @param dto 项目创建参数（project_name、project_type 必填）
     * @return 新创建的项目详情 {@link ProjectVO}
     */
    @PostMapping
    public Result<ProjectVO> createProject(@RequestBody ProjectCreateDTO dto) {
        return Result.success();
    }

    /**
     * API-18 分页查询项目列表
     *
     * <p>按名称、成果类型、状态和更新时间分页查询当前用户有权访问的项目。</p>
     *
     * @param dto 查询参数（keyword、project_type、status、page、size 均为选填）
     * @return 分页项目列表 {@link Result<PageResult<ProjectVO>>}
     */
    @GetMapping
    public Result<?> listProjects(ProjectQueryDTO dto) {
        return Result.success();
    }

    /**
     * API-19 获取项目详情
     *
     * <p>获取项目内容、元数据、当前版本和权限。</p>
     *
     * @param id 项目ID（路径参数）
     * @return 项目详情 {@link ProjectVO}
     */
    @GetMapping("/{id}")
    public Result<ProjectVO> getProject(@PathVariable String id) {
        return Result.success();
    }

    /**
     * API-20 更新项目元数据
     *
     * <p>修改项目名称、类型、说明等元数据，使用项目版本号防止并发覆盖。</p>
     *
     * @param id  项目ID（路径参数）
     * @param dto 更新参数（current_version 必填）
     * @return 更新后的项目详情 {@link ProjectVO}
     */
    @PatchMapping("/{id}")
    public Result<ProjectVO> updateProject(@PathVariable String id,
                                           @RequestBody ProjectCreateDTO dto) {
        return Result.success();
    }

    /**
     * API-21 复制项目
     *
     * <p>复制有权访问的项目并创建新的私有项目。</p>
     *
     * @param id       源项目ID（路径参数）
     * @param new_name 新项目名称（选填，默认原名称+"副本"）
     * @return 新创建的副本项目 {@link ProjectVO}
     */
    @PostMapping("/{id}/copies")
    public Result<ProjectVO> copyProject(@PathVariable String id, @RequestBody ProjectCopyDTO dto) {
        return Result.success();
    }

    /**
     * API-22 归档项目
     *
     * <p>将项目更新为归档状态并禁止继续编辑。</p>
     *
     * @param id 项目ID（路径参数）
     * @return 归档后的项目（status = archived）{@link ProjectVO}
     */
    @PostMapping("/{id}/archive")
    public Result<ProjectVO> archiveProject(@PathVariable String id) {
        return Result.success();
    }

    /**
     * API-23 恢复项目
     *
     * <p>将归档或可恢复删除状态的项目恢复为可用状态。</p>
     *
     * @param id 项目ID（路径参数）
     * @return 恢复后的项目 {@link ProjectVO}
     */
    @PostMapping("/{id}/restore")
    public Result<ProjectVO> restoreProject(@PathVariable String id) {
        return Result.success();
    }

    /**
     * API-24 永久删除项目
     *
     * <p>在权限、保留期和关联导出任务校验通过后永久删除项目。</p>
     *
     * @param id 项目ID（路径参数）
     * @return 删除结果（无数据体）
     */
    @DeleteMapping("/{id}")
    public Result<Void> deleteProject(@PathVariable String id) {
        return Result.success();
    }

    /**
     * API-25 AI修订
     *
     * <p>对指定页面或组件执行自然语言修改。</p>
     *
     * @param id          项目ID（路径参数）
     * @param dto         修订请求参数 {@link AiRevisionDTO}（含 target_type、target_id、instruction、context）
     * @return 修改后的页面内容 {@link PageVO}
     */
    @PostMapping("/{id}/ai-revisions")
    public Result<PageVO> aiRevision(@PathVariable String id, @RequestBody AiRevisionDTO dto) {
        return Result.success();
    }

    /**
     * API-26 添加页面组件
     *
     * <p>向指定项目的页面中插入文本、图片、音视频、表格、H5或学科工具组件。</p>
     *
     * @param id  项目ID（路径参数）
     * @param dto 页面组件参数（page_type、page_order 必填）{@link PageDTO}
     * @return 添加后的页面信息 {@link PageVO}
     */
    @PostMapping("/{id}/components")
    public Result<PageVO> addComponent(@PathVariable String id,
                                       @RequestBody PageDTO dto) {
        return Result.success();
    }

    /**
     * API-27 更新组件
     *
     * <p>修改指定组件的内容、位置和样式。</p>
     *
     * @param id          项目ID（路径参数）
     * @param componentId 组件ID（路径参数）
     * @param dto         页面组件更新参数 {@link PageDTO}
     * @return 更新后的页面信息 {@link PageVO}
     */
    @PatchMapping("/{id}/components/{componentId}")
    public Result<PageVO> updateComponent(@PathVariable String id,
                                          @PathVariable String componentId,
                                          @RequestBody PageDTO dto) {
        return Result.success();
    }

    /**
     * API-28 保存项目版本
     *
     * <p>保存不可变项目版本并返回版本编号。</p>
     *
     * @param id          项目ID（路径参数）
     * @param dto         版本创建请求参数 {@link VersionCreateDTO}（含 description）
     * @return 版本ID和版本号
     */
    @PostMapping("/{id}/versions")
    public Result<?> saveVersion(@PathVariable String id, @RequestBody VersionCreateDTO dto) {
        return Result.success();
    }

    /**
     * API-29 分页查询历史版本
     *
     * <p>查询项目历史版本、创建人、说明和创建时间。</p>
     *
     * @param id   项目ID（路径参数）
     * @param dto  分页参数（page、size 选填）
     * @return 分页版本列表
     */
    @GetMapping("/{id}/versions")
    public Result<?> listVersions(@PathVariable String id, PageQuery dto) {
        return Result.success();
    }

    /**
     * API-30 版本差异比较
     *
     * <p>将目标版本与指定版本或当前版本进行差异比较。</p>
     *
     * @param id                项目ID（路径参数）
     * @param versionId         目标版本ID（路径参数）
     * @param compareVersionId  对比版本ID（选填，不传则比较当前版本）
     * @return 差异结果（differences 数组 + summary 摘要）
     */
    @GetMapping("/{id}/versions/{versionId}/diff")
    public Result<?> versionDiff(@PathVariable String id,
                                 @PathVariable String versionId,
                                 @RequestParam(required = false) Integer compareVersionId) {
        return Result.success();
    }

    /**
     * API-31 恢复历史版本
     *
     * <p>基于历史版本创建新的当前版本，不修改原历史记录。</p>
     *
     * @param id        项目ID（路径参数）
     * @param versionId 源版本ID（路径参数）
     * @return 恢复后的项目（current_version 递增）{@link ProjectVO}
     */
    @PostMapping("/{id}/versions/{versionId}/restore")
    public Result<ProjectVO> restoreVersion(@PathVariable String id,
                                            @PathVariable String versionId) {
        return Result.success();
    }
}
