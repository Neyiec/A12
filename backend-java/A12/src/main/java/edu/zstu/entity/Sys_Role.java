package edu.zstu.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 系统角色（sys_role）
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class Sys_Role {
    private int id;
    private String role_code;    //角色标识: super_admin/admin/content_auditor/knowledge_curator/teacher
    private String role_name;    //角色名称(展示用)
    private String description;  //角色说明
    private int sort_order;      //展示排序
    private int status;          //是否启用 1表示是 0表示否
    private LocalDateTime created_at;
    private LocalDateTime updated_at;
}
