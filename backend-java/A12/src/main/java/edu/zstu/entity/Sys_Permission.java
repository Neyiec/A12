package edu.zstu.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 系统权限（sys_permission）
 * 按模块×操作建模，perm_code = "{module_key}:{action_key}"，如 users:view
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class Sys_Permission {
    private int id;
    private String perm_code;     //权限标识
    private String perm_name;     //权限名称(展示用)
    private String module_key;    //所属模块: dashboard/users/roles/audit/resources/settings
    private String module_label;  //模块中文名
    private String action_key;    //操作: view/create/edit/delete/audit/export/stats/modify/resetPassword/configPerm
    private String action_label;  //操作中文名
    private String description;   //权限说明
    private int status;           //是否启用 1表示是 0表示否
    private LocalDateTime created_at;
    private LocalDateTime updated_at;
}
