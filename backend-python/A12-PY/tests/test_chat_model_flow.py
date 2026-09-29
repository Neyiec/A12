import unittest
from types import SimpleNamespace
from unittest.mock import patch

from a12_ppt.ai_runtime import use_runtime_options
from a12_ppt.llm.client import LLMClient
from a12_ppt.llm.model_factory import create_chat_model
from a12_ppt.chat_router import ChatRouteRequest, ChatRouteWorkflow


class _FakeModel:
    async def ainvoke(self, _messages):
        return SimpleNamespace(content="课程建议", usage_metadata={})

    async def astream(self, _messages):
        yield SimpleNamespace(content="课程")
        yield SimpleNamespace(content="建议")


class _EmptyModel:
    async def astream(self, _messages):
        yield SimpleNamespace(content="")


class ChatModelFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_langgraph_routes_model_decision_and_manual_preference(self):
        class RouteModel:
            available = True

            async def complete(self, system, transcript, temperature):
                self_test.assertIn('"route":"chat|planning"', system)
                self_test.assertEqual(temperature, 0.15)
                return '{"route":"planning","confidence":0.94,"reason":"明确制作课件"}'

        self_test = self
        workflow = ChatRouteWorkflow()
        request = ChatRouteRequest(user_id="7", messages=[{"role": "user", "content": "帮我制作课件"}])
        with patch("a12_ppt.chat_router.LLMClient", return_value=RouteModel()):
            result = await workflow.route(request)
            self.assertEqual(result["route"], "planning")
            self.assertEqual(result["next_stage"], "outline_graph")
            self.assertFalse(result["forced"])
            forced = await workflow.route(request.model_copy(update={"route_preference": "chat"}))
            self.assertEqual(forced["route"], "chat")
            self.assertEqual(forced["next_stage"], "ordinary_chat")
            self.assertTrue(forced["forced"])

    async def test_langgraph_keeps_explanation_in_chat_and_falls_back_safely(self):
        class RouteModel:
            available = True

            async def complete(self, _system, _transcript, _temperature):
                return '{"route":"chat","confidence":0.96,"reason":"询问如何制作"}'

        workflow = ChatRouteWorkflow()
        request = ChatRouteRequest(user_id="7", messages=[{"role": "user", "content": "如何制作课件？"}])
        with patch("a12_ppt.chat_router.LLMClient", return_value=RouteModel()):
            result = await workflow.route(request)
        self.assertEqual(result["route"], "chat")

        class BrokenModel:
            available = True

            async def complete(self, _system, _transcript, _temperature):
                raise RuntimeError("暂时不可用")

        with patch("a12_ppt.chat_router.LLMClient", return_value=BrokenModel()):
            fallback = await workflow.route(request)
        self.assertEqual(fallback["route"], "chat")
        self.assertEqual(fallback["confidence"], 0.0)

    async def test_chat_and_stream_use_routed_model_and_reasoning(self):
        client = LLMClient()
        client.settings = SimpleNamespace(
            openai_api_key="test-key", openai_base_url="https://example.test/v1",
            openai_model="test-model", openai_model_fast="", openai_model_standard="",
            openai_model_deep="", openai_model_vision="", request_timeout_seconds=10,
        )
        with patch("a12_ppt.llm.client.create_chat_model", return_value=_FakeModel()) as factory, \
                patch("a12_ppt.llm.client.record_run"), \
                patch("a12_ppt.llm.client.routed_model", return_value="test-model"):
            with use_runtime_options(model_profile="standard", reasoning_effort="high"):
                self.assertEqual(await client.complete("system", "user"), "课程建议")
                self.assertEqual([part async for part in client.complete_stream("system", "user")], ["课程", "建议"])
            self.assertEqual(factory.call_count, 2)
            for call in factory.call_args_list:
                self.assertEqual(call.args[0], "test-model")
                self.assertEqual(call.args[-1], "high")

    def test_model_factory_constructs_valid_provider_options(self):
        create_chat_model.cache_clear()
        with patch("a12_ppt.llm.model_factory.ChatOpenAI") as constructor:
            create_chat_model("qwen-test", "test-key", "https://dashscope.aliyuncs.com/compatible-mode/v1", 10, 0.2, "medium")
            self.assertEqual(constructor.call_args.kwargs["extra_body"], {"enable_thinking": True})
        create_chat_model.cache_clear()

    async def test_empty_stream_is_reported_as_failure(self):
        client = LLMClient()
        client.settings = SimpleNamespace(openai_api_key="test-key", openai_base_url="https://example.test/v1",
                                          request_timeout_seconds=10)
        with patch("a12_ppt.llm.client.create_chat_model", return_value=_EmptyModel()), \
                patch("a12_ppt.llm.client.record_run") as record, \
                patch("a12_ppt.llm.client.routed_model", return_value="test-model"):
            with self.assertRaisesRegex(RuntimeError, "没有返回可显示的正文"):
                [part async for part in client.complete_stream("system", "user")]
            self.assertEqual(record.call_args.args[0], "failed")


if __name__ == "__main__":
    unittest.main()
