package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 通用分页查询参数
 * 所有带分页的查询 DTO 都继承此类
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class PageQuery {
    private int page = 1;
    private int size = 10;
}
