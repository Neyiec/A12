import asyncio
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import psycopg

from . import agent_evolution as evolution
from .direct_auth import direct_user_id, direct_user_role

router = APIRouter(prefix="/api/v1/python/agent-evolution")


def administrator():
    if not direct_user_id.get():
        raise HTTPException(401, "请先登录管理端")
    if direct_user_role.get() != "admin":
        raise HTTPException(403, "仅管理员可管理候选与发布")
    return direct_user_id.get()


async def execute(function, *args):
    try:
        return {"code": 200, "message": "success", "data": await asyncio.to_thread(function, *args)}
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except psycopg.Error as exc:
        raise HTTPException(503, "策略版本存储暂时不可用") from exc


@router.get("")
async def overview():
    administrator()
    return await execute(evolution.dashboard)


class CandidateRequest(BaseModel):
    template_update: bool = False


@router.post("/candidates")
async def derive(request: CandidateRequest):
    return await execute(evolution.derive_candidate, administrator(), request.template_update)


@router.post("/versions/{version_id}/approve")
async def approve(version_id: int):
    return await execute(evolution.approve, version_id, administrator())


class ReleaseRequest(BaseModel):
    action: Literal["canary", "promote", "rollback", "stop"]
    expected_revision: int = Field(ge=1)
    version_id: int | None = Field(default=None, ge=1)
    percent: Literal[5, 10, 20] = 10
    reason: str = Field(min_length=1, max_length=500)


@router.post("/release")
async def release(request: ReleaseRequest):
    return await execute(evolution.change_release, request.action, request.expected_revision, request.version_id,
                         request.percent, administrator(), request.reason)
