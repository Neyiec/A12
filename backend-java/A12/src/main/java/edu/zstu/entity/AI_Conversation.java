package edu.zstu.entity;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class AI_Conversation {
    private int id;
    private int user_id;
    private String title;
    private String status;
    private String messages; //json字符串 AI的消息列表
    private String context_summary; //上下文摘要
    private String python_session_id; // Python outline chat session id
    private String last_question; // Latest clarification question from Python
    private LocalDateTime created_at;
    private LocalDateTime updated_at;
}
