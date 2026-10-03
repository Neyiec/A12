import json
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from a12_ppt.community_review import CHECK_NAMES, classify_domain, review_content


def payload(subject="数学", html="<h1>勾股定理</h1><p>a²+b²=c²</p>"):
    return {"content_version": 3, "title": "勾股定理", "subject": subject, "grade": "八年级",
            "license": "CC BY-NC 4.0", "content_data": json.dumps({"slides": [{"title": "定理", "html": html}]})}


def model_reply(score=95, statuses=None):
    statuses = statuses or ["pass"] * 4
    return json.dumps({"score": score, "summary": "四项检查通过", "checks": [
        {"name": name, "status": status, "evidence": "课件文字可核验"}
        for name, status in zip(CHECK_NAMES, statuses)], "findings": []}, ensure_ascii=False)


@pytest.mark.parametrize("subject,domain", [("语文", "arts"), ("数学", "science"),
                                             ("计算机基础", "engineering"), ("数学与编程", "unknown")])
def test_subject_routes_to_three_specialists_or_human(subject, domain):
    assert classify_domain(subject) == domain


def test_clean_text_only_deck_can_pass():
    model = SimpleNamespace(ainvoke=AsyncMock(return_value=SimpleNamespace(content=model_reply())))
    settings = SimpleNamespace(openai_api_key="test", openai_model_standard="test-model",
                               openai_model="fallback", openai_base_url="http://example.test/v1",
                               request_timeout_seconds=10)
    with patch("a12_ppt.community_review.get_settings", return_value=settings), \
         patch("a12_ppt.community_review.create_chat_model", return_value=model):
        result = asyncio.run(review_content(payload()))
    assert result["domain"] == "science"
    assert result["verdict"] == "pass"
    assert result["content_version"] == 3


def test_unverified_image_requires_human_even_when_model_says_pass():
    model = SimpleNamespace(ainvoke=AsyncMock(return_value=SimpleNamespace(content=model_reply())))
    settings = SimpleNamespace(openai_api_key="test", openai_model_standard="test-model",
                               openai_model="fallback", openai_base_url="http://example.test/v1",
                               request_timeout_seconds=10)
    with patch("a12_ppt.community_review.get_settings", return_value=settings), \
         patch("a12_ppt.community_review.create_chat_model", return_value=model):
        result = asyncio.run(review_content(payload(html="<p>知识点</p><img src='image.png'>")))
    assert result["verdict"] == "review"
    assert any("图片" in item["evidence"] for item in result["findings"])


def test_missing_model_falls_back_to_human():
    settings = SimpleNamespace(openai_api_key="", openai_model_standard="", openai_model="test-model")
    with patch("a12_ppt.community_review.get_settings", return_value=settings):
        result = asyncio.run(review_content(payload(subject="物理")))
    assert result["verdict"] == "error"


def test_incomplete_model_checklist_never_passes():
    model = SimpleNamespace(ainvoke=AsyncMock(return_value=SimpleNamespace(content='{"score":100,"checks":[]}')))
    settings = SimpleNamespace(openai_api_key="test", openai_model_standard="test-model",
                               openai_model="fallback", openai_base_url="http://example.test/v1",
                               request_timeout_seconds=10)
    with patch("a12_ppt.community_review.get_settings", return_value=settings), \
         patch("a12_ppt.community_review.create_chat_model", return_value=model):
        result = asyncio.run(review_content(payload()))
    assert result["verdict"] == "error"
