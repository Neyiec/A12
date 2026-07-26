package edu.zstu.service;

import edu.zstu.dto.MaterialDTO;
import edu.zstu.dto.MaterialQueryDTO;
import edu.zstu.dto.ResourceBatchActionDTO;
import edu.zstu.dto.ResourceUploadConfirmDTO;
import edu.zstu.dto.UploadTokenDTO;
import edu.zstu.utils.PageResult;
import edu.zstu.vo.MaterialVO;
import edu.zstu.vo.UploadTokenVO;

import java.util.Map;

public interface ResourceService {
    UploadTokenVO createUploadToken(UploadTokenDTO dto, Integer userId);
    MaterialVO confirmUpload(ResourceUploadConfirmDTO dto, Integer userId);
    PageResult<MaterialVO> listResources(MaterialQueryDTO dto, Integer userId);
    MaterialVO getResource(Integer id, Integer userId);
    MaterialVO updateResource(Integer id, MaterialDTO dto, Integer userId);
    void deleteResource(Integer id, Integer userId);
    void batchAction(ResourceBatchActionDTO dto, Integer userId);
    MaterialVO setPermission(Integer id, MaterialDTO dto, Integer userId);
    Map<String, Object> getDownloadUrl(Integer id, Integer userId);
}
