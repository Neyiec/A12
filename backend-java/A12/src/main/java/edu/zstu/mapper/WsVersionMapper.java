package edu.zstu.mapper;

import edu.zstu.dto.PageQuery;
import edu.zstu.entity.Ws_Version;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.*;
import java.util.List;

@Mapper
public interface WsVersionMapper {
    Ws_Version findById(@Param("id") Integer id);
    List<Ws_Version> findByProjectId(@Param("projectId") Integer projectId);
    int insert(Ws_Version version);
    int findMaxVersionNumber(@Param("projectId") Integer projectId);
    int deleteByProjectId(@Param("projectId") Integer projectId);
}
