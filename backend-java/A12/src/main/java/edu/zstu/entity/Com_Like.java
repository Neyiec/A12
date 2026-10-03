package edu.zstu.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 社区点赞实体（对应表 com_like）
 * user_id + target_type + target_id 唯一索引防重复点赞
 *
 * [数据交互说明] - 导出:
 *   - CommunityServiceImpl: 点赞/取消点赞写入，列表与榜单批量查询当前用户点赞态
 *   - ComLikeMapper: 表 com_like 的 CRUD 与窗口聚合数据源
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class Com_Like {
    private Long id;
    private int user_id;          //点赞用户ID
    private String target_type;   //目标类型(skill/lesson_case)
    private int target_id;        //目标内容ID
    private LocalDateTime created_at; //点赞时间（窗口聚合/防刷依据）
}
