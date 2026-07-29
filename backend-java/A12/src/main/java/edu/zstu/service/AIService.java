package edu.zstu.service;

import edu.zstu.dto.ConversationDTO;
import edu.zstu.dto.PlanConfirmationDTO;
import edu.zstu.dto.TaskCreateDTO;
import edu.zstu.vo.ConversationVO;
import edu.zstu.vo.TaskVO;

/**
 * AI 教学引擎 Service 接口<br>提供备课会话管理、消息交互、教学计划确认、任务执行等 AI 教学核心业务方法。
 */

public interface AIService {
    TaskVO createSession(TaskCreateDTO dto);
    ConversationVO sendMessage(String id, ConversationDTO dto);
    TaskVO getPlan(String id);
    void confirmPlan(String id, PlanConfirmationDTO dto);
    TaskVO createRun(String id);
    TaskVO getRun(String runId);
}

