package edu.zstu;

import edu.zstu.utils.LocalObjectStorage;
import edu.zstu.utils.OssUtil;
import edu.zstu.utils.OssConfig;
import edu.zstu.controller.LocalStorageController;
import com.aliyun.oss.OSS;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.server.ResponseStatusException;
import java.nio.file.*;
import java.io.ByteArrayInputStream;
import java.net.URI;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

class LocalObjectStorageTest {
    @TempDir Path directory;
    private LocalObjectStorage store(long limit) { return new LocalObjectStorage(directory.toString(),"http://localhost:8088",limit); }
    @Test void signedUploadAndDownloadRoundTrip() throws Exception {
        var storage = store(1000);
        var mvc = MockMvcBuilders.standaloneSetup(new LocalStorageController(storage)).build();
        String key = "local/uploads/1/id/中文.txt";
        var upload = storage.signedUrl(key,"PUT",10);
        mvc.perform(put(URI.create(upload.toString())).content("hello")).andExpect(status().isNoContent());
        var download = storage.signedUrl(key,"GET",10);
        mvc.perform(get(URI.create(download.toString()))).andExpect(status().isOk()).andExpect(content().string("hello"));
        assertEquals(key,storage.extract(download.toString()));
        storage.delete(key);
        assertFalse(storage.exists(key));
    }
    @Test void signaturesRejectTamperingAndWrongMethod() throws Exception {
        var storage = store(1000);
        var mvc = MockMvcBuilders.standaloneSetup(new LocalStorageController(storage)).build();
        var url = storage.signedUrl("local/uploads/1/a.txt","PUT",10).toString();
        mvc.perform(get(URI.create(url))).andExpect(status().isForbidden());
        mvc.perform(put(URI.create(url.replace("a.txt","b.txt"))).content("x")).andExpect(status().isForbidden());
        assertThrows(ResponseStatusException.class,() -> storage.verify("local/uploads/1/a.txt","PUT",0,"bad"));
    }
    @Test void unsignedFileIsNotPublic() throws Exception {
        var mvc = MockMvcBuilders.standaloneSetup(new LocalStorageController(store(1000))).build();
        mvc.perform(get("/api/v1/storage/local-object").param("object_key","local/a.txt")).andExpect(status().isBadRequest());
    }
    @Test void blocksTraversalAndAbsolutePaths() {
        var storage = store(1000);
        for (String key : new String[]{"local/../x","local/C:/x","local/\\x","remote/x","local/"})
            assertThrows(ResponseStatusException.class,() -> storage.path(key));
    }
    @Test void oversizedUploadLeavesNoPartialFile() {
        var storage = store(2);
        assertThrows(ResponseStatusException.class,() -> storage.write("local/a.txt",new ByteArrayInputStream(new byte[3])));
        assertFalse(storage.exists("local/a.txt"));
    }
    @Test void switchingProviderPreservesLocalAndOssRouting() throws Exception {
        var local = store(1000);
        var oss = mock(OSS.class);
        var config = new OssConfig();config.setBucketName("example");config.setEndpoint("oss-cn-hangzhou.aliyuncs.com");
        var util = new OssUtil(oss,config,local);
        ReflectionTestUtils.setField(util,"provider","local");
        assertEquals("local/uploads/1/a",util.uploadObjectKey("uploads/1/a"));
        local.write("local/uploads/1/a",new ByteArrayInputStream(new byte[]{1}));
        String url = util.getObjectUrl("local/uploads/1/a");
        ReflectionTestUtils.setField(util,"provider","oss");
        assertEquals("uploads/1/a",util.uploadObjectKey("uploads/1/a"));
        assertTrue(util.resolveDownloadUrl(url,10).contains("signature="));
        assertTrue(util.doesObjectExist("local/uploads/1/a"));
        util.doesObjectExist("uploads/1/a");verify(oss).doesObjectExist("example","uploads/1/a");
        assertEquals("uploads/1/a",util.extractObjectKey("https://example.oss-cn-hangzhou.aliyuncs.com/uploads/1/a"));
    }
    @Test void restartInvalidatesOldSignedUrls() throws Exception {
        var first = store(1000);
        var second = store(1000);
        var mvc = MockMvcBuilders.standaloneSetup(new LocalStorageController(second)).build();
        mvc.perform(put(URI.create(first.signedUrl("local/uploads/1/a","PUT",10).toString())).content("x"))
            .andExpect(status().isForbidden());
    }
}
