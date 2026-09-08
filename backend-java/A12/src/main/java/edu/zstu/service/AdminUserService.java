package edu.zstu.service;

import edu.zstu.dto.*;
import edu.zstu.utils.PageResult;
import edu.zstu.vo.UserVO;

import java.util.List;
import java.util.Map;

public interface AdminUserService {
    PageResult<UserVO> listUsers(UserQueryDTO dto);
    UserVO getUser(Integer id);
    UserVO updateUserStatus(Integer id, UserStatusDTO dto);
    UserVO updateUser(Integer id, UserDTO dto);
    void deleteUser(Integer id);
    UserVO createUser(UserDTO dto);
    List<Map<String, Object>> listRoles();
    Map<String, Object> createRole(RoleDTO dto);
    Map<String, Object> updateRole(Integer id, RoleUpdateDTO dto);
    void deleteRole(Integer id);
    UserVO assignRoles(Integer id, AssignRolesDTO dto);
    void updateRolePermissions(Integer id, RolePermissionsDTO dto);
    Map<String, Object> batchCreateUsers(BatchCreateUsersDTO dto);
}