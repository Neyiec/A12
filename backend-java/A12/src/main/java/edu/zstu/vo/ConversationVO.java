package edu.zstu.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * AI对话会话信息
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ConversationVO {
    private int id;
    private int user_id;
    private String title;
    private String status;
    private String messages;
    private String context_summary;
    private LocalDateTime created_at;
    private LocalDateTime updated_at;
}
