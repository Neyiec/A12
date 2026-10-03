package edu.zstu.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 热门榜单条目（功能11）
 * rank 从 1 开始；hot_score = like×3 + favorite×2 + reuse×4 + view×0.2（窗口内加权）
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class RankItemVO {
    private int rank;          //榜单名次（1 起）
    private double hot_score;  //热度分
    private ContentVO content; //内容概要
}
