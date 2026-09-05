from typing import Any, AsyncIterator

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from ..config import get_settings
from .model_factory import create_chat_model_from_settings


class LLMClient:
    """大模型服务类"""
    def __init__(self) -> None:
        self.settings = get_settings()

    """判断是否存在API_KEY"""
    @property
    def available(self) -> bool:
        return bool(self.settings.openai_api_key)

    async def complete(self, system_prompt: str, user_prompt: str, temperature: float = 0.45) -> str:
        return await self.complete_messages([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ], temperature=temperature)

    async def complete_messages(self, messages: list[BaseMessage], temperature: float = 0.45) -> str:
        if not self.available:
            return ""

        model = create_chat_model_from_settings(self.settings, temperature=temperature)
        response = await model.ainvoke(messages)
        content = response.content
        if isinstance(content, str):
            return content
        return "".join(str(part) for part in content)

    async def invoke_tools(
        self,
        messages: list[BaseMessage],
        tools: list[dict[str, Any]],
        temperature: float = 0.1,
    ) -> AIMessage:
        """Invoke the chat model with native tool calling enabled."""
        if not self.available or not tools:
            return AIMessage(content="")
        model = create_chat_model_from_settings(self.settings, temperature=temperature)
        response = await model.bind_tools(tools).ainvoke(messages)
        if isinstance(response, AIMessage):
            return response
        return AIMessage(content=response.content or "")

    async def complete_stream(self, system_prompt: str, user_prompt: str, temperature: float = 0.45) -> AsyncIterator[str]:
        """流式补全：逐 token 产出文本片段。模型不可用时直接结束（不产出任何片段）。"""
        if not self.available:
            return
        model = create_chat_model_from_settings(self.settings, temperature=temperature)
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
        async for chunk in model.astream(messages):
            content = chunk.content
            if isinstance(content, str):
                text = content
            else:
                text = "".join(str(part) for part in content) if content else ""
            if text:
                yield text
