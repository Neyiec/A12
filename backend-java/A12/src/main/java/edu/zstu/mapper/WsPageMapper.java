package edu.zstu.mapper;

import edu.zstu.entity.Ws_Page;
import org.apache.ibatis.annotations.*;

import java.util.List;

@Mapper
public interface WsPageMapper {
    Ws_Page findById(@Param("id") Integer id);
    List<Ws_Page> findByProjectId(@Param("projectId") Integer projectId);
    int insert(Ws_Page page);
    int update(Ws_Page page);
    int updateWithVersion(@Param("page") Ws_Page page, @Param("expectedVersion") Integer expectedVersion);
    int deleteById(@Param("id") Integer id);
    int deleteByIdAndProjectId(@Param("id") Integer id, @Param("projectId") Integer projectId);
    int deleteByProjectId(@Param("projectId") Integer projectId);
}
