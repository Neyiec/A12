package edu.zstu.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class VersionVO {
    private int version_id;
    private int version_number;
    private String description;
    private String snapshot_data;
    private Integer created_by;
    private LocalDateTime created_at;
}
