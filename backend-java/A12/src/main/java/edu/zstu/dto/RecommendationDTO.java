package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 设置推荐/置顶请求参数 (API-90)
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class RecommendationDTO {
    private int is_top;
    private String expires_at;
}
