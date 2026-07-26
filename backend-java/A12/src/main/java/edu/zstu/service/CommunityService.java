package edu.zstu.service;

/**
 * 社区模块 Service 接口<br>提供社区内容检索、收藏关注、投稿审核、举报处理等社区业务方法。
 */

public interface CommunityService {
    Object listItems();
    Object getItem(String id);
    Object favorite(String id);
    Object unfavorite(String id);
    Object recordView(String id);
    Object listFavorites();
    Object listRecentViews();
    Object removeRecentView(String itemId);
    Object reuseItem(String id);
    Object createSubmission();
    Object listSubmissions();
    Object getSubmission(String id);
    Object updateSubmission(String id);
    Object saveSubmissionVersion(String id);
    Object submitForReview(String id);
    Object createReport();
    Object listReports();
    Object getReport(String id);
}

