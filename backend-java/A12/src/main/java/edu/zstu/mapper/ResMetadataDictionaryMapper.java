package edu.zstu.mapper;

import edu.zstu.entity.Res_Metadata_Dictionary;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface ResMetadataDictionaryMapper {
    Res_Metadata_Dictionary findById(@Param("id") Integer id);
    Res_Metadata_Dictionary findByUserTypeName(@Param("userId") Integer userId, @Param("dictType") String dictType, @Param("name") String name);
    List<Res_Metadata_Dictionary> findByUserAndType(@Param("userId") Integer userId, @Param("dictType") String dictType);
    int insert(Res_Metadata_Dictionary dictionary);
    int update(Res_Metadata_Dictionary dictionary);
    int upsert(Res_Metadata_Dictionary dictionary);
    int softDelete(@Param("id") Integer id, @Param("userId") Integer userId, @Param("dictType") String dictType);
}
