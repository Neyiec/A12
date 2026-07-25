package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 保存版本请求参数 (API-28)
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class VersionCreateDTO {
    private String description;
}
