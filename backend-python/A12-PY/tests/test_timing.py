import asyncio
import logging

import pytest

from a12_ppt.ai_runtime import use_runtime_options
from a12_ppt.timing import timed, timing_stage, log_timing, _stage


def test_timing_logs_success_failure_and_never_sensitive_payload(caplog):
    caplog.set_level(logging.INFO, logger="a12_ppt.timing")
    with use_runtime_options(user_id="1") as runtime:
        with timing_stage("slide.html", slide_no=2):
            log_timing("safe", 12, prompt="PRIVATE-PROMPT", token="PRIVATE-TOKEN", html="PRIVATE-HTML")
            with timing_stage("llm.request"):
                pass
        with pytest.raises(ValueError):
            with timing_stage("html.repair", attempt=2):
                raise ValueError("PRIVATE-ERROR-DETAIL")
    assert runtime.run_id in caplog.text
    assert "stage=slide.html status=success" in caplog.text
    assert "stage=html.repair status=failed" in caplog.text
    assert "error_type=ValueError" in caplog.text
    assert "PRIVATE" not in caplog.text
    assert any("stage=slide.html/llm.request" in r.message and "slide_no=2" in r.message for r in caplog.records)
    assert _stage.get() == ""


def test_stream_timing_preserves_output_cancellation_cleanup_and_context(caplog):
    caplog.set_level(logging.INFO, logger="a12_ppt.timing")
    closed = []

    @timed("test.stream")
    async def stream():
        try:
            assert _stage.get() == "test.stream"
            yield {"type": "slide"}
            yield {"type": "final"}
        finally:
            closed.append(True)

    async def run():
        assert [item async for item in stream()] == [{"type": "slide"}, {"type": "final"}]
        iterator = stream()
        await anext(iterator)
        assert _stage.get() == ""
        # ASGI/取消路径可以在不同任务里关闭流。
        await asyncio.create_task(iterator.aclose())
        assert _stage.get() == ""
    asyncio.run(run())
    assert len(closed) == 2
    assert "status=cancelled" in caplog.text


def test_concurrent_stages_keep_independent_paths(caplog):
    caplog.set_level(logging.INFO, logger="a12_ppt.timing")

    @timed("page", fields=("slide_no",))
    async def page(slide_no):
        with timing_stage("model"):
            await asyncio.sleep(0)
        return slide_no

    async def run():
        with timing_stage("deck"):
            assert await asyncio.gather(page(1), page(2)) == [1, 2]
    asyncio.run(run())
    assert "stage=deck/page/model" in caplog.text
    assert "page/page" not in caplog.text
    assert "slide_no=1" in caplog.text and "slide_no=2" in caplog.text


def test_cancelled_coroutine_is_logged_and_not_swallowed(caplog):
    caplog.set_level(logging.INFO, logger="a12_ppt.timing")

    @timed("request")
    async def request():
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(request())
    assert "stage=request status=cancelled" in caplog.text
