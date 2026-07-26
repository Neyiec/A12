package edu.zstu.mapper;

import edu.zstu.entity.Adm_Audit;
import org.apache.ibatis.annotations.*;
import java.util.List;

@Mapper
public interface AdmAuditMapper {
    Adm_Audit findById(@Param("id") Integer id);
    List<Adm_Audit> findByType(@Param("auditType") String auditType);
    List<Adm_Audit> findByStatus(@Param("status") String status);
    List<Adm_Audit> findByTarget(@Param("targetType") String targetType, @Param("targetId") Integer targetId);
    List<Adm_Audit> findAll();
    int insert(Adm_Audit audit);
    int process(Adm_Audit audit);
    List<Adm_Audit> findByReporter(@Param("reporterId") Integer reporterId);
    List<Adm_Audit> findByReporterAndStatus(@Param("reporterId") Integer reporterId, @Param("status") String status);
}
