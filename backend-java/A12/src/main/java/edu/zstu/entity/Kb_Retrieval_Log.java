package edu.zstu.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class Kb_Retrieval_Log {
    private long id;
    private int user_id;
    private String type; //类型(retrieval/generation)
    private int task_id;
    private String query_text;
    private String result_chunks; //json字符串 检索结果列表
    private String prompt_context;
    private String generated_content;
    private String model_name;
    private LocalDateTime created_at;
}
