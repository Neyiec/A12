import unittest
from unittest.mock import AsyncMock

from langchain_core.messages import HumanMessage

from a12_ppt.outline_chat.workflow import OutlineChatWorkflow


class ModelClarificationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.workflow = OutlineChatWorkflow()
        self.workflow.llm = type("FakeModel", (), {"available": True})()
        self.workflow.llm.complete = AsyncMock()

    async def test_model_asks_one_contextual_question_with_choices(self):
        self.workflow.llm.complete.return_value = '''{
          "ask": true, "field": "grade", "text": "这节分数课面向哪个年级？",
          "options": [{"label": "三年级", "value": "三年级", "description": "初步认识分数"},
                      {"label": "五年级", "value": "五年级", "description": "分数运算"}]}
        '''
        question = await self.workflow._model_clarification(
            {"title": "分数课", "subject": "数学"}, [HumanMessage(content="帮我备一节分数课")], 0)
        self.assertEqual(question["text"], "这节分数课面向哪个年级？")
        self.assertEqual(question["round"], 1)
        self.assertEqual(question["questions"][0]["field"], "grade")
        self.assertEqual(len(question["questions"][0]["options"]), 2)

    async def test_model_can_start_without_question(self):
        self.workflow.llm.complete.return_value = '{"ask": false}'
        question = await self.workflow._model_clarification(
            {"title": "分数课"}, [HumanMessage(content="请直接设计")], 0)
        self.assertIsNone(question)

    async def test_three_questions_are_hard_limit_across_saved_messages(self):
        messages = [{"role": "assistant", "content": "问题", "metadata": {"type": "clarification"}}
                    for _ in range(3)]
        rounds = self.workflow._clarification_rounds(messages)
        self.assertEqual(rounds, 3)
        question = await self.workflow._model_clarification({}, [HumanMessage(content="继续")], rounds)
        self.assertIsNone(question)
        self.workflow.llm.complete.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
