package edu.zstu.mapper;

import edu.zstu.entity.Sys_User;
import edu.zstu.dto.UserQueryDTO;
import org.apache.ibatis.annotations.*;

import java.util.List;

@Mapper
public interface SysUserMapper {
    Sys_User findById(@Param("id") Integer id);
    Sys_User findByUsername(@Param("username") String username);
    Sys_User findByEmail(@Param("email") String email);
    Sys_User findByPhone(@Param("phone") String phone);
    Sys_User findByUsernameAndPasswordHash(@Param("username") String username, @Param("passwordHash") String passwordHash);
    List<Sys_User> findAll();
    int insert(Sys_User user);
    int update(Sys_User user);
    int updateActiveStatus(@Param("id") Integer id, @Param("isActive") Integer isActive);
    int changePassword(@Param("newPasswordHash") String newPasswordHash, @Param("username") String username);
    int updateContact(@Param("id") Integer id, @Param("realName") String realName,
                      @Param("email") String email, @Param("phone") String phone,
                      @Param("realNameChanged") boolean realNameChanged,
                      @Param("emailChanged") boolean emailChanged, @Param("phoneChanged") boolean phoneChanged);
    int updateLastLogin(@Param("id") Integer id, @Param("lastLoginIp") String lastLoginIp);
    int deleteById(@Param("id") Integer id);
    List<Sys_User> findByQuery(UserQueryDTO dto);
}
