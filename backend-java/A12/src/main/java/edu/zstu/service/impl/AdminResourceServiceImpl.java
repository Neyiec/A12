package edu.zstu.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import edu.zstu.dto.ItemStatusDTO;
import edu.zstu.dto.ResourceDTO;
import edu.zstu.entity.Adm_Resource;
import edu.zstu.mapper.AdmResourceMapper;
import edu.zstu.service.AdminResourceService;
import edu.zstu.utils.OssUtil;
import edu.zstu.utils.PageResult;
import edu.zstu.vo.ResourceVO;
import org.springframework.stereotype.Service;

import java.net.URL;
import java.time.LocalDateTime;
import java.util.*;

@Service
public class AdminResourceServiceImpl implements AdminResourceService {

    private final AdmResourceMapper resourceMapper;
    private final OssUtil ossUtil;

    public AdminResourceServiceImpl(AdmResourceMapper resourceMapper, OssUtil ossUtil) {
        this.resourceMapper = resourceMapper;
        this.ossUtil = ossUtil;
    }

    @Override
    public PageResult<ResourceVO> listResources(String resourceType, Integer status, int page, int size) {
        PageHelper.startPage(page, size);
        List<Adm_Resource> list = resourceMapper.findByQuery(resourceType, status);
        PageInfo<Adm_Resource> info = new PageInfo<>(list);

        List<ResourceVO> records = info.getList().stream().map(this::toResourceVO).toList();
        PageResult<ResourceVO> r = new PageResult<>();
        r.setTotal(info.getTotal()); r.setPage(page); r.setSize(size); r.setRecords(records);
        return r;
    }

    @Override
    public Map<String, Object> createUploadSession(ResourceDTO dto, Integer adminId) {
        if (dto.getResource_type() == null || dto.getTitle() == null) {
            throw new RuntimeException("缺少必填字段: resource_type, title");
        }

        // 创建待上传记录 (status=0)
        Adm_Resource resource = new Adm_Resource();
        BeanUtil.copyProperties(dto, resource);
        resource.setStatus(0);
        resource.setUploaded_by(adminId);
        resourceMapper.insert(resource);

        // 生成 OSS 签名上传 URL
        String objectKey = "public/" + dto.getResource_type() + "/" + resource.getId() + "_" + UUID.randomUUID();
        URL signedUrl = ossUtil.generateUploadUrl(objectKey, 120);

        // 暂存 objectKey（用于 complete 时拼接 file_url）
        resource.setFile_url(ossUtil.getObjectUrl(objectKey));
        resourceMapper.update(resource);

        Map<String, Object> result = new HashMap<>();
        result.put("upload_id", resource.getId());
        result.put("upload_url", signedUrl.toString());
        result.put("expires_at", LocalDateTime.now().plusMinutes(120));
        return result;
    }

    @Override
    public ResourceVO completeUpload(Integer id, Integer adminId) {
        Adm_Resource resource = resourceMapper.findById(id);
        if (resource == null) throw new RuntimeException("上传会话不存在");
        if (resource.getStatus() != 0) throw new RuntimeException("上传会话状态异常");

        // 验证 OSS 文件是否存在
        String objectKey = ossUtil.extractObjectKey(resource.getFile_url());
        if (!ossUtil.doesObjectExist(objectKey)) {
            throw new RuntimeException("文件上传尚未完成或文件不存在于OSS");
        }

        resource.setStatus(1);
        resourceMapper.updateStatus(id, 1);
        return toResourceVO(resource);
    }

    @Override
    public ResourceVO getResource(Integer id) {
        Adm_Resource r = resourceMapper.findById(id);
        if (r == null) throw new RuntimeException("资源不存在");
        return toResourceVO(r);
    }

    @Override
    public ResourceVO updateResource(Integer id, ResourceDTO dto, Integer adminId) {
        Adm_Resource r = resourceMapper.findById(id);
        if (r == null) throw new RuntimeException("资源不存在");

        if (dto.getTitle() != null) r.setTitle(dto.getTitle());
        if (dto.getSubject() != null) r.setSubject(dto.getSubject());
        if (dto.getGrade() != null) r.setGrade(dto.getGrade());
        if (dto.getDescription() != null) r.setDescription(dto.getDescription());
        if (dto.getFile_url() != null) r.setFile_url(dto.getFile_url());
        if (dto.getTemplate_data() != null) r.setTemplate_data(dto.getTemplate_data());
        if (dto.getThumbnail() != null) r.setThumbnail(dto.getThumbnail());
        resourceMapper.update(r);
        return toResourceVO(r);
    }

    @Override
    public ResourceVO updateStatus(Integer id, ItemStatusDTO dto, Integer adminId) {
        Adm_Resource r = resourceMapper.findById(id);
        if (r == null) throw new RuntimeException("资源不存在");
        resourceMapper.updateStatus(id, dto.getStatus());
        r.setStatus(dto.getStatus());
        return toResourceVO(r);
    }

    @Override
    public Map<String, Object> getProcessingStatus(Integer id) {
        Adm_Resource r = resourceMapper.findById(id);
        if (r == null) throw new RuntimeException("资源不存在");

        // MVP 返回模拟处理状态（实际暂不接入安全检测/解析/索引流水线）
        Map<String, Object> result = new HashMap<>();
        result.put("security_check", "passed");
        result.put("parse_status", "completed");
        result.put("index_status", "completed");
        result.put("error_msg", "");
        return result;
    }

    private ResourceVO toResourceVO(Adm_Resource r) {
        ResourceVO vo = new ResourceVO();
        BeanUtil.copyProperties(r, vo);
        return vo;
    }
}