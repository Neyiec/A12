package edu.zstu.mapper;

import edu.zstu.dto.ProjectQueryDTO;
import edu.zstu.entity.Ws_Project;
import org.apache.ibatis.annotations.*;

import java.util.List;

@Mapper
public interface WsProjectMapper {
    List<Ws_Project> findByQuery(ProjectQueryDTO dto);
    Ws_Project findById(@Param("id") Integer id);
    List<Ws_Project> findByUserId(@Param("userId") Integer userId);
    List<Ws_Project> findAll();
    int insert(Ws_Project project);
    int update(Ws_Project project);
    int updateStatus(@Param("id") Integer id, @Param("status") String status);
    int deleteById(@Param("id") Integer id);
}
