package edu.zstu.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 社区内容详情
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ContentVO {
    private int id;
    private String content_type;
    private int author_id;
    private String title;
    private String description;
    private String subject;
    private String grade;
    private String lesson_type;
    private String keywords;
    private String content_data;
    private String input_variables;
    private String example_effect;
    private int version;
    private String version_history;
    private String license;
    private String status;
    private int is_top;
    private int view_count;
    private int use_count;
    private int like_count;       //点赞数
    private int favorite_count;   //收藏数
    private boolean liked;        //当前用户是否已点赞（未登录恒为 false，不参与缓存）
    private LocalDateTime created_at;
    private LocalDateTime updated_at;
    private LocalDateTime favorited_at; // 当前用户收藏时间，不是内容发布时间
    @com.fasterxml.jackson.annotation.JsonInclude(com.fasterxml.jackson.annotation.JsonInclude.Include.NON_NULL)
    private SubmissionReview submission_review;

    public record SubmissionReview(String status, String action, String comment, LocalDateTime processed_at) {}
}
