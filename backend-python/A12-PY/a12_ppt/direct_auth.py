"""FastAPI 直连鉴权；Java 仍是账号与资源权限的权威服务。"""

import json
import os
import secrets
from contextvars import ContextVar

import httpx
from fastapi import HTTPException
import redis.asyncio as async_redis
from redis.exceptions import RedisError


direct_user_id: ContextVar[str | None] = ContextVar("direct_user_id", default=None)
direct_bearer: ContextVar[str | None] = ContextVar("direct_bearer", default=None)
direct_user_role: ContextVar[str | None] = ContextVar("direct_user_role", default=None)


async def verify_active_token(user_id: str, token: str) -> None:
    """与 Java 共用 Redis 登录态：过期或异地登录替换的令牌立即失效。"""
    if not user_id.isdecimal() or not token:
        raise HTTPException(status_code=401, detail="令牌无效")
    redis_url = os.getenv("A12_AUTH_REDIS_URL") or os.getenv(
        "A12_RESOURCE_REDIS_URL", "redis://127.0.0.1:6379/0")
    try:
        async with async_redis.from_url(redis_url, decode_responses=True,
                                        socket_connect_timeout=3, socket_timeout=3) as client:
            stored = await client.get(f"token:user:{user_id}")
    except RedisError:
        raise HTTPException(status_code=503, detail="登录状态服务暂时不可用") from None
    if not stored or not secrets.compare_digest(stored, token):
        raise HTTPException(status_code=401, detail="令牌已过期或已被替换")


async def require_active_browser_token() -> None:
    """在模型调用点复核令牌；可信的后台索引任务没有浏览器令牌。"""
    token = direct_bearer.get()
    user_id = direct_user_id.get()
    if token or user_id:
        await verify_active_token(user_id or "", token or "")


def internal_request_allowed(value: str | None) -> bool:
    configured = os.getenv("A12_PYTHON_INTERNAL_KEY", "")
    return bool(configured and value and secrets.compare_digest(configured, value))


async def authenticate_browser(authorization: str | None) -> tuple[str, str, str]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="请先登录")
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="请先登录")
    java_url = os.getenv("JAVA_AUTH_BASE_URL", "http://127.0.0.1:8088").rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.get(f"{java_url}/api/v1/users/me",
                                        headers={"Authorization": f"Bearer {token}"})
        if response.status_code == 401:
            raise HTTPException(status_code=401, detail="令牌已过期或已被替换")
        response.raise_for_status()
        result = response.json()
        if result.get("code") not in (0, 200) or not isinstance(result.get("data"), dict):
            raise HTTPException(status_code=401, detail="令牌无效")
        user_id = result["data"].get("id")
        if not isinstance(user_id, int) or user_id <= 0:
            raise HTTPException(status_code=401, detail="令牌无效")
        return str(user_id), token, str(result["data"].get("user_type") or "")
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError, KeyError):
        raise HTTPException(status_code=503, detail="账号服务暂时不可用") from None


def reject_identity_spoofing(body: bytes, query: dict[str, str], user_id: str) -> None:
    if "user_id" in query and query["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="不能访问其他用户的数据")
    if not body:
        return
    try:
        payload = json.loads(body)
    except ValueError:
        return  # 请求格式由 FastAPI/Pydantic 校验。

    def inspect(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in ("user_id", "owner_user_id", "uploaded_by") and item is not None and str(item) != user_id:
                    raise HTTPException(status_code=403, detail="不能指定其他用户的身份")
                inspect(item)
        elif isinstance(value, list):
            for item in value:
                inspect(item)

    inspect(payload)


async def signed_personal_resource_url(resource_id: str, *, require_ai_permission: bool = False) -> str:
    """从 Java 资源服务校验所有权并获取签名 URL，不信任浏览器给的 file_url。"""
    token = direct_bearer.get()
    if not token or not resource_id.isdecimal():
        raise HTTPException(status_code=403, detail="无权访问该资源")
    java_url = os.getenv("JAVA_AUTH_BASE_URL", "http://127.0.0.1:8088").rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            if require_ai_permission:
                details = await client.get(f"{java_url}/api/v1/resources/{resource_id}",
                                           headers={"Authorization": f"Bearer {token}"})
                if details.status_code in (401, 403):
                    raise HTTPException(status_code=details.status_code, detail="无法读取该教案的授权状态")
                details.raise_for_status()
                envelope = details.json()
                material = envelope.get("data") or {}
                if envelope.get("code") not in (0, 200) or material.get("allow_ai") != 1:
                    raise HTTPException(status_code=403, detail="请先在资源库允许 AI 使用该教案")
                if not str(material.get("file_name") or "").lower().endswith(".docx"):
                    raise HTTPException(status_code=400, detail="格式转换目前支持 .docx 教案")
            response = await client.post(f"{java_url}/api/v1/resources/{resource_id}/download-url",
                                         headers={"Authorization": f"Bearer {token}"})
        if response.status_code == 401:
            raise HTTPException(status_code=401, detail="令牌已过期或已被替换")
        response.raise_for_status()
        result = response.json()
        url = (result.get("data") or {}).get("download_url") if result.get("code") in (0, 200) else None
        if not isinstance(url, str) or not url:
            raise HTTPException(status_code=403, detail="无权访问该资源")
        return url
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError):
        raise HTTPException(status_code=503, detail="资源权限服务暂时不可用") from None


async def signed_public_resource_url(resource_id: str) -> str:
    """管理员直连索引时，从 Java 业务服务获取可信的公共资源签名 URL。"""
    token = direct_bearer.get()
    if not token or not resource_id.isdecimal():
        raise HTTPException(status_code=403, detail="无权访问该资源")
    java_url = os.getenv("JAVA_AUTH_BASE_URL", "http://127.0.0.1:8088").rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.get(
                f"{java_url}/api/v1/admin/public-resources/{resource_id}/download-url",
                headers={"Authorization": f"Bearer {token}"},
            )
        response.raise_for_status()
        result = response.json()
        url = (result.get("data") or {}).get("download_url") if result.get("code") in (0, 200) else None
        if not isinstance(url, str) or not url:
            raise HTTPException(status_code=403, detail="无权访问该资源")
        return url
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError):
        raise HTTPException(status_code=503, detail="公共资源服务暂时不可用") from None


async def hydrate_public_registration(request) -> None:
    """Business registration is authoritative; browser metadata cannot invent a source."""
    token = direct_bearer.get()
    if not token or not request.resource_id.isdecimal():
        raise HTTPException(403, '无权访问该资源')
    java_url = os.getenv('JAVA_AUTH_BASE_URL', 'http://127.0.0.1:8088').rstrip('/')
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.get(f'{java_url}/api/v1/admin/public-resources/{request.resource_id}',
                                        headers={'Authorization': f'Bearer {token}'})
        response.raise_for_status()
        envelope = response.json()
        if envelope.get('code') not in (0, 200):
            raise HTTPException(403, '无法读取公共来源登记')
        record = envelope.get('data') or {}
        if hasattr(request, 'title'):
            request.title = record.get('title') or request.title
        if hasattr(request, 'file_size'):
            request.file_size = record.get('file_size')
        provenance = json.loads(record.get('source_metadata') or '{}')
        request.metadata.update({'provenance': provenance, 'ingested_at': record.get('created_at'),
                                 'subject': record.get('subject'), 'grade': record.get('grade'),
                                 '_business_registration': {'source_metadata': record.get('source_metadata'), 'file_url': record.get('file_url')}})
        request.metadata.pop('source_check', None)
        request.metadata.pop('superseded', None)
        request.available = record.get('status') == 1
        request.allow_ai = record.get('status') == 1
    except (httpx.HTTPError, ValueError):
        raise HTTPException(503, '公共来源登记服务暂时不可用') from None


async def acknowledge_public_index(resource_id, result, metadata):
    """Persist only business status after direct AI calls; failures stay visible to the caller."""
    status = {'indexed': 'completed', 'skipped': 'completed', 'failed': 'failed', 'disabled': 'disabled'}.get(result.get('status'))
    if not status:
        return False
    snapshot = metadata.get('_business_registration') or {}
    java_url = os.getenv('JAVA_AUTH_BASE_URL', 'http://127.0.0.1:8088').rstrip('/')
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.post(f'{java_url}/api/v1/admin/public-resources/{resource_id}/index-result',
                headers={'Authorization': 'Bearer ' + (direct_bearer.get() or '')},
                json={'status': status, 'expected_source_metadata': snapshot.get('source_metadata'), 'expected_file_url': snapshot.get('file_url')})
        return response.is_success and response.json().get('code') in (0, 200)
    except (httpx.HTTPError, ValueError):
        return False
