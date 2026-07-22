package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.NoArgsConstructor;

/**
 * 素材资源查询参数
 * 支持按用户、文件类型和关键字筛选
 */
@EqualsAndHashCode(callSuper = true)
@Data
@NoArgsConstructor
@AllArgsConstructor
public class MaterialQueryDTO extends PageQuery {
    private Integer user_id;
    private String file_type;
    private String keyword;
}
