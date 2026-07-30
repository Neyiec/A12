import json
import uuid
from typing import Any

from ..llm import LLMClient
from ..models import LessonPlanGenerateRequest
from ..presentation.json_utils import extract_json


class LessonPlanGenerator:
    def __init__(self) -> None:
        self.llm = LLMClient()

    async def generate(self, request: LessonPlanGenerateRequest) -> dict[str, Any]:
        if self.llm.available:
            plan = await self._generate_with_model(request)
            if plan:
                return self._normalize_response(request, plan)
        return self._normalize_response(request, self._fallback_plan(request))

    async def _generate_with_model(self, request: LessonPlanGenerateRequest) -> dict[str, Any]:
        prompt = f"""
请根据 PPT 大纲和参考资料，生成一份可直接导出为 Word 的中文教师教案。

课程信息:
{json.dumps(request.model_dump(), ensure_ascii=False, indent=2, default=str)[:18000]}

必须返回严格 JSON，不要 Markdown。结构:
{{
  "title": "",
  "subject": "",
  "grade": "",
  "duration_minutes": 45,
  "teaching_goals": [],
  "key_points": [],
  "difficult_points": [],
  "teaching_methods": [],
  "teaching_resources": [],
  "lesson_process": [
    {{
      "stage": "导入",
      "duration_minutes": 5,
      "teacher_activity": "",
      "student_activity": "",
      "design_intent": "",
      "ppt_reference": ""
    }}
  ],
  "classroom_activities": [],
  "blackboard_design": "",
  "homework": [],
  "assessment": [],
  "reflection": ""
}}
""".strip()
        try:
            raw = await self.llm.complete("你是严谨的一线教师教案设计专家，只返回可解析 JSON。", prompt, 0.25)
            data = json.loads(extract_json(raw))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _fallback_plan(self, request: LessonPlanGenerateRequest) -> dict[str, Any]:
        slides = request.slides or list((request.outline or {}).get("slides") or [])
        goals = [request.teaching_goals] if request.teaching_goals else []
        points = []
        for slide in slides:
            title = slide.get("title") if isinstance(slide, dict) else None
            if title:
                points.append(str(title))
        process = []
        if slides:
            per_stage = max(3, int((request.duration_minutes or 45) / max(len(slides), 1)))
            for index, slide in enumerate(slides):
                title = str(slide.get("title") or f"第 {index + 1} 页") if isinstance(slide, dict) else f"第 {index + 1} 页"
                process.append({
                    "stage": title,
                    "duration_minutes": per_stage,
                    "teacher_activity": f"围绕“{title}”进行讲解、提问和板书梳理。",
                    "student_activity": "倾听、思考、回答问题并完成课堂记录。",
                    "design_intent": "帮助学生建立知识结构并落实核心概念。",
                    "ppt_reference": f"第 {index + 1} 页",
                })
        else:
            process = [
                {"stage": "导入", "duration_minutes": 5, "teacher_activity": "创设情境并提出核心问题。", "student_activity": "结合经验表达已有认识。", "design_intent": "激活先备知识。", "ppt_reference": ""},
                {"stage": "新授", "duration_minutes": 30, "teacher_activity": "讲解重点内容并组织探究。", "student_activity": "参与讨论、完成任务。", "design_intent": "形成系统理解。", "ppt_reference": ""},
                {"stage": "总结", "duration_minutes": 10, "teacher_activity": "归纳重点并布置作业。", "student_activity": "总结收获并提出疑问。", "design_intent": "巩固迁移。", "ppt_reference": ""},
            ]
        return {
            "title": request.title,
            "subject": request.subject or "",
            "grade": request.grade or "",
            "duration_minutes": request.duration_minutes or 45,
            "teaching_goals": goals or ["理解本课核心知识，能结合情境进行表达和应用。"],
            "key_points": points[:8],
            "difficult_points": points[:3],
            "teaching_methods": ["讲授法", "启发式提问", "任务驱动"],
            "teaching_resources": ["PPT课件", "参考资料", "课堂练习"],
            "lesson_process": process,
            "classroom_activities": ["围绕核心问题开展讨论或小组任务。"],
            "blackboard_design": request.title,
            "homework": ["整理本课知识结构。", "完成与本课知识点相关的巩固练习。"],
            "assessment": ["课堂问答", "任务完成情况", "课后作业"],
            "reflection": "课后根据学生反馈调整讲解节奏和活动设计。",
        }

    def _normalize_response(self, request: LessonPlanGenerateRequest, plan: dict[str, Any]) -> dict[str, Any]:
        plan.setdefault("title", request.title)
        plan.setdefault("subject", request.subject or "")
        plan.setdefault("grade", request.grade or "")
        plan.setdefault("duration_minutes", request.duration_minutes or 45)
        plan.setdefault("lesson_process", [])
        return {
            "lesson_plan_id": f"lesson_plan_{uuid.uuid4().hex[:12]}",
            "title": plan.get("title") or request.title,
            "lesson_plan": plan,
        }
