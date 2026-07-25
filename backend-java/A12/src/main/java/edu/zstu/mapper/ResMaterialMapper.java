package edu.zstu.mapper;

import edu.zstu.entity.Res_Material;
import org.apache.ibatis.annotations.*;
import java.util.List;

@Mapper
public interface ResMaterialMapper {
    Res_Material findById(@Param("id") Integer id);
    List<Res_Material> findByUserId(@Param("userId") Integer userId);
    List<Res_Material> findAll();
    List<Res_Material> findByTypeAndUser(@Param("fileType") String fileType, @Param("userId") Integer userId);
    int insert(Res_Material material);
    int update(Res_Material material);
    int softDelete(@Param("id") Integer id);
}
