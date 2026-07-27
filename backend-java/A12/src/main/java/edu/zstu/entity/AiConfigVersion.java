package edu.zstu.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.time.LocalDateTime;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class AiConfigVersion {
    private int id;
    private int configId;
    private int version;
    private String configValue;
    private String reason;
    private Integer createdBy;
    private LocalDateTime createdAt;
}
