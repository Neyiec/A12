import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from langchain_core.messages import HumanMessage
from redis.exceptions import ConnectionError

from a12_ppt.direct_auth import direct_bearer, direct_user_id, require_active_browser_token, verify_active_token
from a12_ppt.llm.client import LLMClient


class _RedisContext:
    def __init__(self, value=None, error=None):
        self.get = AsyncMock(side_effect=error, return_value=value)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass


class RedisTokenAuthTests(unittest.IsolatedAsyncioTestCase):
    async def test_valid_current_token(self):
        redis = _RedisContext("current-token")
        with patch("a12_ppt.direct_auth.async_redis.from_url", return_value=redis):
            await verify_active_token("7", "current-token")
        redis.get.assert_awaited_once_with("token:user:7")

    async def test_expired_or_replaced_token_is_rejected(self):
        for stored in (None, "other-login-token"):
            with self.subTest(stored=stored), patch("a12_ppt.direct_auth.async_redis.from_url",
                                                     return_value=_RedisContext(stored)):
                with self.assertRaises(HTTPException) as raised:
                    await verify_active_token("7", "old-token")
                self.assertEqual(raised.exception.status_code, 401)

    async def test_redis_failure_fails_closed(self):
        with patch("a12_ppt.direct_auth.async_redis.from_url",
                   return_value=_RedisContext(error=ConnectionError("offline"))):
            with self.assertRaises(HTTPException) as raised:
                await verify_active_token("7", "current-token")
        self.assertEqual(raised.exception.status_code, 503)

    async def test_model_call_rechecks_browser_token_but_allows_trusted_background_job(self):
        user_scope = direct_user_id.set("7")
        token_scope = direct_bearer.set("browser-token")
        try:
            with patch("a12_ppt.direct_auth.verify_active_token", new_callable=AsyncMock) as verify:
                await require_active_browser_token()
                verify.assert_awaited_once_with("7", "browser-token")
        finally:
            direct_bearer.reset(token_scope)
            direct_user_id.reset(user_scope)
        with patch("a12_ppt.direct_auth.verify_active_token", new_callable=AsyncMock) as verify:
            await require_active_browser_token()
            verify.assert_not_awaited()

    async def test_revoked_token_blocks_model_before_request_is_sent(self):
        client = LLMClient()
        client.settings = SimpleNamespace(openai_api_key="test-key")
        with patch("a12_ppt.llm.client.require_active_browser_token", new_callable=AsyncMock,
                   side_effect=HTTPException(status_code=401, detail="令牌已过期")), \
             patch("a12_ppt.llm.client.create_chat_model") as model:
            with self.assertRaises(HTTPException) as raised:
                await client.complete_messages([HumanMessage(content="你好")])
        self.assertEqual(raised.exception.status_code, 401)
        model.assert_not_called()


if __name__ == "__main__":
    unittest.main()
