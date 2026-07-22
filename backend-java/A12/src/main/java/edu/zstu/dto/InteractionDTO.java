package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 社区互动操作请求参数（收藏/派生）
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class InteractionDTO {
    private String action_type;
    private String target_type;
    private int target_id;
    private Integer target_version;
    private String bind_materials;
}
