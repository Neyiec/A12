package edu.zstu;

import edu.zstu.utils.ResourceProvenance;
import edu.zstu.dto.ResourceDTO;
import edu.zstu.entity.Adm_Resource;
import edu.zstu.mapper.AdmResourceMapper;
import edu.zstu.service.impl.AdminResourceServiceImpl;
import org.junit.jupiter.api.Test;
import java.time.LocalDate;
import java.util.Map;
import com.fasterxml.jackson.databind.ObjectMapper;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class PublicResourceProvenanceTest {
    private String source(String type, String url, String kind, String until) throws Exception {
        return new ObjectMapper().writeValueAsString(Map.of("source_kind", kind, "source_type", type,
                "source_url", url, "source_note", "teacher original", "authority_level", type.equals("teacher") ? "general" : type,
                "version_label", "2022年版", "version_year", "2022", "valid_until", until));
    }
    @Test void validatesAuthorityAgainstHostnameNotSubstring() throws Exception {
        assertNotNull(ResourceProvenance.validate(source("official", "https://www.moe.gov.cn/a", "curriculum", ""), true));
        assertNotNull(ResourceProvenance.validate(source("publisher", "https://www.pep.com.cn/a", "textbook", ""), true));
        for (String url : new String[]{"https://moe.gov.cn.evil.example/a", "https://evilgov.cn/a", "https://moe.gov.cn@evil.example/a", "http://www.moe.gov.cn/a"}) {
            assertThrows(IllegalArgumentException.class, () -> ResourceProvenance.validate(source("official", url, "curriculum", ""), true));
        }
    }
    @Test void missingFieldsAndExpiredNewsCannotPublish() throws Exception {
        assertThrows(IllegalArgumentException.class, () -> ResourceProvenance.validate(null, true));
        assertThrows(IllegalArgumentException.class, () -> ResourceProvenance.validate(source("teacher", "", "current_affairs", ""), true));
        assertThrows(IllegalArgumentException.class, () -> ResourceProvenance.validate(source("teacher", "", "current_affairs", LocalDate.now().minusDays(1).toString()), true));
        assertNotNull(ResourceProvenance.validate(source("teacher", "", "current_affairs", LocalDate.now().toString()), true));
        // Older curriculum editions do not expire merely because they were published years ago.
        assertNotNull(ResourceProvenance.validate(source("teacher", "", "curriculum", ""), true));
    }
    @Test void invalidUploadAndEnableAreRejectedBeforeDatabaseWrites() {
        AdmResourceMapper mapper = mock(AdmResourceMapper.class);
        AdminResourceServiceImpl service = new AdminResourceServiceImpl(mapper, null, null, null, null, null, null);
        ResourceDTO dto = new ResourceDTO(); dto.setTitle("test"); dto.setResource_type("document");
        assertThrows(IllegalArgumentException.class, () -> service.createUploadSession(dto, 1));
        verifyNoInteractions(mapper);
        Adm_Resource resource = new Adm_Resource(); resource.setId(7); resource.setStatus(0);
        when(mapper.findById(7)).thenReturn(resource);
        edu.zstu.dto.ItemStatusDTO status = new edu.zstu.dto.ItemStatusDTO(); status.setStatus(1);
        assertThrows(IllegalArgumentException.class, () -> service.updateStatus(7, status, 1));
        verify(mapper, never()).updateStatus(anyInt(), anyInt());
    }
    @Test void directIndexCompletionPersistsBusinessStateAndRejectsStaleRegistration() {
        AdmResourceMapper mapper = mock(AdmResourceMapper.class);
        edu.zstu.service.BusinessLogService logs = mock(edu.zstu.service.BusinessLogService.class);
        AdminResourceServiceImpl service = new AdminResourceServiceImpl(mapper, null, null, logs, null, null, null);
        Adm_Resource resource = new Adm_Resource(); resource.setId(7); resource.setStatus(1);
        resource.setSource_metadata("registered-v1"); resource.setFile_url("http://local/file.txt");
        when(mapper.findById(7)).thenReturn(resource);
        assertThrows(IllegalArgumentException.class, () -> service.recordIndexResult(7, Map.of("status","completed"), 1));
        verify(mapper, never()).updateAiIndexStatus(anyInt(), anyString(), any());
        service.recordIndexResult(7, Map.of("status","completed","expected_source_metadata","registered-v1","expected_file_url","http://local/file.txt"), 1);
        verify(mapper).updateAiIndexStatus(7, "completed", null);
    }
}
