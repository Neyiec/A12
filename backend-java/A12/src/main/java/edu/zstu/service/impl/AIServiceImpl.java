package edu.zstu.service.impl;

import edu.zstu.service.AIService;
import org.springframework.stereotype.Service;

/**
 * AI 教学引擎 Service 实现
 */
@Service
public class AIServiceImpl implements AIService {
    @Override
    public Object createSession() { return null; }
    @Override
    public Object sendMessage(String id) { return null; }
    @Override
    public Object getPlan(String id) { return null; }
    @Override
    public Object confirmPlan(String id) { return null; }
    @Override
    public Object createRun(String id) { return null; }
    @Override
    public Object getRun(String runId) { return null; }
    @Override
    public Object getRunEvents(String runId) { return null; }
}
