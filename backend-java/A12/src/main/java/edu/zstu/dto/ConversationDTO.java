package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * AI对话操作请求参数（创建/更新会话）
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ConversationDTO {
    private String title;
    private String status;
    private String messages;
    private String context_summary;
    private String message;
    private String resource_ids;
    private Boolean enable_rag;
    private Boolean enable_web;
    private Integer slide_count;
    private String known_context;
}
