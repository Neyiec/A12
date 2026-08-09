package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class IntentRecognitionDTO {
    private String user_id;
    private String session_id;
    private String title;
    private String message;
    private String history;
    private String known_context;
    private String resource_ids;
    private Boolean enable_rag;
    private Boolean enable_web;
    private Integer slide_count;
    private String language;
}
