package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 项目授权请求参数
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ProjectPermissionDTO {
    private Integer user_id;
}