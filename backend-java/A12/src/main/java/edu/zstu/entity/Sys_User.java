package edu.zstu.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;


import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class Sys_User{
    private int id;
    private String username;
    private String password_hash;
    private String real_name;
    private String email;
    private String phone;
    private String avatar; //头像url
    private String user_type; //用户类型teacher/admin
    private String roles; //json字符串         扮演的角色 比如teacher ，team_leader
    private String permissions; //json字符串 权限列表
    private int is_active; //是否激活 1表示是 0表示否
    private LocalDateTime created_at;
    private LocalDateTime updated_at;

}
