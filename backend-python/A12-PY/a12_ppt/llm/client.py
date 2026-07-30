import httpx
from ..config import get_settings


class LLMClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._client: httpx.AsyncClient | None = None

    @property
    def available(self) -> bool:
        return bool(self.settings.openai_api_key)

    async def complete(self, system_prompt: str, user_prompt: str, temperature: float = 0.45) -> str:
        if not self.available:
            return ""
        url = self.settings.openai_base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self.settings.openai_model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        headers = {"Authorization": f"Bearer {self.settings.openai_api_key}"}
        if self._client is None:
            timeout = httpx.Timeout(self.settings.request_timeout_seconds)
            limits = httpx.Limits(max_connections=max(16, self.settings.max_slide_concurrency * 2), max_keepalive_connections=10)
            self._client = httpx.AsyncClient(timeout=timeout, limits=limits)
        response = await self._client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
