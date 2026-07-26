package edu.zstu.service;

/**
 * AI 教学引擎 Service 接口<br>提供备课会话管理、消息交互、教学计划确认、任务执行等 AI 教学核心业务方法。
 */

public interface AIService {
    Object createSession();
    Object sendMessage(String id);
    Object getPlan(String id);
    Object confirmPlan(String id);
    Object createRun(String id);
    Object getRun(String runId);
    Object getRunEvents(String runId);
}

