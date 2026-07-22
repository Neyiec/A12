package edu.zstu.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 用户登录响应信息（含token）
 * 登录成功后返回给前端，不包含密码
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class LoginVO {
    private String token;
    private int user_id;
    private String username;
    private String real_name;
    private String avatar;
    private String user_type;
    private String roles;
    private String permissions;
    private LocalDateTime created_at;
}
