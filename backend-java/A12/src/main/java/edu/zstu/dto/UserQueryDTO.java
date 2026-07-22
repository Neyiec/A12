package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.NoArgsConstructor;

/**
 * 用户列表查询参数
 * 支持关键字模糊搜索、按用户类型和激活状态筛选
 */
@EqualsAndHashCode(callSuper = true)
@Data
@NoArgsConstructor
@AllArgsConstructor
public class UserQueryDTO extends PageQuery {
    private String keyword;
    private String user_type;
    private Integer is_active;
}
