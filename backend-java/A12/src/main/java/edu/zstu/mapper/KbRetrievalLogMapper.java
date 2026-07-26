package edu.zstu.mapper;

import edu.zstu.entity.Kb_Retrieval_Log;
import org.apache.ibatis.annotations.*;
import java.util.List;

@Mapper
public interface KbRetrievalLogMapper {
    Kb_Retrieval_Log findById(@Param("id") Long id);
    List<Kb_Retrieval_Log> findByUserId(@Param("userId") Integer userId);
    List<Kb_Retrieval_Log> findByTaskId(@Param("taskId") Integer taskId);
    int insert(Kb_Retrieval_Log log);
}
