package edu.zstu.utils;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.net.URI;
import java.time.LocalDate;
import java.util.*;

/** 公共资源来源登记：声明权威等级必须与服务端白名单相符。 */
public final class ResourceProvenance {
    private static final ObjectMapper JSON = new ObjectMapper();
    private ResourceProvenance() {}
    public static Map<String, Object> read(String value) {
        if (value == null || value.isBlank()) return Map.of();
        try { return JSON.readValue(value, new TypeReference<Map<String, Object>>() {}); }
        catch (Exception error) { throw new IllegalArgumentException("来源登记须为 JSON 对象"); }
    }
    public static boolean officialHost(String host) {
        return host != null && (host.equals("gov.cn") || host.endsWith(".gov.cn"));
    }
    public static boolean publisherHost(String host) {
        return host != null && Set.of("pep.com.cn", "hep.com.cn").stream().anyMatch(root -> host.equals(root) || host.endsWith("." + root));
    }
    public static String validate(String value, boolean publishing) {
        Map<String, Object> raw = read(value);
        Map<String, Object> data = new LinkedHashMap<>();
        for (String key : List.of("source_kind", "source_type", "source_url", "source_note", "version_label", "version_year", "authority_level", "valid_until")) {
            Object item = raw.get(key);
            String text = item == null ? "" : item.toString().trim();
            if (text.length() > (key.equals("source_url") ? 1800 : 500)) throw new IllegalArgumentException("来源字段过长: " + key);
            data.put(key, text);
        }
        if (!publishing && raw.isEmpty()) return null;
        String kind = text(data, "source_kind"), type = text(data, "source_type"), level = text(data, "authority_level");
        if (!Set.of("curriculum", "textbook", "current_affairs", "courseware", "other").contains(kind)) throw new IllegalArgumentException("请选择资料时效类型");
        if (!Set.of("official", "publisher", "teacher", "other").contains(type)) throw new IllegalArgumentException("请选择来源类型");
        if (!Set.of("official", "publisher", "general").contains(level)) throw new IllegalArgumentException("请选择可信等级");
        String url = text(data, "source_url"), note = text(data, "source_note");
        if (url.isBlank() && note.isBlank()) throw new IllegalArgumentException("来源链接或来源说明至少填写一项");
        String host = null;
        if (!url.isBlank()) {
            try {
                URI uri = URI.create(url); host = uri.getHost();
                if (!"https".equalsIgnoreCase(uri.getScheme()) || host == null || uri.getUserInfo() != null || (uri.getPort() != -1 && uri.getPort() != 443)) throw new Exception();
                host = host.toLowerCase(Locale.ROOT);
            } catch (Exception error) { throw new IllegalArgumentException("来源链接须为不含账号的 HTTPS 地址"); }
        }
        if ((level.equals("official") || type.equals("official")) && (!type.equals("official") || !level.equals("official") || !officialHost(host))) throw new IllegalArgumentException("官方来源须使用 gov.cn 白名单链接并选择官方等级");
        if ((level.equals("publisher") || type.equals("publisher")) && (!type.equals("publisher") || !level.equals("publisher") || !publisherHost(host))) throw new IllegalArgumentException("出版社来源须使用 pep.com.cn 或 hep.com.cn 白名单链接");
        if (text(data, "version_label").isBlank()) throw new IllegalArgumentException("请填写课标版本、教材版次或资料版本");
        try {
            int year = Integer.parseInt(text(data, "version_year"));
            if (year < 1900 || year > LocalDate.now().getYear() + 1) throw new Exception();
        } catch (Exception error) { throw new IllegalArgumentException("请填写有效的版本年份"); }
        String until = text(data, "valid_until");
        if (kind.equals("current_affairs") && until.isBlank()) throw new IllegalArgumentException("时政资料必须填写有效期");
        if (!until.isBlank()) {
            try {
                LocalDate date = LocalDate.parse(until);
                if (publishing && date.isBefore(LocalDate.now())) throw new Exception();
            } catch (Exception error) { throw new IllegalArgumentException("有效期无效或已过期，不能发布"); }
        }
        try { return JSON.writeValueAsString(data); }
        catch (Exception error) { throw new IllegalArgumentException("来源登记无法保存"); }
    }
    private static String text(Map<String, Object> data, String key) { return String.valueOf(data.getOrDefault(key, "")); }
}
