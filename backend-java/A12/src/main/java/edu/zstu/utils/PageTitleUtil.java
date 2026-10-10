package edu.zstu.utils;

/** Bound only database metadata; never truncate the slide's full JSON/HTML content. */
public final class PageTitleUtil {
    private PageTitleUtil() {}
    public static String forStorage(String value) {
        if (value == null) return null;
        String title = value.strip();
        if (title.codePointCount(0, title.length()) <= 200) return title;
        return title.substring(0, title.offsetByCodePoints(0, 199)) + "…";
    }
}
