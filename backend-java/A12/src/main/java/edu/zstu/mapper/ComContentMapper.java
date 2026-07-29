package edu.zstu.mapper;

import edu.zstu.dto.ContentQueryDTO;
import edu.zstu.entity.Com_Content;
import org.apache.ibatis.annotations.*;
import java.util.List;

@Mapper
public interface ComContentMapper {
    Com_Content findById(@Param("id") Integer id);
    List<Com_Content> findByAuthorId(@Param("authorId") Integer authorId);
    List<Com_Content> findPublic();
    List<Com_Content> findByType(@Param("contentType") String contentType);
    List<Com_Content> findAll();
    int insert(Com_Content content);
    int update(Com_Content content);
    int incrementViewCount(@Param("id") Integer id);
    int incrementUseCount(@Param("id") Integer id);
    int incrementViewCountBy(@Param("id") Integer id, @Param("delta") long delta);
    int incrementUseCountBy(@Param("id") Integer id, @Param("delta") long delta);
    List<Com_Content> searchPublic(ContentQueryDTO dto);
    List<Com_Content> findByAuthorAndStatus(@Param("authorId") Integer authorId, @Param("status") String status);
}
