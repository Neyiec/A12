from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from ..config import get_settings
from .model_factory import create_chat_model_from_settings


class LLMClient:
    def __init__(self) -> None:
        self.settings = get_settings()

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
