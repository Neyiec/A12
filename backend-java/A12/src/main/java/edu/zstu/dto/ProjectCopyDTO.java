package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 复制项目请求参数 (API-21)
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ProjectCopyDTO {
    private String new_name;
}
