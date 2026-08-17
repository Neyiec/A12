package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class SubjectComponentDTO {
    private String component_id;
    private String type;
    private Map<String, Object> data;
    private Map<String, Object> render;
    private Map<String, Object> style;
}
