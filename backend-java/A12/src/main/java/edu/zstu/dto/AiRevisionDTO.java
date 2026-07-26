package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * AI修订请求参数 (API-25)
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class AiRevisionDTO {
    private String target_type;
    private String target_id;
    private String instruction;
    private String context;
}
