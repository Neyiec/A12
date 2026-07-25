package edu.zstu.mapper;

import edu.zstu.entity.Sys_Log;
import org.apache.ibatis.annotations.*;
import java.time.LocalDateTime;
import java.util.List;

@Mapper
public interface SysLogMapper {
    Sys_Log findById(@Param("id") Integer id);
    List<Sys_Log> findAll();
    List<Sys_Log> findByUserId(@Param("userId") Integer userId);
    List<Sys_Log> findByTypeAndTime(@Param("logType") String logType,
                                    @Param("startTime") LocalDateTime startTime,
                                    @Param("endTime") LocalDateTime endTime);
    int insert(Sys_Log log);
}
