import asyncio
from types import SimpleNamespace

from a12_ppt.ai_runtime import current_runtime, use_auxiliary_reasoning, use_runtime_options
from a12_ppt.outline_chat.tool_node import OutlineToolNode, ToolPlan
from a12_ppt.outline_chat.workflow import OutlineChatWorkflow
from unittest.mock import AsyncMock, patch
import json


def test_auxiliary_reasoning_preserves_identity_and_restores_on_failure():
    with use_runtime_options(user_id="7", model_profile="deep", reasoning_effort="high"):
        original = current_runtime()
        try:
            with use_auxiliary_reasoning():
                assert current_runtime().reasoning_effort == "low"
                assert current_runtime().user_id == "7"
                assert current_runtime().model_profile == "deep"
                assert current_runtime().run_id == original.run_id
                raise ValueError("failed planner")
        except ValueError:
            pass
        assert current_runtime() == original


def test_intent_and_clarification_use_light_reasoning_only_for_auxiliary_calls():
    class Model:
        available = True

        async def complete(self, *args):
            assert current_runtime().reasoning_effort == "low"
            return '{"title":"微积分入门","ask":false}'

    async def run():
        workflow = OutlineChatWorkflow.__new__(OutlineChatWorkflow)
        workflow.llm = Model()
        with use_runtime_options(reasoning_effort="high"):
            result = await workflow._extract_intent_with_model([], {})
            assert result["title"] == "微积分入门"
            assert await workflow._model_clarification(result, [], 0) is None
            assert current_runtime().reasoning_effort == "high"
    asyncio.run(run())


def test_rule_retrieval_runs_before_optional_planner_finishes_and_never_repeats():
    async def run():
        node = OutlineToolNode.__new__(OutlineToolNode)
        node.mcp_client = SimpleNamespace(enabled=False)
        retrieval_started = asyncio.Event()
        planning_started = asyncio.Event()
        executed = []

        async def plan(*args, **kwargs):
            planning_started.set()
            await retrieval_started.wait()
            return [ToolPlan("rag_search", {}, "llm_native"),
                    ToolPlan("diagram_tool", {}, "llm_native")]

        async def execute(item, specs):
            executed.append(item.name)
            if item.name == "rag_search":
                retrieval_started.set()
                await planning_started.wait()
                return {"context": "教材内容"}, 1
            return {"nodes": []}, 1

        node._autonomous_plans = plan
        node._execute_timed = execute
        node._rule_plans = lambda *args: [ToolPlan("rag_search", {}, "rule")]
        # A serial planner/retrieval implementation deadlocks on this barrier.
        result = await asyncio.wait_for(node({"intent": {"title": "测试", "enable_rag": True}}), 2)
        assert executed == ["rag_search", "diagram_tool"]
        assert result["tool_context"]["rag"]["context"] == "教材内容"
        assert len(result["tool_trace"]) == 2
    asyncio.run(run())


def test_graph_timeout_switches_to_fast_budget_and_emits_progress():
    from a12_ppt.outline_chat.learning_graphs import build_learning_graphs
    from test_course_graph import ai_proposal

    async def run():
        seen = []
        progress = []

        async def complete(*args):
            runtime = current_runtime()
            seen.append(runtime)
            if len(seen) == 1:
                raise TimeoutError()
            return json.dumps(ai_proposal())

        model = SimpleNamespace(available=True, complete=complete)
        with use_runtime_options(user_id="7", model_profile="deep", reasoning_effort="high"):
            original = current_runtime()
            result = await build_learning_graphs({"title": "光的折射"}, {}, {"_progress": progress.append}, model)
            assert current_runtime() == original
        assert result["generation"]["attempts"] == 2
        assert [r.model_profile for r in seen] == ["deep", "fast"]
        assert [r.request_timeout_seconds for r in seen] == [45, 30]
        assert all(r.max_retries == 0 and r.reasoning_effort == "low" for r in seen)
        assert "最后一次尝试" in progress[-1]["data"]["message"]
    asyncio.run(run())


def test_graph_budget_reaches_real_model_constructor_without_sdk_retry():
    from a12_ppt.ai_runtime import use_graph_generation_budget
    from a12_ppt.llm.client import LLMClient

    async def run():
        client = LLMClient()
        client.settings = SimpleNamespace(openai_api_key="test", openai_base_url="https://example.test",
                                         request_timeout_seconds=90)
        model = SimpleNamespace(ainvoke=AsyncMock(return_value=SimpleNamespace(content="{}", usage_metadata={})))
        with patch("a12_ppt.llm.client.create_chat_model", return_value=model) as factory, \
             patch("a12_ppt.llm.client.record_run"), \
             patch("a12_ppt.llm.client.require_active_browser_token", new=AsyncMock()):
            with use_graph_generation_budget(45):
                await client.complete("system", "user")
            assert factory.call_args.args[3] == 45
            assert factory.call_args.kwargs["max_retries"] == 0
    asyncio.run(run())
