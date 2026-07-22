package edu.zstu.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class Res_Material {
    private int id;
    private int user_id;
    private String file_name;
    private String file_type; //文件类型(word/pdf/ppt/txt/image/audio/video)
    private String file_url;
    private long file_size; //文件大小(字节)
    private String thumbnail;
    private String description;
    private String categories; //json数组 ["课程名","章节"]
    private String tags; //json数组 ["标签1","标签2"]
    private String access_type; //访问权限(private/shared/authorized)
    private String authorized_users; //json数组 授权用户ID列表
    private int allow_ai; //是否允许AI访问 1是0否
    private int status; //状态(1正常/0已删除)
    private LocalDateTime created_at;
    private LocalDateTime updated_at;
}
