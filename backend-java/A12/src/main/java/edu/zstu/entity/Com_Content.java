package edu.zstu.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class Com_Content {
    private int id;
    private String content_type; //内容类型(skill/case)
    private int author_id;
    private String title;
    private String description;
    private String subject; //学科
    private String grade; //适用年级
    private String lesson_type; //课型
    private String keywords; //逗号分隔的主题和知识点
    private String content_data; //json字符串 内容主体
    private String input_variables; //json字符串 输入变量定义(仅skill)
    private String example_effect;
    private int version; //当前版本号
    private String version_history; //json字符串 版本历史列表
    private String license; //授权说明
    private String status; //状态(public/reviewing/offline)
    private int is_top; //是否置顶 1是0否
    private int view_count;
    private int use_count;
    private int like_count; //点赞数（冗余列，com_like 计数）
    private int favorite_count; //收藏数（冗余列，com_interaction favorite 计数）
    private boolean liked;
    private LocalDateTime created_at;
    private LocalDateTime updated_at;
}
