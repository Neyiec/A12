package edu.zstu;

import edu.zstu.controller.AiRuntimeConfigInternalController;
import edu.zstu.entity.Sys_Config;
import edu.zstu.mapper.SysConfigMapper;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class AiRuntimeConfigInternalControllerTest {
    @Test
    void onlyPublishedValuesReachPython() {
        SysConfigMapper mapper = mock(SysConfigMapper.class);
        Sys_Config published = new Sys_Config();
        published.setConfig_key("subject_policy:理科");
        published.setConfig_value("published-value");
        published.setStatus("published");
        Sys_Config draft = new Sys_Config();
        draft.setConfig_key("subject_policy:文科");
        draft.setConfig_value("draft-value");
        draft.setStatus("draft");
        when(mapper.findByGroup("teaching_subject")).thenReturn(List.of(published, draft));
        when(mapper.findByGroup("image_generation")).thenReturn(List.of());

        var result = new AiRuntimeConfigInternalController(mapper).published();
        assertEquals("published-value", result.getData().get("teaching_subject").get("subject_policy:理科"));
        assertFalse(result.getData().get("teaching_subject").containsKey("subject_policy:文科"));
    }
}
