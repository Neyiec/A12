import asyncio
import os
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from a12_ppt.community_review_worker import process_event

REAL_ASYNC_CLIENT = httpx.AsyncClient


def test_stale_or_already_processed_event_never_calls_model():
    async def respond(request):
        return httpx.Response(200, json={"code": 409, "message": "审核任务已失效", "data": None})

    transport = httpx.MockTransport(respond)
    with patch.dict(os.environ, {"A12_PYTHON_INTERNAL_KEY": "test-key"}), \
         patch("a12_ppt.community_review_worker.httpx.AsyncClient",
               side_effect=lambda **kwargs: REAL_ASYNC_CLIENT(transport=transport)), \
         patch("a12_ppt.community_review_worker.review_content", new_callable=AsyncMock) as review:
        asyncio.run(process_event({"audit_id": "12", "content_version": "2"}))
    review.assert_not_called()


def test_valid_event_posts_review_result():
    requests = []

    async def respond(request):
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(200, json={"code": 200, "data": {"content_version": 2, "subject": "数学"}})
        return httpx.Response(200, json={"code": 200, "data": None})

    transport = httpx.MockTransport(respond)
    result = {"content_version": 2, "domain": "science", "verdict": "review", "score": 70,
              "summary": "待人工核验", "checks": [], "findings": []}
    with patch.dict(os.environ, {"A12_PYTHON_INTERNAL_KEY": "test-key"}), \
         patch("a12_ppt.community_review_worker.httpx.AsyncClient",
               side_effect=lambda **kwargs: REAL_ASYNC_CLIENT(transport=transport)), \
         patch("a12_ppt.community_review_worker.review_content", new_callable=AsyncMock,
               return_value=result) as review:
        asyncio.run(process_event({"audit_id": "12", "content_version": "2"}))
    review.assert_awaited_once()
    assert [request.method for request in requests] == ["GET", "POST"]
    assert requests[1].headers["X-A12-Internal-Key"] == "test-key"


def test_server_failure_is_retried_instead_of_acknowledged():
    async def respond(request):
        return httpx.Response(500, json={"code": 500, "message": "数据库不可用"})

    transport = httpx.MockTransport(respond)
    with patch.dict(os.environ, {"A12_PYTHON_INTERNAL_KEY": "test-key"}), \
         patch("a12_ppt.community_review_worker.httpx.AsyncClient",
               side_effect=lambda **kwargs: REAL_ASYNC_CLIENT(transport=transport)):
        with pytest.raises(httpx.HTTPStatusError):
            asyncio.run(process_event({"audit_id": "12", "content_version": "2"}))
