package edu.zstu.service;

/**
 * 后台 — 内容审核与举报处理 Service 接口<br>提供审核任务分配、审核决策、内容状态管理、举报处理等业务方法。
 */

public interface AdminModerationService {
    Object listModerationTasks();
    Object getModerationTask(String id);
    Object makeDecision(String id);
    Object updateItemStatus(String id);
    Object updateRecommendation(String id);
    Object listReports();
    Object getReport(String id);
    Object resolveReport(String id);
}

