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
    UserVO createUser(UserDTO dto);
    List<Map<String, Object>> listRoles();
    UserVO assignRoles(Integer id, AssignRolesDTO dto);
    void updateRolePermissions(Integer id, RolePermissionsDTO dto);
    Map<String, Object> batchCreateUsers(BatchCreateUsersDTO dto);
}