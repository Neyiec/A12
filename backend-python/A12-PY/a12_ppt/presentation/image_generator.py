"""PPT 文生图客户端。

当前实现使用百炼 DashScope 异步文生图协议。生成结果会立即下载并转成 data URL，
避免百炼结果链接过期后导致历史课件或导出的 PPT 丢图。
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from ..config import get_settings


@dataclass(frozen=True)
class GeneratedImage:
    source_url: str
    data_url: str
    prompt: str
    model: str
    cache_key: str


class ImageGenerationClient:
    """调用百炼文生图并把短期 URL 固化成本地缓存和 data URL。"""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.cache_dir = Path(__file__).resolve().parents[2] / "data" / "generated_images"

    @property
    def available(self) -> bool:
        return bool(self.settings.image_generation_api_key and self.settings.image_generation_model)

    async def generate(self, prompt: str, aspect_ratio: str = "16:9") -> GeneratedImage | None:
        prompt = (prompt or "").strip()[:1800]
        if not self.available or not prompt:
            return None

        cache_key = hashlib.sha256(
            f"{self.settings.image_generation_model}\n{aspect_ratio}\n{prompt}".encode("utf-8")
        ).hexdigest()
        cached = self._read_cache(cache_key, prompt)
        if cached:
            return cached

        headers = {
            "Authorization": f"Bearer {self.settings.image_generation_api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        }
        size = "1024*768" if aspect_ratio == "4:3" else "1280*720"
        payload = {
            "model": self.settings.image_generation_model,
            "input": {
                "prompt": prompt,
                "negative_prompt": "文字，字幕，水印，标志，二维码，低清晰度，构图混乱，错误肢体",
            },
            "parameters": {"size": size, "n": 1},
        }
        timeout = httpx.Timeout(self.settings.image_generation_timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            created = await client.post(
                f"{self.settings.image_generation_base_url}/services/aigc/text2image/image-synthesis",
                headers=headers,
                json=payload,
            )
            created.raise_for_status()
            body = created.json()
            task_id = str((body.get("output") or {}).get("task_id") or "")
            if not task_id:
                raise RuntimeError(body.get("message") or "文生图服务没有返回 task_id")

            deadline = asyncio.get_running_loop().time() + self.settings.image_generation_timeout_seconds
            source_url = ""
            while asyncio.get_running_loop().time() < deadline:
                await asyncio.sleep(max(0.5, self.settings.image_generation_poll_interval_seconds))
                result = await client.get(
                    f"{self.settings.image_generation_base_url}/tasks/{task_id}",
                    headers={"Authorization": headers["Authorization"]},
                )
                result.raise_for_status()
                result_body: dict[str, Any] = result.json()
                output = result_body.get("output") or {}
                status = str(output.get("task_status") or "").upper()
                if status == "SUCCEEDED":
                    results = output.get("results") or []
                    source_url = str((results[0] if results else {}).get("url") or "")
                    break
                if status in {"FAILED", "CANCELED", "UNKNOWN"}:
                    raise RuntimeError(result_body.get("message") or f"文生图任务失败：{status}")
            if not source_url:
                raise TimeoutError("文生图任务等待超时")

            downloaded = await client.get(source_url)
            downloaded.raise_for_status()
            image_bytes = downloaded.content
            if not image_bytes or len(image_bytes) > 15 * 1024 * 1024:
                raise RuntimeError("生成图片为空或超过 15MB 限制")
            content_type = (downloaded.headers.get("content-type") or "").split(";", 1)[0]
            if not content_type.startswith("image/"):
                content_type = mimetypes.guess_type(source_url)[0] or "image/png"

        return self._write_cache(cache_key, prompt, source_url, content_type, image_bytes)

    def _read_cache(self, cache_key: str, prompt: str) -> GeneratedImage | None:
        for suffix, content_type in (("png", "image/png"), ("jpg", "image/jpeg"), ("webp", "image/webp")):
            path = self.cache_dir / f"{cache_key}.{suffix}"
            if path.exists() and path.stat().st_size:
                encoded = base64.b64encode(path.read_bytes()).decode("ascii")
                return GeneratedImage("", f"data:{content_type};base64,{encoded}", prompt, self.settings.image_generation_model, cache_key)
        return None

    def _write_cache(
        self, cache_key: str, prompt: str, source_url: str, content_type: str, image_bytes: bytes
    ) -> GeneratedImage:
        suffix = {"image/jpeg": "jpg", "image/webp": "webp"}.get(content_type, "png")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        (self.cache_dir / f"{cache_key}.{suffix}").write_bytes(image_bytes)
        encoded = base64.b64encode(image_bytes).decode("ascii")
        return GeneratedImage(
            source_url=source_url,
            data_url=f"data:{content_type};base64,{encoded}",
            prompt=prompt,
            model=self.settings.image_generation_model,
            cache_key=cache_key,
        )
