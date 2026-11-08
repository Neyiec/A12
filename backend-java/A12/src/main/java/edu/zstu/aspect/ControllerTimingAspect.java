package edu.zstu.aspect;

import edu.zstu.utils.Result;
import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.concurrent.TimeUnit;

@Slf4j
@Aspect
@Component
public class ControllerTimingAspect {
    @Value("${a12.observability.slow-request-ms:1000}")
    private long slowRequestMs;

    @Around("execution(public * edu.zstu.controller..*.*(..))")
    public Object measure(ProceedingJoinPoint invocation) throws Throwable {
        long start = System.nanoTime();
        String outcome = "exception";
        try {
            Object response = invocation.proceed();
            outcome = response instanceof Result<?> result ? Integer.toString(result.getCode()) : "returned";
            return response;
        } catch (Throwable failure) {
            log.error("controller failed method={} errorType={}",
                    invocation.getSignature().toShortString(), failure.getClass().getSimpleName());
            throw failure;
        } finally {
            long elapsed = TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - start);
            if ("500".equals(outcome) || "503".equals(outcome))
                log.error("controller completed method={} elapsedMs={} outcome={}",invocation.getSignature().toShortString(),elapsed,outcome);
            else log.info("controller completed method={} elapsedMs={} outcome={} slow={}",
                    invocation.getSignature().toShortString(), elapsed, outcome, elapsed >= slowRequestMs);
        }
    }
}
