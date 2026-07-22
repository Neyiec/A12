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
}
