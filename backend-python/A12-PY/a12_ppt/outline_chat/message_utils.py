from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage


def dict_to_message(item: dict[str, Any]) -> BaseMessage:
    role = str(item.get("role") or "user")
    content = str(item.get("content") or "")
    if role == "assistant":
        return AIMessage(content=content)
    if role == "system":
        return SystemMessage(content=content)
    return HumanMessage(content=content)


def message_to_dict(message: BaseMessage) -> dict[str, str]:
    if isinstance(message, AIMessage):
        role = "assistant"
    elif isinstance(message, SystemMessage):
        role = "system"
    else:
        role = "user"
    content = message.content
    if not isinstance(content, str):
        content = "".join(str(part) for part in content)
    return {"role": role, "content": content}


def normalize_messages(items: list[dict[str, Any]] | list[BaseMessage]) -> list[BaseMessage]:
    messages: list[BaseMessage] = []
    for item in items or []:
        if isinstance(item, BaseMessage):
            messages.append(item)
        elif isinstance(item, dict):
            messages.append(dict_to_message(item))
    return messages


def messages_to_dicts(messages: list[BaseMessage]) -> list[dict[str, str]]:
    return [message_to_dict(message) for message in messages]


def message_text(message: BaseMessage) -> str:
    content = message.content
    return content if isinstance(content, str) else "".join(str(part) for part in content)
