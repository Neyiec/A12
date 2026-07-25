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
    int deleteById(@Param("id") Integer id);
    int deleteByProjectId(@Param("projectId") Integer projectId);
}
