package edu.zstu;

import ch.qos.logback.classic.Logger;
import ch.qos.logback.core.read.ListAppender;
import edu.zstu.aspect.ControllerTimingAspect;
import edu.zstu.utils.Result;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.Signature;
import org.junit.jupiter.api.Test;
import org.slf4j.LoggerFactory;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class ControllerTimingAspectTest {
    @Test void reportsSuccessAndFailureWithoutArgumentsOrExceptionPayload() throws Throwable {
        Logger logger=(Logger)LoggerFactory.getLogger(ControllerTimingAspect.class);
        ListAppender<ch.qos.logback.classic.spi.ILoggingEvent> capture=new ListAppender<>();capture.start();logger.addAppender(capture);
        try {
            ProceedingJoinPoint point=mock(ProceedingJoinPoint.class);Signature signature=mock(Signature.class);
            when(point.getSignature()).thenReturn(signature);when(signature.toShortString()).thenReturn("Controller.method()");
            when(point.proceed()).thenReturn(Result.success());new ControllerTimingAspect().measure(point);
            assertTrue(capture.list.stream().anyMatch(e->e.getLevel().toString().equals("INFO")&&e.getFormattedMessage().contains("outcome=200")));
            when(point.proceed()).thenThrow(new IllegalStateException("private exception body"));
            assertThrows(IllegalStateException.class,()->new ControllerTimingAspect().measure(point));
            assertTrue(capture.list.stream().anyMatch(e->e.getLevel().toString().equals("ERROR")&&e.getFormattedMessage().contains("IllegalStateException")));
            assertFalse(capture.list.stream().anyMatch(e->e.getFormattedMessage().contains("private")));
            verify(point,never()).getArgs();
        } finally { logger.detachAppender(capture); }
    }
}
