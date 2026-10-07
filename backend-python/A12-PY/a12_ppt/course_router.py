"""教师课程工作台 API，浏览器直连 Python，不经 Java 转发。"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from .models import Result
from .direct_auth import direct_user_id
from .course_graph import course_graph_store, GraphVersionConflict
from .learning_path import plan_learning_path, prune_graph
from .course_draft import extract_course_draft, outline_from_path


class DraftRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    subject: str = Field(default="", max_length=80)
    source_text: str = Field(default="", max_length=60000)
    resource_ids: list[str] = Field(default_factory=list, max_length=20)


class PathRequest(BaseModel):
    target_ids: list[str] = Field(min_length=1, max_length=24)
    start_id: str | None = None
    mastered_ids: list[str] = Field(default_factory=list, max_length=300)
    ordered_ids: list[str] | None = Field(default=None, max_length=24)
    subject: str = Field(default="", max_length=80)
    grade: str = Field(default="", max_length=80)


class PruneRequest(BaseModel):
    seed_ids: list[str] = Field(min_length=1, max_length=30)
    hops: int = Field(default=1, ge=0, le=5)
    max_nodes: int = Field(default=16, ge=1, le=50)
    token_budget: int = Field(default=3000, ge=200, le=12000)


class RestoreRequest(BaseModel):
    version: int = Field(ge=1)
    expected_version: int = Field(ge=1)


def current_teacher():
    user_id = direct_user_id.get()
    if not user_id:
        raise HTTPException(status_code=401, detail="请先登录")
    return user_id


def owned_graph(course_id):
    graph = course_graph_store.get(current_teacher(), course_id)
    if not graph:
        raise HTTPException(status_code=404, detail="课程图谱不存在")
    return graph


def validated_path(graph, request):
    path = plan_learning_path(graph, request.target_ids, request.start_id, request.mastered_ids)
    if request.ordered_ids is not None:
        positions = {node_id: index for index, node_id in enumerate(request.ordered_ids)}
        if len(positions) != len(request.ordered_ids) or set(positions) != {node["id"] for node in path["nodes"]}:
            raise ValueError("手工路径必须保留所有必要先修节点且不能重复")
        if any(positions[edge["source"]] >= positions[edge["target"]] for edge in path["edges"] if edge["relation"] == "prerequisite"):
            raise ValueError("手工路径违反先修顺序")
        path["nodes"] = sorted(path["nodes"], key=lambda node: positions[node["id"]])
    return path


def create_course_router(generator):
    router = APIRouter(prefix="/api/v1/python/courses", tags=["课程双图谱与学习路径"])

    @router.get("")
    async def list_courses():
        return Result(data=course_graph_store.list_courses(current_teacher()))

    @router.post("/graph/draft")
    async def draft(request: DraftRequest):
        current_teacher()
        try:
            return Result(data=await extract_course_draft(request.model_dump(), generator.llm))
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        except Exception as exc:
            raise HTTPException(503, "课程图谱抽取暂时不可用，请检查模型或资料") from exc

    @router.get("/{course_id}/versions")
    async def versions(course_id: str):
        owned_graph(course_id)
        return Result(data=course_graph_store.versions(current_teacher(), course_id))

    @router.post("/{course_id}/restore")
    async def restore(course_id: str, request: RestoreRequest):
        owned_graph(course_id)
        graph = course_graph_store.get_version(current_teacher(), course_id, request.version)
        if not graph:
            raise HTTPException(404, "历史图谱版本不存在")
        try:
            return Result(data=course_graph_store.put(current_teacher(), course_id, graph["title"], graph, request.expected_version))
        except GraphVersionConflict as exc:
            raise HTTPException(409, str(exc)) from exc

    @router.post("/{course_id}/learning-path")
    async def learning_path(course_id: str, request: PathRequest):
        try:
            return Result(data=validated_path(owned_graph(course_id), request))
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @router.post("/{course_id}/prune")
    async def prune(course_id: str, request: PruneRequest):
        graph = owned_graph(course_id)
        try:
            result = prune_graph(graph, request.seed_ids, request.hops, request.max_nodes, request.token_budget)
            return Result(data={"course_id": course_id, "version": graph["version"], **result})
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @router.post("/{course_id}/path-outline")
    async def path_outline(course_id: str, request: PathRequest):
        graph = owned_graph(course_id)
        try:
            path = validated_path(graph, request)
            return Result(data={"outline": outline_from_path(graph, path, request.subject, request.grade)})
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    return router
