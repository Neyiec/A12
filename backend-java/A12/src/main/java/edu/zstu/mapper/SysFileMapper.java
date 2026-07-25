package edu.zstu.mapper;

import edu.zstu.entity.Sys_File;
import org.apache.ibatis.annotations.*;
import java.util.List;

@Mapper
public interface SysFileMapper {
    Sys_File findById(@Param("id") Long id);
    List<Sys_File> findAll();
    List<Sys_File> findByUploaderId(@Param("uploaderId") Integer uploaderId);
    List<Sys_File> findByBiz(@Param("bizType") String bizType, @Param("bizId") Integer bizId);
    int insert(Sys_File file);
    int deleteById(@Param("id") Long id);
}
