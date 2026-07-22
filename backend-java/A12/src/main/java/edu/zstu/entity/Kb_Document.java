package edu.zstu.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class Kb_Document {
    private int id;
    private String source_type; //来源类型(personal/platform)
    private int source_id; //来源素材ID(平台资源为空)
    private int user_id;
    private String title;
    private String doc_type; //文档类型(text/image/audio/video)
    private String parse_status; //解析状态(pending/parsing/completed/failed)
    private String chunks; //json字符串 分块列表
    private LocalDateTime created_at;
    private LocalDateTime updated_at;
}
