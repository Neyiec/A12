package edu.zstu.service.impl;

import edu.zstu.service.AdminModerationService;
import org.springframework.stereotype.Service;

/**
 * 后台 — 内容审核与举报处理 Service 实现
 */
@Service
public class AdminModerationServiceImpl implements AdminModerationService {
    @Override
    public Object listModerationTasks() { return null; }
    @Override
    public Object getModerationTask(String id) { return null; }
    @Override
    public Object makeDecision(String id) { return null; }
    @Override
    public Object updateItemStatus(String id) { return null; }
    @Override
    public Object updateRecommendation(String id) { return null; }
    @Override
    public Object listReports() { return null; }
    @Override
    public Object getReport(String id) { return null; }
    @Override
    public Object resolveReport(String id) { return null; }
}
