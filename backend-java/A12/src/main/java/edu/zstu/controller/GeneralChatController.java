package edu.zstu.controller;

import edu.zstu.dto.GeneralChatDTO;
import edu.zstu.service.GeneralChatService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;
import java.util.Map;
import edu.zstu.utils.Result;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/ai/general-chat")
public class GeneralChatController {
    private final GeneralChatService generalChatService;

    @PostMapping("/turns")
    public Result<Map<String, Object>> beginTurn(@RequestBody GeneralChatDTO request) {
        return Result.success(generalChatService.beginTurn(request));
    }

    @PostMapping("/turns/{sessionId}/result")
    public Result<Map<String, Object>> completeTurn(@PathVariable Integer sessionId,
                                                     @RequestBody Map<String, Object> result) {
        return Result.success(generalChatService.completeTurn(sessionId, result));
    }
}
