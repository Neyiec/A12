package edu.zstu.controller;

import edu.zstu.utils.Result;
import lombok.extern.slf4j.Slf4j;
import org.springframework.dao.DataAccessException;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.servlet.mvc.method.annotation.ResponseEntityExceptionHandler;

@Slf4j
@RestControllerAdvice
public class ApiExceptionAdvice extends ResponseEntityExceptionHandler {
    @ExceptionHandler(DataIntegrityViolationException.class)
    public ResponseEntity<Result<Void>> integrity(DataIntegrityViolationException error) {
        return failure(HttpStatus.CONFLICT, "数据存在冲突，请刷新或检查输入后重试", error);
    }

    @ExceptionHandler(DataAccessException.class)
    public ResponseEntity<Result<Void>> storage(DataAccessException error) {
        return failure(HttpStatus.SERVICE_UNAVAILABLE, "数据服务暂时不可用，请稍后重试", error);
    }

    @ExceptionHandler(RuntimeException.class)
    public ResponseEntity<Result<Void>> unexpected(RuntimeException error) {
        return failure(HttpStatus.INTERNAL_SERVER_ERROR, "服务处理失败，请稍后重试", error);
    }

    private ResponseEntity<Result<Void>> failure(HttpStatus status, String message, RuntimeException error) {
        // 异常文本可能包含 SQL、文件路径或参数值，日志只记录类型与代码位置。
        StackTraceElement[] trace = error.getStackTrace();
        log.warn("api failure status={} type={} location={}", status.value(),
                error.getClass().getSimpleName(), trace.length == 0 ? "unknown" : trace[0]);
        return ResponseEntity.status(status).body(Result.error(status.value(), message));
    }
}
