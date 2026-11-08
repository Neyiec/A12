package edu.zstu.service;

import edu.zstu.mapper.AdmResourceMapper;
import edu.zstu.mapper.ResMaterialMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

/** 事件在业务事务提交后发布，失败状态必须使用独立事务持久化。 */
@Service
@RequiredArgsConstructor
public class ResourceIndexFailureRecorder {
    private final AdmResourceMapper publicResources;
    private final ResMaterialMapper personalResources;

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void record(String source, Integer id, String message) {
        if ("public".equals(source)) publicResources.updateAiIndexStatus(id, "failed", message);
        if ("personal".equals(source)) personalResources.updateAiIndexStatus(id, "failed", message);
    }
}
