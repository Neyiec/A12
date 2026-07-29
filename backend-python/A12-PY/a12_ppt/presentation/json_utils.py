import re


def extract_json(raw: str) -> str:
    match = re.search(r"```(?:json)?\s*(.*?)```", raw or "", flags=re.DOTALL)
    if match:
        return match.group(1)
    start = (raw or "").find("{")
    end = (raw or "").rfind("}")
    return raw[start:end + 1] if start >= 0 and end > start else raw


def split_points(text: str) -> list[str]:
    parts = re.split(r"[，。；、\n,.!?！？]", text or "")
    return [part.strip() for part in parts if part.strip()][:8] or ["核心概念", "关键方法", "实践应用"]
