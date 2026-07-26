package edu.zstu.controller;

import edu.zstu.dto.ResourceDTO;
import edu.zstu.dto.ItemStatusDTO;
import edu.zstu.utils.Result;
import edu.zstu.vo.ResourceVO;
import org.springframework.web.bind.annotation.*;

/**
 * 后台 — 公共资源模块 Controller
 * API-79~85：公共资源上传、检索、状态管理
 *
 * <p>管理员管理平台公共资源，包括检索、上传、元数据更新、启用/停用
 * 以及处理状态（安全检测、知识解析、索引）查询。</p>
 */
@RestController
@RequestMapping("/api/v1/admin/public-resources")
public class AdminResourceController {

    /**
     * API-79 分页查询公共资源
     *
     * <p>按类型、来源、版本、安全状态、解析状态和索引状态分页查询。</p>
     *
     * @param resource_type 资源类型（选填）
     * @param status        状态（选填）
     * @param page          页码（选填，默认1）
     * @param size          每页条数（选填，默认10）
     * @return 分页公共资源列表
     */
    @GetMapping
    public Result<?> listResources(@RequestParam(required = false) String resource_type,
                                   @RequestParam(required = false) Integer status,
                                   @RequestParam(defaultValue = "1") int page,
                                   @RequestParam(defaultValue = "10") int size) {
        return Result.success();
    }

    /**
     * API-80 创建公共资源上传会话
     *
     * <p>创建公共资源上传会话并取得短时签名地址。</p>
     *
     * @param dto 资源上传参数 {@link ResourceDTO}
     * @return 上传会话ID和签名地址
     */
    @PostMapping("/uploads")
    public Result<?> createUploadSession(@RequestBody ResourceDTO dto) {
        return Result.success();
    }

    /**
     * API-81 完成公共资源上传
     *
     * <p>完成上传并创建或更新资源版本，随后触发内容安全检测。</p>
     *
     * @param id 上传会话ID（路径参数）
     * @return 完成后的资源信息 {@link ResourceVO}
     */
    @PostMapping("/uploads/{id}/complete")
    public Result<ResourceVO> completeUpload(@PathVariable String id) {
        return Result.success();
    }

    /**
     * API-82 获取公共资源详情
     *
     * <p>获取公共资源元数据、来源、授权、版本及处理状态。</p>
     *
     * @param id 资源ID（路径参数）
     * @return 资源详情 {@link ResourceVO}
     */
    @GetMapping("/{id}")
    public Result<ResourceVO> getResource(@PathVariable String id) {
        return Result.success();
    }

    /**
     * API-83 更新公共资源
     *
     * <p>更新公共资源分类、来源、授权或版本说明。</p>
     *
     * @param id  资源ID（路径参数）
     * @param dto 更新参数 {@link ResourceDTO}
     * @return 更新后的资源信息 {@link ResourceVO}
     */
    @PatchMapping("/{id}")
    public Result<ResourceVO> updateResource(@PathVariable String id,
                                             @RequestBody ResourceDTO dto) {
        return Result.success();
    }

    /**
     * API-84 启用/停用公共资源
     *
     * <p>启用或停用公共资源，停用时同步停用知识索引。</p>
     *
     * @param id     资源ID（路径参数）
     * @param status 0=停用, 1=启用（必填）
     * @return 更新后的资源信息 {@link ResourceVO}
     */
    @PutMapping("/{id}/status")
    public Result<ResourceVO> updateStatus(@PathVariable String id, @RequestBody ItemStatusDTO dto) {
        return Result.success();
    }

    /**
     * API-85 查询处理状态
     *
     * <p>查询内容安全、知识解析和索引处理状态及失败原因。</p>
     *
     * @param id 资源ID（路径参数）
     * @return 处理状态详情
     */
    @GetMapping("/{id}/processing-status")
    public Result<?> getProcessingStatus(@PathVariable String id) {
        return Result.success();
    }
}
