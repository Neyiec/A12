package edu.zstu.service;

import edu.zstu.dto.PasswordChangeDTO;
import edu.zstu.dto.ContactChangeDTO;
import edu.zstu.vo.UserVO;

import java.util.Map;

/**
 * 用户模块 Service 接口<br>提供当前用户信息查询、密码修改等用户相关业务方法。
 */

public interface UserService {
    UserVO getCurrentUser();
    void changePassword(PasswordChangeDTO dto);
    UserVO changeContact(ContactChangeDTO dto);

    Map<String, Object> findUserIdByUsername(String username);
    Map<String, Object> findUserIdByEmail(String email);
}

