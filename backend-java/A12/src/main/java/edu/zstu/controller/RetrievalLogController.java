package edu.zstu.controller;

import edu.zstu.entity.Kb_Retrieval_Log;
import edu.zstu.mapper.KbRetrievalLogMapper;
import edu.zstu.utils.CurrentHolder;
import edu.zstu.utils.Result;
import edu.zstu.vo.PageResult;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/v1/kb/retrieval-logs")
public class RetrievalLogController {
    private final KbRetrievalLogMapper retrievalLogMapper;

    public RetrievalLogController(KbRetrievalLogMapper retrievalLogMapper) {
        this.retrievalLogMapper = retrievalLogMapper;
    }

    @GetMapping
    public Result<PageResult<Kb_Retrieval_Log>> listLogs(@RequestParam(required = false) String type,
                                                         @RequestParam(required = false) Integer task_id,
                                                         @RequestParam(defaultValue = "1") int page,
                                                         @RequestParam(defaultValue = "20") int size) {
        Integer userId = requireLogin();
        int safePage = Math.max(page, 1);
        int safeSize = Math.max(1, Math.min(size, 100));
        int offset = (safePage - 1) * safeSize;
        List<Kb_Retrieval_Log> records = retrievalLogMapper.findRecent(userId, type, task_id, offset, safeSize);
        long total = retrievalLogMapper.countRecent(userId, type, task_id);
        return Result.success(PageResult.of(records, total, safePage, safeSize));
    }

    @GetMapping("/{id}")
    public Result<Kb_Retrieval_Log> getLog(@PathVariable Long id) {
        Integer userId = requireLogin();
        Kb_Retrieval_Log log = retrievalLogMapper.findById(id);
        if (log == null || log.getUser_id() != userId) {
            throw new RuntimeException("Retrieval log not found");
        }
        return Result.success(log);
    }

    private Integer requireLogin() {
        Integer userId = CurrentHolder.getCurrentId();
        if (userId == null) {
            throw new RuntimeException("Not logged in");
        }
        return userId;
    }
}
