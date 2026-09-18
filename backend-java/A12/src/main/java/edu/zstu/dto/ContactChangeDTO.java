package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/** 当前用户通过原邮箱验证码修改真实姓名、邮箱或手机号的请求参数。 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ContactChangeDTO {
    private String real_name;
    private String email;
    private String phone;
    private String code;
}
