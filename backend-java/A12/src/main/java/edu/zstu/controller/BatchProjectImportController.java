package edu.zstu.controller;

import edu.zstu.service.BatchProjectImportService;
import edu.zstu.utils.CurrentHolder;
import edu.zstu.utils.Result;
import edu.zstu.vo.ProjectVO;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

@RestController
@RequiredArgsConstructor
public class BatchProjectImportController {
    private final BatchProjectImportService importer;

    @PostMapping("/api/v1/projects/batch-import")
    public Result<ProjectVO> importOwn(@RequestBody BatchProjectImportService.ImportRequest request) {
        return Result.success(importer.save(CurrentHolder.getCurrentId(),request));
    }

    // Existing internal-key filter protects background persistence after the browser closes.
    @PostMapping("/api/v1/internal/batch-projects/{userId}")
    public Result<ProjectVO> importBackground(@PathVariable Integer userId, @RequestBody BatchProjectImportService.ImportRequest request) {
        Integer previous=CurrentHolder.getCurrentId();
        try {
            CurrentHolder.setCurrentId(userId);
            return Result.success(importer.save(userId,request));
        } finally {
            if(previous==null) CurrentHolder.remove(); else CurrentHolder.setCurrentId(previous);
        }
    }
}
