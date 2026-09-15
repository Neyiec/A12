package edu.zstu.mapper;

import edu.zstu.entity.Adm_Resource;
import org.apache.ibatis.annotations.*;
import java.util.List;

@Mapper
public interface AdmResourceMapper {
    Adm_Resource findById(@Param("id") Integer id);
    List<Adm_Resource> findByIds(@Param("ids") List<Integer> ids);
    List<Adm_Resource> findActive();
    List<Adm_Resource> findAll();
    List<Adm_Resource> findByType(@Param("resourceType") String resourceType);
    int insert(Adm_Resource resource);
    int update(Adm_Resource resource);
    int updateStatus(@Param("id") Integer id, @Param("status") Integer status);
    int updateAiIndexStatus(@Param("id") Integer id, @Param("status") String status, @Param("error") String error);
    int deleteById(@Param("id") Integer id);
    List<Adm_Resource> findByQuery(@Param("resourceType") String resourceType, @Param("status") Integer status);
}
