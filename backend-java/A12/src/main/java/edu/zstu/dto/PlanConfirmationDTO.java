package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 教学设计大纲确认/退回/补充请求参数 (API-13)
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class PlanConfirmationDTO {
    private String action;
    private String comment;
    private int plan_version;
}
