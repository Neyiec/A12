package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.NoArgsConstructor;

/**
 * 社区内容搜索查询参数
 * 支持按内容类型、学科、年级、状态和关键字筛选；
 * 功能11 新增排序维度：sort_by（like/favorite/use）× period（day/week/month/all）
 */
@EqualsAndHashCode(callSuper = true)
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ContentQueryDTO extends PageQuery {
    private String content_type;
    private String subject;
    private String grade;
    private String status;
    private String keyword;
    /** recommended/newest/likes/favorites/uses/hot */
    private String sort;
    /** day/week/month/all，排序时间窗口。 */
    private String period;
    /** 由服务端填充，不信任客户端传入的用户 ID。 */
    private Integer viewer_id;
    private String sort_by;   //排序维度：like/favorite/use，空为默认（置顶+更新时间）
}
