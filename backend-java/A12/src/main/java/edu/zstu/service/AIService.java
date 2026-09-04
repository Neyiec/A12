package edu.zstu.service;

import edu.zstu.dto.ConversationDTO;
import edu.zstu.dto.PlanConfirmationDTO;
import edu.zstu.dto.TaskCreateDTO;
import edu.zstu.vo.ConversationVO;
import edu.zstu.vo.TaskVO;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;
import java.util.List;

/**
 * AI 教学引擎 Service 接口<br>提供备课会话管理、消息交互、教学计划确认、任务执行等 AI 教学核心业务方法。
 */

public interface AIService {
    TaskVO createSession(TaskCreateDTO dto);
    List<ConversationVO> listSessions();
    ConversationVO getSession(String id);
    ConversationVO updateSession(String id, ConversationDTO dto);
    void deleteSession(String id);
    ConversationVO sendMessage(String id, ConversationDTO dto);
    SseEmitter sendMessageStream(String id, ConversationDTO dto);
    ConversationVO sendAudioMessage(String id, MultipartFile file, String language, ConversationDTO dto);
    TaskVO getPlan(String id);
    void confirmPlan(String id, PlanConfirmationDTO dto);
    TaskVO createRun(String id);
    TaskVO getRun(String runId);
}

