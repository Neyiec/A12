package edu.zstu.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class PageBatchSaveDTO {
    private Integer current_version;
    private String client_version;
    private Boolean autosave;
    private List<PageDTO> pages;
}
