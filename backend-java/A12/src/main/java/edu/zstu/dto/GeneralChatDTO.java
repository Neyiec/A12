package edu.zstu.dto;

import lombok.Data;

@Data
public class GeneralChatDTO {
    private Integer session_id;
    private String message;
    private String model_profile;
    private String reasoning_effort;
    /** auto / chat / planning；用户手动选择优先于自动判断。 */
    private String route_preference;
    private String resource_ids;
}
