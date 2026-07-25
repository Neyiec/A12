package edu.zstu.mapper;

import edu.zstu.entity.Kb_Document;
import org.apache.ibatis.annotations.*;
import java.util.List;

@Mapper
public interface KbDocumentMapper {
    Kb_Document findById(@Param("id") Integer id);
    List<Kb_Document> findByUserId(@Param("userId") Integer userId);
    Kb_Document findBySource(@Param("sourceType") String sourceType, @Param("sourceId") Integer sourceId);
    List<Kb_Document> findByParseStatus(@Param("parseStatus") String parseStatus);
    int insert(Kb_Document document);
    int updateParseResult(Kb_Document document);
}
