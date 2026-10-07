import json
import uuid
from typing import Any

from ..llm import LLMClient
from ..models import LessonPlanGenerateRequest
from ..presentation.json_utils import extract_json
from ..teaching_policy import teaching_model_guidance, teaching_policy, teaching_style_guidance


class LessonPlanGenerator:
    """教案生成器"""
    def __init__(self) -> None:
        self.llm = LLMClient()

    async def generate(self, request: LessonPlanGenerateRequest) -> dict[str, Any]:
        from ..direct_auth import direct_user_id
        user_id = direct_user_id.get()
        if user_id:
            from ..outline_chat.postgres_store import postgres_memory_store
            profile = postgres_memory_store.refresh_teacher_profile(user_id)
            outline = dict(request.outline or {})
            outline["teacher_style_summary"] = str(profile.get("style_summary") or "") if profile and profile.get("enabled", True) else ""
            request = request.model_copy(update={"outline": outline})
        if self.llm.available:
            plan = await self._generate_with_model(request)
            if plan:
                return self._normalize_response(request, plan)
        return self._normalize_response(request, self._fallback_plan(request))

    async def _generate_with_model(self, request: LessonPlanGenerateRequest) -> dict[str, Any]:
        outline = request.outline or {}
        model = request.teaching_model or outline.get("teaching_model") or "boppps"
        policy = teaching_policy(request.subject or outline.get("subject"))
        prompt = f"""
请根据 PPT 大纲和参考资料，生成一份可直接导出为 Word 的中文教师教案。

学科教学策略：{json.dumps(policy, ensure_ascii=False)}
教学模型：{teaching_model_guidance(model)}
教师风格偏好：{teaching_style_guidance(request.teaching_style or outline.get('teaching_style'))}
长期画像摘要：{str(outline.get('teacher_style_summary') or '')[:1200]}
本轮明确要求优先于长期画像。教案各阶段应与大纲 learning_phase 对应，PPT 引用填写真实页码。

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
                    "stage": str(slide.get("learning_phase") or title) if isinstance(slide, dict) else title,
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
            "teaching_methods": [teaching_policy(request.subject).get("method", "启发式提问")],
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
        model = request.teaching_model or (request.outline or {}).get("teaching_model") or "boppps"
        if model == "boppps":
            self._normalize_boppps(request, plan)
        return {
            "lesson_plan_id": f"lesson_plan_{uuid.uuid4().hex[:12]}",
            "title": plan.get("title") or request.title,
            "lesson_plan": plan,
        }

    def _normalize_boppps(self, request: LessonPlanGenerateRequest, plan: dict[str, Any]) -> None:
        """保证六阶段完整、课时守恒，页码只引用真实的大纲页面。"""
        phases = [
            ("bridge_in", "导入", "创设与本课相关的真实情境。", "表达已有经验并提出问题。"),
            ("objective", "学习目标", "说明可观察、可评价的学习目标。", "用自己的话解释本课要完成的任务。"),
            ("pre_assessment", "前测", "提出诊断性问题，了解先备知识。", "独立作答，说明思路和不确定之处。"),
            ("participatory_learning", "参与式学习", "示范案例并组织分组探究与练习。", "完成案例分析、合作探究和实践任务。"),
            ("post_assessment", "后测", "用新情境任务检查学习目标达成情况。", "独立完成迁移任务并解释解题依据。"),
            ("summary", "总结", "归纳知识关系并提供针对性反馈。", "回顾学习目标，总结收获与待解决的问题。"),
        ]
        aliases = {"bridge_in": ["导入", "bridge"], "objective": ["目标", "objective"],
                   "pre_assessment": ["前测", "pre_assessment"],
                   "participatory_learning": ["参与", "新授", "探究", "participatory"],
                   "post_assessment": ["后测", "post_assessment"], "summary": ["总结", "summary"]}
        source = [item for item in plan.get("lesson_process", []) if isinstance(item, dict)] if isinstance(plan.get("lesson_process"), list) else []
        slides = request.slides or (request.outline or {}).get("slides") or []
        duration = max(6, int(request.duration_minutes or 45))
        # 参与式学习承担主要课时，其余阶段始终至少一分钟。
        weights = [0.10, 0.05, 0.10, 0.55, 0.12, 0.08]
        times = [1 + int((duration - 6) * weight) for weight in weights]
        times[3] += duration - sum(times)
        process = []
        for index, (phase, label, teacher, student) in enumerate(phases):
            matched = [item for item in source if item.get("learning_phase") == phase or
                       any(alias in str(item.get("stage") or "").lower() for alias in aliases[phase])]
            if phase == "participatory_learning":
                matched += [item for item in source if item not in matched and
                            item.get("learning_phase") not in aliases and
                            not any(alias in str(item.get("stage") or "").lower()
                                    for values in aliases.values() for alias in values)]
            row = dict(matched[0]) if matched else {}
            row.update(stage=label, learning_phase=phase, duration_minutes=times[index])
            row["teacher_activity"] = "；".join(str(item["teacher_activity"]) for item in matched if item.get("teacher_activity")) or teacher
            row["student_activity"] = "；".join(str(item["student_activity"]) for item in matched if item.get("student_activity")) or student
            row["design_intent"] = row.get("design_intent") or f"落实{label}阶段的教学目标。"
            pages = [str(i + 1) for i, slide in enumerate(slides) if isinstance(slide, dict) and slide.get("learning_phase") == phase]
            row["ppt_reference"] = "第 " + "、".join(pages) + " 页" if pages else ""
            process.append(row)
        plan["duration_minutes"] = duration
        plan["teaching_model"] = "boppps"
        plan["lesson_process"] = process
