package edu.zstu.mapper;

import edu.zstu.entity.Sys_Config;
import org.apache.ibatis.annotations.*;

import java.util.List;

@Mapper
public interface SysConfigMapper {
    Sys_Config findById(@Param("id") Integer id);
    List<Sys_Config> findAll();
    List<Sys_Config> findByGroup(@Param("configGroup") String configGroup);
    Sys_Config findByGroupAndKey(@Param("configGroup") String configGroup, @Param("configKey") String configKey);
    int insert(Sys_Config config);
    int update(Sys_Config config);
    int deleteById(@Param("id") Integer id);
}
