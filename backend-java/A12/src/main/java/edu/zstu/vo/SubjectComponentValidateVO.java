package edu.zstu.vo;

import edu.zstu.dto.SubjectComponentDTO;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class SubjectComponentValidateVO {
    private Boolean valid;
    private SubjectComponentDTO normalized;
    private Map<String, Object> render_hint;
    private List<String> errors;
    private List<String> warnings;
}
