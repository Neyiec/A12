package com.a12.teacher;

import android.app.Activity;
import android.content.ContentResolver;
import android.content.Intent;
import android.net.Uri;
import android.provider.DocumentsContract;
import android.webkit.MimeTypeMap;
import androidx.activity.result.ActivityResult;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.ActivityCallback;
import com.getcapacitor.annotation.CapacitorPlugin;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.Locale;
import java.util.concurrent.atomic.AtomicBoolean;

@CapacitorPlugin(name = "A12FileDownload")
public class FileDownloadPlugin extends Plugin {
    private final AtomicBoolean busy = new AtomicBoolean();

    @PluginMethod
    public void save(PluginCall call) {
        String filename = call.getString("filename", "download").replace('/', '_').replace('\\', '_');
        try {
            parseDownloadUrl(call);
        } catch (IOException failure) {
            call.reject(failure.getMessage());
            return;
        }
        if (!busy.compareAndSet(false, true)) {
            call.reject("已有文件正在保存");
            return;
        }

        int dot = filename.lastIndexOf('.');
        String mimeType = dot < 0 ? null : MimeTypeMap.getSingleton()
            .getMimeTypeFromExtension(filename.substring(dot + 1).toLowerCase(Locale.ROOT));
        Intent picker = new Intent(Intent.ACTION_CREATE_DOCUMENT);
        picker.addCategory(Intent.CATEGORY_OPENABLE);
        picker.setType(mimeType == null ? "application/octet-stream" : mimeType);
        picker.putExtra(Intent.EXTRA_TITLE, filename);
        try {
            startActivityForResult(call, picker, "saveSelectedDocument");
        } catch (RuntimeException failure) {
            busy.set(false);
            call.reject("无法打开文件保存窗口");
        }
    }

    @ActivityCallback
    private void saveSelectedDocument(PluginCall call, ActivityResult result) {
        Uri destination = result.getData() == null ? null : result.getData().getData();
        if (call == null || result.getResultCode() != Activity.RESULT_OK || destination == null) {
            busy.set(false);
            if (call != null) call.reject("已取消保存", "CANCELLED");
            return;
        }
        ContentResolver resolver = getContext().getContentResolver();
        new Thread(() -> {
            try {
                downloadTo(call, resolver, destination);
                call.resolve();
            } catch (IOException | RuntimeException failure) {
                try { DocumentsContract.deleteDocument(resolver, destination); }
                catch (Exception ignored) { /* A document provider may not support deletion. */ }
                call.reject(failure instanceof DownloadException ? failure.getMessage() : "文件保存失败，请检查网络或存储空间");
            } finally {
                busy.set(false);
            }
        }, "A12FileDownload").start();
    }

    private static URL parseDownloadUrl(PluginCall call) throws IOException {
        try {
            URL url = new URL(call.getString("url", ""));
            if (("http".equals(url.getProtocol()) || "https".equals(url.getProtocol()))
                && !url.getHost().isEmpty() && url.getUserInfo() == null) return url;
        } catch (IOException ignored) { /* Invalid URLs use the same user-facing error. */ }
        throw new IOException("无效的文件下载地址");
    }

    private static void downloadTo(PluginCall call, ContentResolver resolver, Uri destination) throws IOException {
        HttpURLConnection connection = (HttpURLConnection) parseDownloadUrl(call).openConnection();
        connection.setConnectTimeout(15000);
        connection.setReadTimeout(30000);
        connection.setInstanceFollowRedirects(false);
        String authorization = call.getString("authorization");
        if (authorization != null) connection.setRequestProperty("Authorization", authorization);
        try {
            int status = connection.getResponseCode();
            if (status != HttpURLConnection.HTTP_OK) throw new DownloadException("文件下载失败（HTTP " + status + "）");
            long expectedBytes = connection.getContentLengthLong();
            try (InputStream input = connection.getInputStream(); OutputStream output = resolver.openOutputStream(destination, "wt")) {
                if (output == null) throw new IOException("No output stream");
                byte[] buffer = new byte[32768];
                long writtenBytes = 0;
                int count;
                while ((count = input.read(buffer)) != -1) {
                    output.write(buffer, 0, count);
                    writtenBytes += count;
                }
                if (expectedBytes >= 0 && writtenBytes != expectedBytes) throw new DownloadException("文件下载不完整，请重试");
            }
        } finally {
            connection.disconnect();
        }
    }

    private static final class DownloadException extends IOException {
        DownloadException(String message) { super(message); }
    }
}
