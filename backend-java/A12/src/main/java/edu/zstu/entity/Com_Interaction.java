package edu.zstu.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class Com_Interaction {
    private long id;
    private int user_id;
    private String action_type; //操作类型(favorite/derivation)
    private String target_type; //目标类型(skill/case)
    private int target_id;
    private int target_version; //复用时来源版本号
    private int target_project_id; //派生项目ID(仅derivation)
    private String bind_materials; //json数组 绑定的私有素材ID列表
    private LocalDateTime created_at;
}
