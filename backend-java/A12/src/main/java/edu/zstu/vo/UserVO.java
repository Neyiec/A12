package edu.zstu.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 用户信息（不含密码）
 * 向前端返回的用户数据，已脱敏处理
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class UserVO {
    private int id;
    private String username;
    private String real_name;
    private String phone;
    private String email;
    private String avatar;
    private String user_type;
    private String roles;
    private String permissions;
    private int is_active;
    private LocalDateTime created_at;
    private LocalDateTime updated_at;
}
