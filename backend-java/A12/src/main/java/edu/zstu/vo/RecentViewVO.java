package edu.zstu.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 最近浏览记录
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class RecentViewVO {
    private ContentVO item;
    private LocalDateTime viewed_at;
}
