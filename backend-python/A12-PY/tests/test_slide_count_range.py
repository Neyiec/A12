import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from a12_ppt.models import OutlineGenerateRequest, OutlineChatStreamRequest, SlideCountRange
from a12_ppt.outline_chat.workflow import OutlineChatWorkflow
from a12_ppt.presentation import PPTGenerator


def request(**values):
    return OutlineGenerateRequest(title="微积分入门", subject="数学", grade="大一", **values)


def slides(count):
    return {"title": "微积分入门", "slides": [{"title": f"第{i}项教学任务", "content_points": [f"内容{i}"]} for i in range(count)]}


def generator():
    flow = PPTGenerator.__new__(PPTGenerator)
    flow.llm = SimpleNamespace(available=True)
    return flow


def test_page_range_validation_and_optional_compatibility():
    assert request().slide_count_range is None
    assert request().slide_count == 8  # 历史API固定页数行为兼容。
    assert request(slide_count=None).slide_count is None
    for low, high in [(0, 10), (10, 31), (20, 10), (1.5, 10)]:
        with pytest.raises(ValidationError):
            SlideCountRange(min_pages=low, max_pages=high)
    assert SlideCountRange(min_pages=12, max_pages=12).max_pages == 12


def test_range_overrides_fixed_count_and_survives_graph_confirmation_request():
    workflow = OutlineChatWorkflow.__new__(OutlineChatWorkflow)
    intent = {"title": "微积分", "slide_count": 8}
    req = OutlineChatStreamRequest(user_id="1", message="确认课程信息", slide_count_range={"min_pages": 10, "max_pages": 18})
    workflow._apply_slide_options(intent, req)
    assert intent["slide_count"] is None
    # 确认请求本身未再次填写范围，仍沿用已保存的教师选择。
    workflow._apply_slide_options(intent, OutlineChatStreamRequest(user_id="1", message="确认双图谱"))
    state = {"intent": intent, "request": req}
    generated = workflow._outline_request_from_state(state)
    assert generated.slide_count_range.min_pages == 10
    assert generated.slide_count is None


def test_model_plans_inside_range_without_default_eight_page_truncation():
    flow = generator()
    req = request(slide_count_range={"min_pages": 10, "max_pages": 18})
    prompt = flow._outline_prompt(req, 10)
    assert "10 至 18" in prompt and "不要固定采用" in prompt
    result = flow._decorate_outline(slides(14), req)
    assert len(result["slides"]) == 14
    assert result["slide_count"] == 14
    assert result["outline"]["generation_options"]["slide_count_range"]["max_pages"] == 18
    assert result["outline"]["quality_report"]["checks"]["slide_count_close"]


def test_no_range_automatic_planning_keeps_model_count_and_fixed_api_stays_compatible():
    flow = generator()
    auto = request(slide_count=None)
    assert "自主规划" in flow._outline_prompt(auto, 8)
    assert len(flow._decorate_outline(slides(12), auto)["slides"]) == 12
    assert len(flow._decorate_outline(slides(12), request())["slides"]) == 8


def test_outside_range_replans_once_and_does_not_pad_or_truncate_into_success():
    async def run():
        flow = generator()
        req = request(slide_count_range={"min_pages": 10, "max_pages": 18})
        flow._generate_outline_with_model = AsyncMock(return_value=slides(13))
        result = await flow._enforce_page_range(slides(8), req, 10)
        assert len(result["slides"]) == 13
        flow._generate_outline_with_model.assert_awaited_once()
        flow._generate_outline_with_model = AsyncMock(return_value=slides(25))
        with pytest.raises(ValueError, match="AI未按10至18页"):
            await flow._enforce_page_range(slides(25), req, 10)
        flow._generate_outline_with_model.assert_awaited_once()
    asyncio.run(run())


def test_streamed_outline_preserves_ai_selected_count():
    async def run():
        flow = generator()
        flow._with_reference_and_rag_context = AsyncMock(side_effect=lambda req: req)
        async def stream(*args):
            yield json.dumps(slides(15), ensure_ascii=False)
        flow.llm.complete_stream = stream
        events = [e async for e in flow.stream_outline(request(slide_count_range={"min_pages": 10, "max_pages": 18}))]
        assert events[-1]["type"] == "final"
        assert events[-1]["response"]["slide_count"] == 15
    asyncio.run(run())
