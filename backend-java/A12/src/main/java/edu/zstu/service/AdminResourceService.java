package edu.zstu.service;

import edu.zstu.dto.ItemStatusDTO;
import edu.zstu.dto.ResourceDTO;
import edu.zstu.utils.PageResult;
import edu.zstu.vo.ResourceVO;

import java.util.Map;

public interface AdminResourceService {
    ResourceVO recordIndexResult(Integer id, Map<String, String> result, Integer adminId);
    PageResult<ResourceVO> listResources(String resourceType, Integer status, int page, int size);
    Map<String, Object> createUploadSession(ResourceDTO dto, Integer adminId);
    ResourceVO completeUpload(Integer id, Integer adminId);
    ResourceVO getResource(Integer id);
    ResourceVO updateResource(Integer id, ResourceDTO dto, Integer adminId);
    ResourceVO updateStatus(Integer id, ItemStatusDTO dto, Integer adminId);
    ResourceVO deleteResource(Integer id, Integer adminId);
    ResourceVO reparseResource(Integer id, Integer adminId);
    Map<String, Object> getDownloadUrl(Integer id);
    Map<String, Object> getProcessingStatus(Integer id);
    Map<String, Object> bootstrapAiResourceIndex(boolean forceReparse);
    Map<String, Object> aiIndexReparse(String sourceType, Integer resourceId, Integer adminId);
}
