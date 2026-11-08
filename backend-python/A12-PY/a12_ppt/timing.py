"""AI 链路耗时：仅记录阶段、模型及页码，不记录提示词、令牌或资料正文。"""
import asyncio
import inspect
import logging
import time
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps

from .ai_runtime import current_runtime

logger = logging.getLogger("a12_ppt.timing")
_stage = ContextVar("a12_timing_stage", default="")
_fields = ContextVar("a12_timing_fields", default={})


def log_timing(stage, elapsed_ms, *, status="success", **fields):
    fields = {**_fields.get(), **fields}
    # 字段白名单防止调用方误把原始请求写入日志。
    details = " ".join(f"{key}={value}" for key, value in fields.items()
                       if key in {"slide_no", "index", "attempt", "model", "reasoning", "count", "concurrency", "error_type", "preset"})
    logger.info("AI耗时 run_id=%s stage=%s status=%s elapsed_ms=%d elapsed_s=%.3f %s",
                current_runtime().run_id or "-", stage, status, round(elapsed_ms), elapsed_ms / 1000, details)


@contextmanager
def timing_stage(stage, **fields):
    parent = _stage.get()
    name = f"{parent}/{stage}" if parent else stage
    token = _stage.set(name)
    fields = {**_fields.get(), **fields}
    field_token = _fields.set(fields)
    started = time.perf_counter()
    log_timing(name, 0, status="start", **fields)
    try:
        yield
    except BaseException as exc:
        log_timing(name, (time.perf_counter() - started) * 1000,
                   status="cancelled" if isinstance(exc, (asyncio.CancelledError, GeneratorExit)) else "failed",
                   error_type=type(exc).__name__, **fields)
        raise
    else:
        log_timing(name, (time.perf_counter() - started) * 1000, **fields)
    finally:
        _stage.reset(token)
        _fields.reset(field_token)


def timed(stage, fields=()):
    """同步函数、协程及 SSE 异步生成器均可测量，异常与取消不会被吞掉。"""
    def decorate(fn):
        signature = inspect.signature(fn)
        def labels(args, kwargs):
            bound = signature.bind_partial(*args, **kwargs).arguments
            return {key: bound[key] for key in fields if key in bound}
        if inspect.isasyncgenfunction(fn):
            @wraps(fn)
            async def stream(*args, **kwargs):
                parent = _stage.get()
                name = f"{parent}/{stage}" if parent else stage
                info = {**_fields.get(), **labels(args, kwargs)}
                started = time.perf_counter()
                status = "success"
                log_timing(name, 0, status="start", **info)
                iterator = fn(*args, **kwargs)
                try:
                    while True:
                        # SSE yield 期间不能把阶段 ContextVar 泄漏给消费者，
                        # 也不能在异步生成器被其他任务关闭时重置旧任务的 token。
                        token = _stage.set(name)
                        field_token = _fields.set(info)
                        try:
                            item = await anext(iterator)
                        except StopAsyncIteration:
                            break
                        finally:
                            _stage.reset(token)
                            _fields.reset(field_token)
                        yield item
                except BaseException as exc:
                    status = "cancelled" if isinstance(exc, (asyncio.CancelledError, GeneratorExit)) else "failed"
                    raise
                finally:
                    try:
                        await iterator.aclose()
                    finally:
                        log_timing(name, (time.perf_counter() - started) * 1000, status=status, **info)
            return stream
        if inspect.iscoroutinefunction(fn):
            @wraps(fn)
            async def asynchronous(*args, **kwargs):
                with timing_stage(stage, **labels(args, kwargs)):
                    return await fn(*args, **kwargs)
            return asynchronous
        @wraps(fn)
        def synchronous(*args, **kwargs):
            with timing_stage(stage, **labels(args, kwargs)):
                return fn(*args, **kwargs)
        return synchronous
    return decorate
