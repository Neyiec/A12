package edu.zstu.service.impl;

import cn.hutool.core.bean.BeanUtil;
import edu.zstu.dto.PasswordChangeDTO;
import edu.zstu.entity.Sys_User;
import edu.zstu.mapper.SysUserMapper;
import edu.zstu.service.UserService;
import edu.zstu.utils.CurrentHolder;
import edu.zstu.utils.JwtUtil;
import edu.zstu.utils.PasswordUtil;
import edu.zstu.vo.UserVO;
import org.springframework.stereotype.Service;


/**
 * 用户模块 Service 实现
 */
@Service
public class UserServiceImpl implements UserService {

    private final SysUserMapper userMapper;
    private final PasswordUtil passwordUtil;
    private final JwtUtil jwtUtil;

    public UserServiceImpl(SysUserMapper userMapper, PasswordUtil passwordUtil,
                           JwtUtil jwtUtil) {
        this.userMapper = userMapper;
        this.passwordUtil = passwordUtil;
        this.jwtUtil = jwtUtil;
    }
    @Override
    public UserVO getCurrentUser() {
        Sys_User user=userMapper.findById(CurrentHolder.getCurrentId());
        if(user== null){
            throw new RuntimeException("用户不存在");
        }
        if(user.getIs_active()!=1){
            throw new RuntimeException("用户未激活，请先激活");
        }
        UserVO userVO= BeanUtil.copyProperties(user,UserVO.class);

        return userVO;
    }
    @Override
    public void changePassword(PasswordChangeDTO dto) {

        String currentPassword = dto.getCurrent_password();
        String newPassword = dto.getNew_password();
        //根据currentHolder获取用户id
        Sys_User user=userMapper.findById(CurrentHolder.getCurrentId());
        if(user== null){
            throw new RuntimeException("用户不存在");
        }
        if(user.getIs_active()!=1){
            throw new RuntimeException("用户未激活，请先激活");
        }

        if (!passwordUtil.hash(currentPassword).equals(user.getPassword_hash())) {
            throw new RuntimeException("当前密码错误");
        }
        int res = userMapper.changePassword(passwordUtil.hash(newPassword), user.getUsername());
        if(res<=0){
            throw new RuntimeException("密码修改失败");
        }
    }
}
