package edu.zstu.mapper;

import edu.zstu.entity.Adm_Resource;
import org.apache.ibatis.annotations.*;
import java.util.List;

@Mapper
public interface AdmResourceMapper {
    Adm_Resource findById(@Param("id") Integer id);
    List<Adm_Resource> findActive();
    List<Adm_Resource> findAll();
    List<Adm_Resource> findByType(@Param("resourceType") String resourceType);
    int insert(Adm_Resource resource);
    int update(Adm_Resource resource);
    int updateStatus(@Param("id") Integer id, @Param("status") Integer status);
}
