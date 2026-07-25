package edu.zstu.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class Ws_Version {
    private int id;
    private int project_id;
    private int version_number;
    private String description;
    private LocalDateTime created_at;
}
