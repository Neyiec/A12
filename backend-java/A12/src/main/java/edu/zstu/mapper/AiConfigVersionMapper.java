package edu.zstu.mapper;

import edu.zstu.entity.AiConfigVersion;
import org.apache.ibatis.annotations.*;

import java.util.List;

@Mapper
public interface AiConfigVersionMapper {
    AiConfigVersion findById(@Param("id") Integer id);
    List<AiConfigVersion> findByConfigId(@Param("configId") Integer configId);
    AiConfigVersion findByConfigIdAndVersion(@Param("configId") Integer configId, @Param("version") Integer version);
    int insert(AiConfigVersion version);
}
