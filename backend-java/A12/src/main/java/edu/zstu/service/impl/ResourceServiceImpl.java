package edu.zstu.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import edu.zstu.dto.MaterialDTO;
import edu.zstu.dto.MaterialQueryDTO;
import edu.zstu.dto.ResourceBatchActionDTO;
import edu.zstu.dto.ResourceUploadConfirmDTO;
import edu.zstu.dto.UploadTokenDTO;
import edu.zstu.entity.Res_Material;
import edu.zstu.mapper.ResMaterialMapper;
import edu.zstu.service.ResourceService;
import edu.zstu.utils.OssUtil;
import edu.zstu.utils.PageResult;
import edu.zstu.vo.MaterialVO;
import edu.zstu.vo.UploadTokenVO;
import org.springframework.stereotype.Service;

import java.net.URL;
import java.time.LocalDateTime;
import java.util.*;

@Service
public class ResourceServiceImpl implements ResourceService {

    private final ResMaterialMapper materialMapper;
    private final OssUtil ossUtil;

    public ResourceServiceImpl(ResMaterialMapper materialMapper, OssUtil ossUtil) {
        this.materialMapper = materialMapper;
        this.ossUtil = ossUtil;
    }

    
    @Override
    public UploadTokenVO createUploadToken(UploadTokenDTO dto, Integer userId) {
        if (dto.getFile_name() == null || dto.getFile_name().isBlank()) {
            throw new RuntimeException("文件名不能为空");
        }
        String objectKey = "uploads/" + userId + "/" + UUID.randomUUID() + "/" + dto.getFile_name();
        URL signedUrl = ossUtil.generateUploadUrl(objectKey, 60);

        UploadTokenVO vo = new UploadTokenVO();
        vo.setObject_key(objectKey);
        vo.setUpload_url(signedUrl.toString());
        vo.setExpires_at(LocalDateTime.now().plusMinutes(60));
        return vo;
    }

    @Override
    public MaterialVO confirmUpload(ResourceUploadConfirmDTO dto, Integer userId) {
        if (!ossUtil.doesObjectExist(dto.getObject_key())) {
            throw new RuntimeException("文件上传尚未完成或文件不存在于OSS");
        }

        if (dto.getReplace_target_id() != null) {
            Res_Material old = materialMapper.findById(dto.getReplace_target_id());
            if (old == null || old.getUser_id() != userId) {
                ossUtil.deleteObject(dto.getObject_key());
                throw new RuntimeException("要替换的资源不存在或无权操作");
            }
            ossUtil.deleteObject(ossUtil.extractObjectKey(old.getFile_url()));
            materialMapper.softDelete(dto.getReplace_target_id());
        }

        String fileType = dto.getFile_type();
        if (fileType == null || fileType.isBlank()) {
            fileType = detectFileType(dto.getFile_name());
        }

        Res_Material material = new Res_Material();
        material.setUser_id(userId);
        material.setFile_name(dto.getFile_name());
        material.setFile_type(fileType);
        material.setFile_url(ossUtil.getObjectUrl(dto.getObject_key()));
        material.setFile_size(dto.getFile_size());
        material.setDescription(dto.getDescription());
        material.setAccess_type("private");
        material.setAllow_ai(0);
        material.setStatus(1);

        materialMapper.insert(material);
        return toMaterialVO(material);
    }



    @Override
    public PageResult<MaterialVO> listResources(MaterialQueryDTO dto, Integer userId) {
        dto.setUser_id(userId);
        PageHelper.startPage(dto.getPage(), dto.getSize());
        List<Res_Material> list = materialMapper.findByQuery(dto);
        PageInfo<Res_Material> info = new PageInfo<>(list);

        List<MaterialVO> records = info.getList().stream().map(this::toMaterialVO).toList();
        PageResult<MaterialVO> r = new PageResult<>();
        r.setTotal(info.getTotal()); r.setPage(dto.getPage());
        r.setSize(dto.getSize()); r.setRecords(records);
        return r;
    }

    @Override
    public MaterialVO getResource(Integer id, Integer userId) {
        Res_Material m = materialMapper.findById(id);
        if (m == null || m.getStatus() != 1) throw new RuntimeException("资源不存在");
        return toMaterialVO(m);
    }

    @Override
    public MaterialVO updateResource(Integer id, MaterialDTO dto, Integer userId) {
        Res_Material m = materialMapper.findById(id);
        if (m == null || m.getStatus() != 1) throw new RuntimeException("资源不存在");
        if (m.getUser_id() != userId) throw new RuntimeException("无权修改该资源");
        BeanUtil.copyProperties(dto, m, "id", "user_id", "file_url", "file_type", "file_size", "status");
        materialMapper.update(m);
        return toMaterialVO(m);
    }

    @Override
    public void deleteResource(Integer id, Integer userId) {
        Res_Material m = materialMapper.findById(id);
        if (m == null) throw new RuntimeException("资源不存在");
        if (m.getUser_id() != userId) throw new RuntimeException("无权删除该资源");
        materialMapper.softDelete(id);
    }

    @Override
    public void batchAction(ResourceBatchActionDTO dto, Integer userId) {}

    @Override
    public MaterialVO setPermission(Integer id, MaterialDTO dto, Integer userId) {
        Res_Material m = materialMapper.findById(id);
        if (m == null || m.getStatus() != 1) throw new RuntimeException("资源不存在");
        if (m.getUser_id() != userId) throw new RuntimeException("无权操作该资源");
        if (dto.getAccess_type() != null) m.setAccess_type(dto.getAccess_type());
        if (dto.getAuthorized_users() != null) m.setAuthorized_users(dto.getAuthorized_users());
        m.setAllow_ai(dto.getAllow_ai());
        materialMapper.update(m);
        return toMaterialVO(m);
    }

    @Override
    public Map<String, Object> getDownloadUrl(Integer id, Integer userId) {
        Res_Material m = materialMapper.findById(id);
        if (m == null || m.getStatus() != 1) throw new RuntimeException("资源不存在");
        if (m.getUser_id() != userId) throw new RuntimeException("无权下载该资源");

        String objectKey = ossUtil.extractObjectKey(m.getFile_url());
        java.net.URL signedUrl = ossUtil.generateDownloadUrl(objectKey, 60);

        Map<String, Object> result = new HashMap<>();
        result.put("download_url", signedUrl.toString());
        result.put("expires_at", java.time.LocalDateTime.now().plusMinutes(60));
        return result;
    }

    private String detectFileType(String fileName) {
        String ext = fileName.substring(fileName.lastIndexOf('.') + 1).toLowerCase();
        return switch (ext) {
            case "doc", "docx" -> "word";
            case "pdf" -> "pdf";
            case "ppt", "pptx" -> "ppt";
            case "txt" -> "txt";
            case "jpg", "jpeg", "png", "gif", "bmp", "webp" -> "image";
            case "mp3", "wav", "aac", "ogg" -> "audio";
            case "mp4", "avi", "mov", "wmv", "flv" -> "video";
            default -> "other";
        };
    }

    private MaterialVO toMaterialVO(Res_Material m) {
        MaterialVO vo = new MaterialVO();
        BeanUtil.copyProperties(m, vo);
        return vo;
    }
}
