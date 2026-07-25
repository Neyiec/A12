package edu.zstu.mapper;

import edu.zstu.entity.Exp_Task;
import org.apache.ibatis.annotations.*;
import java.util.List;

@Mapper
public interface ExpTaskMapper {
    Exp_Task findById(@Param("id") Integer id);
    List<Exp_Task> findByUserId(@Param("userId") Integer userId);
    List<Exp_Task> findByProjectId(@Param("projectId") Integer projectId);
    List<Exp_Task> findAll();
    int insert(Exp_Task task);
    int update(Exp_Task task);
}
