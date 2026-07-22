package edu.zstu.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class Sys_File {
    private long id;
    private String file_name;
    private String file_path;
    private String file_type;
    private String mime_type;
    private long file_size;
    private String storage_type; //存储方式(local/oss)
    private int uploader_id;
    private String biz_type; //业务类型(material/export/resource/avatar)
    private int biz_id;
    private LocalDateTime created_at;
}
