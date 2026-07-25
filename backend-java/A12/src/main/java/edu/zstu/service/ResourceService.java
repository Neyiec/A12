package edu.zstu.service;

import edu.zstu.dto.*;
import edu.zstu.utils.PageResult;
import edu.zstu.vo.MaterialVO;
import org.springframework.web.multipart.MultipartFile;

import java.util.Map;

public interface ResourceService {
    MaterialVO uploadFile(MultipartFile file, String fileType, Integer userId);
    PageResult<MaterialVO> listResources(MaterialQueryDTO dto, Integer userId);
    MaterialVO getResource(Integer id, Integer userId);
    MaterialVO updateResource(Integer id, MaterialDTO dto, Integer userId);
    void deleteResource(Integer id, Integer userId);
    void batchAction(ResourceBatchActionDTO dto, Integer userId);
    MaterialVO setPermission(Integer id, MaterialDTO dto, Integer userId);
    Map<String, Object> getDownloadUrl(Integer id, Integer userId);
}
