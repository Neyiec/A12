package edu.zstu.mapper;

import edu.zstu.entity.Exp_Task;
import org.apache.ibatis.annotations.*;
import java.util.List;

@Mapper
public interface ExpTaskMapper {
    Exp_Task findById(@Param("id") Integer id);
    Exp_Task findByIdForUpdate(@Param("id") Integer id);
    List<Exp_Task> findActiveDuplicates(@Param("userId") Integer userId, @Param("projectId") Integer projectId,
                                       @Param("version") Integer version, @Param("type") String type);
    List<Exp_Task> findPageByUser(@Param("userId") Integer userId, @Param("status") String status);
    List<Exp_Task> findByUserId(@Param("userId") Integer userId);
    List<Exp_Task> findByProjectId(@Param("projectId") Integer projectId);
    List<Exp_Task> findAll();
    int insert(Exp_Task task);
    int update(Exp_Task task);
}
