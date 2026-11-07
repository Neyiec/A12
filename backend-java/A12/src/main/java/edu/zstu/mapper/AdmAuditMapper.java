package edu.zstu.mapper;

import edu.zstu.entity.Adm_Audit;
import org.apache.ibatis.annotations.*;
import java.util.List;

@Mapper
public interface AdmAuditMapper {
    java.util.Map<String, Object> moderationMetrics();
    Adm_Audit findLatestSubmissionAudit(@Param("targetId") Integer targetId);
    Adm_Audit findById(@Param("id") Integer id);
    Adm_Audit findByIdForUpdate(@Param("id") Integer id);
    List<Adm_Audit> findByType(@Param("auditType") String auditType);
    List<Adm_Audit> findByStatus(@Param("status") String status);
    List<Adm_Audit> findByTarget(@Param("targetType") String targetType, @Param("targetId") Integer targetId);
    List<Adm_Audit> findAll();
    int insert(Adm_Audit audit);
    int process(Adm_Audit audit);
    int saveAiReview(Adm_Audit audit);
    List<Adm_Audit> findByReporter(@Param("reporterId") Integer reporterId);
    List<Adm_Audit> findByReporterAndStatus(@Param("reporterId") Integer reporterId, @Param("status") String status);
    List<Adm_Audit> findByReporterAndType(@Param("reporterId") Integer reporterId, @Param("auditType") String auditType);
    List<Adm_Audit> findByReporterTypeAndStatus(@Param("reporterId") Integer reporterId,
                                                @Param("auditType") String auditType,
                                                @Param("status") String status);
    List<Adm_Audit> searchAudits(@Param("auditType") String auditType,
                                  @Param("status") String status,
                                  @Param("targetType") String targetType,
                                  @Param("handlerId") Integer handlerId,
                                  @Param("aiVerdict") String aiVerdict,
                                  @Param("aiDomain") String aiDomain);
}
