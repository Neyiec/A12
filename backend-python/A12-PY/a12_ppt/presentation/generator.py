import asyncio
import base64
import html
import json
import re
import uuid
from typing import Any, AsyncIterator

from ..config import get_settings
from .html_utils import auto_close_basic_tags, clean_html_response, validate_html
from .json_utils import extract_json, split_points
from .palette import fallback_palette
from .prompts import (
    global_constitution_prompt,
    page_briefs_prompt,
    repair_html_prompt,
    slide_html_prompt,
    style_gene_prompt,
)
from ..llm import LLMClient
from ..models import InteractiveModuleGenerateRequest, OutlineGenerateRequest, OutlineUpdateRequest, PresentationGenerateRequest, PresentationModifyRequest, SlideModifyRequest
from ..resources import build_rag_context
from .template_store import DEFAULT_THEME, get_template


class PPTGenerator:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.llm = LLMClient()

    async def generate_outline(self, req: OutlineGenerateRequest) -> dict[str, Any]:
        slide_count = req.slide_count or 8
        req = await self._with_reference_and_rag_context(req)
        outline = await self._generate_outline_with_model(req, slide_count) if self.llm.available else self._fallback_outline(req, slide_count)
        return self._decorate_outline(outline, req)

    async def stream_outline(self, req: OutlineGenerateRequest) -> AsyncIterator[dict[str, Any]]:
        """流式生成大纲：模型边产出边抽取完整 slide 对象并产出 outline_delta，最终产出 final。

        - 产出 `{"type": "slide", "slide": {...}, "index": n}`：一页大纲增量（预览用，尚未经规范化）。
        - 产出 `{"type": "final", "response": {...}}`：规范化后的完整结果（与 generate_outline 返回一致）。
        """
        slide_count = req.slide_count or 8
        req = await self._with_reference_and_rag_context(req)
        if not self.llm.available:
            outline = self._fallback_outline(req, slide_count)
            yield {"type": "final", "response": self._decorate_outline(outline, req)}
            return

        buffer = ""
        array_start = -1
        scan_pos = 0
        emitted = 0
        async for token in self.llm.complete_stream("你是资深教学设计专家，只输出可解析 JSON。", self._outline_prompt(req, slide_count), 0.25):
            buffer += token
            if array_start < 0:
                probe = buffer.find('"slides"')
                if probe != -1:
                    bracket = buffer.find('[', probe)
                    if bracket != -1:
                        array_start = bracket + 1
            if array_start >= 0:
                slides, scan_pos = self._extract_completed_slides(buffer, array_start, scan_pos)
                for slide in slides:
                    emitted += 1
                    yield {"type": "slide", "slide": slide, "index": emitted}

        # 流结束后用完整文本做规范化与结构化后处理
        try:
            data = json.loads(self._extract_json(buffer))
            if isinstance(data, dict) and data.get("slides"):
                outline = self._normalize_outline(data, req.title)
            else:
                outline = self._fallback_outline(req, slide_count)
        except Exception:
            outline = self._fallback_outline(req, slide_count)
        yield {"type": "final", "response": self._decorate_outline(outline, req)}

    def _decorate_outline(self, outline: dict[str, Any], req: OutlineGenerateRequest) -> dict[str, Any]:
        slide_count = req.slide_count or 8
        outline["subject"] = req.subject
        outline["grade"] = req.grade
        outline["requirements"] = req.requirements
        outline["generation_options"] = {
            "resource_ids": req.resource_ids,
            "enable_web": req.enable_web,
            "enable_rag": req.enable_rag,
            "regenerate_instruction": req.regenerate_instruction,
            "interactive_policy": req.interactive_policy,
        }
        return self._outline_response(self._ensure_outline_quality(self._ensure_teaching_design_chain(self._ensure_interactive_assets(outline, req, slide_count), req), req, slide_count))

    async def update_outline(self, req: OutlineUpdateRequest) -> dict[str, Any]:
        outline = dict(req.outline or {})
        if not self.llm.available:
            outline["revision_note"] = req.instruction
            outline = self._finalize_existing_outline(outline)
            return self._outline_response(outline)

        rag_context = ""
        if req.enable_rag:
            from ..tools.rag import rag_search
            query = "\n".join([
                req.instruction or "",
                json.dumps(req.outline, ensure_ascii=False)[:4000],
            ]).strip()
            rag_result = await rag_search(req.resource_ids, query)
            rag_context = rag_result.get("context", "")
        prompt = f"""
请根据用户要求修订或重生成 PPT 大纲。只输出严格 JSON，不要 Markdown。

用户要求：
{req.instruction}

是否启用联网增强：{req.enable_web}
是否启用 RAG 增强：{req.enable_rag}

原大纲：
{json.dumps(req.outline, ensure_ascii=False)}

RAG 资料：
{rag_context[:12000]}

JSON 字段：title, summary, slides。
slides 每项字段：slide_no, title, slide_type, content_points(list), teaching_intent, visual_suggestion。
""".strip()
        try:
            raw = await self.llm.complete("你是资深教学设计专家，只输出可解析 JSON。", prompt, 0.35)
            data = json.loads(self._extract_json(raw))
            if isinstance(data, dict) and data.get("slides"):
                outline = self._normalize_outline(data, str(data.get("title") or outline.get("title") or "未命名大纲"))
        except Exception:
            outline["revision_note"] = req.instruction
        outline = self._finalize_existing_outline(outline)
        return self._outline_response(outline)

    async def generate_presentation(self, req: PresentationGenerateRequest) -> dict[str, Any]:
        slides = self._normalize_slides_for_deck(self._extract_slides(req.outline) or self._fallback_outline_from_title(req.title, 6))
        interactive_assets = self._normalize_interactive_assets((req.outline or {}).get("interactive_assets") or ((req.outline or {}).get("outline") or {}).get("interactive_assets") or [])
        if interactive_assets:
            interactive_assets = await self._materialize_interactive_assets(req, slides, interactive_assets)
            slides = self._attach_interactive_assets(slides, interactive_assets)
        requested_theme = (req.theme or DEFAULT_THEME).strip()
        template = get_template(requested_theme) or {}
        template_name = str(template.get("_selected_theme") or template.get("template_name") or requested_theme)
        template_html = str(template.get("html_template") or "")
        missing_template = bool(template.get("_missing_template"))
        request_context = self._request_context(req)
        quality_assets = await self._build_quality_assets(req.title, requested_theme, template_name, template_html, request_context, slides)

        semaphore = asyncio.Semaphore(max(1, self.settings.max_slide_concurrency))
        generated: list[dict[str, Any] | None] = [None] * len(slides)

        async def build(index: int, slide: dict[str, Any]) -> None:
            async with semaphore:
                slide_no = index + 1
                slide_markup = await self._generate_slide_html(
                    title=req.title,
                    slide=slide,
                    slide_no=slide_no,
                    total=len(slides),
                    theme=requested_theme,
                    template_name=template_name,
                    template_html=template_html,
                    request_context=request_context,
                    all_slides=slides,
                    quality_assets=quality_assets,
                )
                generated[index] = {
                    "slide_no": slide_no,
                    "title": str(slide.get("title") or f"第 {slide_no} 页"),
                    "html": slide_markup,
                    "notes": self._speaker_notes(slide),
                    "interactive_assets": slide.get("interactive_assets", []),
                    "metadata": {
                        "theme": requested_theme,
                        "requested_theme": requested_theme,
                        "template_name": template_name,
                        "missing_template": missing_template,
                        "aspect_ratio": req.aspect_ratio,
                        "quality_pipeline": self.llm.available and self.settings.enable_quality_pipeline,
                        "quality_preset": self.settings.quality_preset,
                        "interactive_assets": slide.get("interactive_assets", []),
                    },
                }

        await asyncio.gather(*(build(i, slide) for i, slide in enumerate(slides)))
        slide_results = [item for item in generated if item is not None]
        return {
            "presentation_id": f"ppt_{uuid.uuid4().hex[:12]}",
            "title": req.title,
            "slide_count": len(slide_results),
            "slides": slide_results,
            "html": self._combine_deck(req.title, slide_results),
            "metadata": {
                "requested_theme": requested_theme,
                "template_name": template_name,
                "missing_template": missing_template,
                "quality_pipeline": self.llm.available and self.settings.enable_quality_pipeline,
                "quality_preset": self.settings.quality_preset,
                "max_slide_concurrency": self.settings.max_slide_concurrency,
                "max_html_retries": self.settings.max_html_retries,
                "interactive_assets": interactive_assets,
            },
        }

    async def modify_slide(self, req: SlideModifyRequest) -> dict[str, Any]:
        changed = ""
        if self.llm.available:
            prompt = self._slide_modify_prompt(req)
            changed = await self._complete_html_with_retry(prompt, self._html_system_prompt(), {}, req.slide_no, 1)
        if not changed:
            changed = self._fallback_modify(req.current_html, req.instruction)
        return {
            "presentation_id": req.presentation_id,
            "slide_no": req.slide_no,
            "html": changed,
            "change_summary": f"已按要求修改：{req.instruction}",
            "metadata": {"model_used": self.llm.available, "theme": req.theme},
        }

    async def modify_presentation(self, req: PresentationModifyRequest) -> dict[str, Any]:
        slides = [dict(slide) for slide in req.slides or [] if isinstance(slide, dict)]
        if not slides:
            return {
                "presentation_id": req.presentation_id,
                "title": req.title,
                "slide_count": 0,
                "slides": [],
                "html": "",
                "change_summary": "没有可修改的 slides",
                "operations": [],
                "metadata": {"model_used": False, "theme": req.theme},
            }

        plan = await self._deck_modify_plan(req, slides)
        slides = self._apply_delete_operations(slides, plan.get("operations", []))
        slides = self._apply_reorder_operations(slides, plan.get("operations", []))
        slides = await self._apply_add_operations(req, slides, plan.get("operations", []))
        slides = self._renumber_slide_results(slides)

        modify_ops = self._selected_modify_operations(req, slides, plan.get("operations", []))
        semaphore = asyncio.Semaphore(max(1, self.settings.max_slide_concurrency))
        modified_map: dict[int, dict[str, Any]] = {}

        async def modify_one(operation: dict[str, Any]) -> None:
            slide_no = int(operation.get("slide_no") or 0)
            if slide_no < 1 or slide_no > len(slides):
                return
            slide = slides[slide_no - 1]
            async with semaphore:
                result = await self.modify_slide(SlideModifyRequest(
                    presentation_id=req.presentation_id,
                    slide_no=slide_no,
                    current_html=str(slide.get("html") or ""),
                    instruction=str(operation.get("instruction") or req.instruction),
                    outline_context={
                        "deck_title": req.title,
                        "deck_instruction": req.instruction,
                        "outline": req.outline or {},
                        "operation": operation,
                        "all_slide_titles": [item.get("title") for item in slides],
                    },
                    theme=req.theme,
                    keep_style=req.keep_style,
                ))
                updated = dict(slide)
                updated["html"] = result.get("html") or slide.get("html") or ""
                updated["title"] = str(operation.get("title") or slide.get("title") or f"第 {slide_no} 页")
                updated["notes"] = slide.get("notes", "")
                metadata = dict(slide.get("metadata") or {})
                metadata.update({
                    "modified": True,
                    "deck_modify_instruction": req.instruction,
                    "deck_modify_operation": operation,
                })
                updated["metadata"] = metadata
                modified_map[slide_no] = updated

        await asyncio.gather(*(modify_one(operation) for operation in modify_ops))
        for slide_no, updated in modified_map.items():
            slides[slide_no - 1] = updated
        slides = self._renumber_slide_results(slides)
        title = str(plan.get("title") or req.title)
        return {
            "presentation_id": req.presentation_id or f"ppt_{uuid.uuid4().hex[:12]}",
            "title": title,
            "slide_count": len(slides),
            "slides": slides,
            "html": self._combine_deck(title, slides),
            "change_summary": str(plan.get("change_summary") or f"已按整套课件要求修改：{req.instruction}"),
            "operations": plan.get("operations", []),
            "modified_slide_nos": sorted(modified_map.keys()),
            "metadata": {
                "model_used": self.llm.available,
                "theme": req.theme,
                "keep_style": req.keep_style,
            },
        }

    async def _deck_modify_plan(self, req: PresentationModifyRequest, slides: list[dict[str, Any]]) -> dict[str, Any]:
        fallback = self._fallback_deck_modify_plan(req, slides)
        if not self.llm.available:
            return fallback
        slide_summary = [
            {
                "slide_no": index + 1,
                "title": slide.get("title"),
                "notes": slide.get("notes", ""),
                "metadata": slide.get("metadata", {}),
                "html_excerpt": str(slide.get("html") or "")[:1200],
            }
            for index, slide in enumerate(slides)
        ]
        prompt = f"""
请把用户对整套 PPT 的自然语言修改要求拆成可执行计划。只返回严格 JSON，不要 Markdown。

用户要求:
{req.instruction}

课件标题: {req.title}
主题: {req.theme or ""}
是否尽量保持原风格: {req.keep_style}
最多修改页数: {req.max_modified_slides or "不限"}

大纲:
{json.dumps(req.outline or {}, ensure_ascii=False, default=str)[:8000]}

当前页面摘要:
{json.dumps(slide_summary, ensure_ascii=False, default=str)[:16000]}

JSON 格式:
{{
  "title": "可选，修改后的课件标题",
  "change_summary": "整套修改摘要",
  "operations": [
    {{
      "type": "modify|add|delete|reorder",
      "slide_no": 1,
      "target_slide_no": 2,
      "after_slide_no": 3,
      "title": "页面标题",
      "instruction": "给单页 HTML 修改器或新增页生成器的具体要求",
      "slide_outline": {{
        "title": "",
        "slide_type": "content",
        "content_points": [],
        "teaching_intent": "",
        "visual_suggestion": ""
      }}
    }}
  ]
}}

规则:
1. 全局风格、统一字体、减少文字、整体更活泼等要求应生成多个 modify 操作。
2. “增加/补充一页”用 add，并给出 after_slide_no 和 slide_outline。
3. “删除第 N 页”用 delete。
4. “把第 A 页移到第 B 页前/后”用 reorder。
5. 不确定具体页时，优先修改所有页面，但不要超过最多修改页数。
""".strip()
        try:
            raw = await self.llm.complete("你是 PPT 课件迭代修改调度器，只输出可解析 JSON。", prompt, 0.2)
            data = json.loads(self._extract_json(raw))
            if isinstance(data, dict) and isinstance(data.get("operations"), list):
                return self._normalize_deck_plan(data, fallback, len(slides), req)
        except Exception:
            pass
        return fallback

    def _fallback_deck_modify_plan(self, req: PresentationModifyRequest, slides: list[dict[str, Any]]) -> dict[str, Any]:
        instruction = req.instruction or ""
        total = len(slides)
        operations: list[dict[str, Any]] = []
        delete_nos = {int(value) for value in re.findall(r"删除第\s*(\d{1,2})\s*页", instruction)}
        for slide_no in sorted(delete_nos):
            if 1 <= slide_no <= total:
                operations.append({"type": "delete", "slide_no": slide_no, "instruction": instruction})

        add_match = re.search(r"(?:增加|新增|补充).*?(?:一页|1页|页面|案例页|活动页|练习页|总结页|导入页|拓展页|页)", instruction)
        if add_match:
            after_match = re.search(r"(?:第\s*(\d{1,2})\s*页(?:后|之后)|放到第\s*(\d{1,2})\s*页后)", instruction)
            after_slide_no = int(next(group for group in after_match.groups() if group)) if after_match else total
            title_match = re.search(r"(?:案例|活动|练习|总结|导入|拓展)", instruction)
            title = title_match.group(0) if title_match else "补充内容"
            operations.append({
                "type": "add",
                "after_slide_no": max(0, min(total, after_slide_no)),
                "instruction": instruction,
                "slide_outline": {
                    "title": title,
                    "slide_type": "content",
                    "content_points": [instruction],
                    "teaching_intent": "根据用户迭代要求补充课件内容。",
                    "visual_suggestion": "保持整套课件主题风格，使用清晰层级展示补充内容。",
                },
            })

        target_nos = {int(value) for value in re.findall(r"第\s*(\d{1,2})\s*页", instruction)}
        target_nos = {slide_no for slide_no in target_nos if 1 <= slide_no <= total and slide_no not in delete_nos}
        global_keywords = ["全部", "所有", "整套", "整体", "统一", "每页", "全局", "风格", "字体", "配色", "减少文字", "精简"]
        if any(keyword in instruction for keyword in global_keywords) or not target_nos:
            target_nos = set(range(1, total + 1))
        if req.max_modified_slides:
            target_nos = set(sorted(target_nos)[:req.max_modified_slides])
        for slide_no in sorted(target_nos):
            operations.append({"type": "modify", "slide_no": slide_no, "instruction": instruction})
        return {
            "title": req.title,
            "change_summary": f"已生成整套课件迭代修改计划：{instruction}",
            "operations": operations,
        }

    def _normalize_deck_plan(self, data: dict[str, Any], fallback: dict[str, Any], total: int, req: PresentationModifyRequest) -> dict[str, Any]:
        operations: list[dict[str, Any]] = []
        for raw in data.get("operations") or []:
            if not isinstance(raw, dict):
                continue
            op_type = str(raw.get("type") or "modify").lower()
            if op_type not in {"modify", "add", "delete", "reorder"}:
                op_type = "modify"
            operation = dict(raw)
            operation["type"] = op_type
            if op_type in {"modify", "delete", "reorder"}:
                try:
                    operation["slide_no"] = int(operation.get("slide_no") or 0)
                except Exception:
                    continue
                if not 1 <= operation["slide_no"] <= total:
                    continue
            if op_type == "add":
                try:
                    operation["after_slide_no"] = max(0, min(total, int(operation.get("after_slide_no") or total)))
                except Exception:
                    operation["after_slide_no"] = total
                operation.setdefault("slide_outline", {"title": operation.get("title") or "补充内容", "content_points": [req.instruction]})
            operation.setdefault("instruction", req.instruction)
            operations.append(operation)
        if req.max_modified_slides:
            kept: list[dict[str, Any]] = []
            modified_count = 0
            for operation in operations:
                if operation.get("type") == "modify":
                    if modified_count >= req.max_modified_slides:
                        continue
                    modified_count += 1
                kept.append(operation)
            operations = kept
        return {
            "title": data.get("title") or fallback.get("title") or req.title,
            "change_summary": data.get("change_summary") or fallback.get("change_summary") or req.instruction,
            "operations": operations or fallback.get("operations", []),
        }

    def _apply_delete_operations(self, slides: list[dict[str, Any]], operations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        delete_nos = {int(op.get("slide_no")) for op in operations if op.get("type") == "delete" and str(op.get("slide_no", "")).isdigit()}
        if not delete_nos:
            return slides
        return [slide for index, slide in enumerate(slides, 1) if index not in delete_nos]

    def _apply_reorder_operations(self, slides: list[dict[str, Any]], operations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        ordered = list(slides)
        for operation in operations:
            if operation.get("type") != "reorder":
                continue
            try:
                slide_no = int(operation.get("slide_no") or 0)
                target = int(operation.get("target_slide_no") or operation.get("after_slide_no") or 0)
            except Exception:
                continue
            if not 1 <= slide_no <= len(ordered) or not 1 <= target <= len(ordered):
                continue
            slide = ordered.pop(slide_no - 1)
            insert_at = target - 1
            if operation.get("after_slide_no"):
                insert_at = target
            if slide_no < target:
                insert_at -= 1
            ordered.insert(max(0, min(len(ordered), insert_at)), slide)
        return ordered

    async def _apply_add_operations(self, req: PresentationModifyRequest, slides: list[dict[str, Any]], operations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result = list(slides)
        add_ops = [op for op in operations if op.get("type") == "add"]
        for operation in add_ops:
            outline = operation.get("slide_outline") if isinstance(operation.get("slide_outline"), dict) else {}
            slide_outline = {
                "title": str(outline.get("title") or operation.get("title") or "补充内容"),
                "slide_type": str(outline.get("slide_type") or "content"),
                "content_points": outline.get("content_points") or [operation.get("instruction") or req.instruction],
                "teaching_intent": str(outline.get("teaching_intent") or "补充用户要求的教学内容。"),
                "visual_suggestion": str(outline.get("visual_suggestion") or "保持整套课件视觉风格。"),
            }
            slide_no = max(1, min(len(result) + 1, int(operation.get("after_slide_no") or len(result)) + 1))
            html_markup = await self._generate_added_slide_html(req, slide_outline, slide_no, len(result) + 1)
            result.insert(slide_no - 1, {
                "slide_no": slide_no,
                "title": slide_outline["title"],
                "html": html_markup,
                "notes": self._speaker_notes(slide_outline),
                "metadata": {
                    "theme": req.theme,
                    "added_by_deck_modify": True,
                    "deck_modify_instruction": req.instruction,
                    "deck_modify_operation": operation,
                },
            })
        return result

    async def _generate_added_slide_html(self, req: PresentationModifyRequest, slide_outline: dict[str, Any], slide_no: int, total: int) -> str:
        if self.llm.available:
            prompt = f"""
请根据整套 PPT 迭代要求新增一页 HTML PPT，只返回完整 HTML。
必须保持 1280x720 固定画布、overflow:hidden、完整 <!DOCTYPE html> 结构。

课件标题: {req.title}
主题: {req.theme or DEFAULT_THEME}
整套修改要求: {req.instruction}
新增页页码: {slide_no}/{total}
新增页大纲:
{json.dumps(slide_outline, ensure_ascii=False, default=str)}
整套大纲:
{json.dumps(req.outline or {}, ensure_ascii=False, default=str)[:8000]}
""".strip()
            html_markup = await self._complete_html_with_retry(prompt, self._html_system_prompt(), slide_outline, slide_no, total)
            if html_markup:
                return html_markup
        return self._fallback_slide_html(req.title, slide_outline, slide_no, total, req.theme or DEFAULT_THEME)

    def _selected_modify_operations(self, req: PresentationModifyRequest, slides: list[dict[str, Any]], operations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        modify_ops = [op for op in operations if op.get("type") == "modify"]
        if not modify_ops:
            modify_ops = self._fallback_deck_modify_plan(req, slides).get("operations", [])
            modify_ops = [op for op in modify_ops if op.get("type") == "modify"]
        seen: set[int] = set()
        selected: list[dict[str, Any]] = []
        for operation in modify_ops:
            try:
                slide_no = int(operation.get("slide_no") or 0)
            except Exception:
                continue
            if 1 <= slide_no <= len(slides) and slide_no not in seen:
                seen.add(slide_no)
                selected.append(operation)
        return selected

    def _renumber_slide_results(self, slides: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result = []
        total = len(slides)
        for index, slide in enumerate(slides, 1):
            item = dict(slide)
            item["slide_no"] = index
            item.setdefault("title", f"第 {index} 页")
            metadata = dict(item.get("metadata") or {})
            metadata["deck_slide_count"] = total
            item["metadata"] = metadata
            result.append(item)
        return result

    async def _build_quality_assets(
        self,
        title: str,
        theme: str,
        template_name: str,
        template_html: str,
        request_context: dict[str, Any],
        slides: list[dict[str, Any]],
    ) -> dict[str, Any]:
        fallback = self._fast_quality_assets(template_name, theme, slides)
        if not (self.llm.available and self.settings.enable_quality_pipeline):
            return fallback

        preset = self.settings.quality_preset
        if preset == "fast":
            return fallback

        if preset == "balanced":
            prompt = f"""
请一次性完成设计规划，输出严格 JSON，不要 Markdown。
字段：
- style_genes: 模板风格基因
- global_constitution: 整套 PPT 全局视觉规则
- page_briefs: 对象，key 为页码字符串，value 为每页创意 brief

必须严格使用主题：{theme}
模板名称：{template_name}
页面数量：{len(slides)}
页面大纲：
{json.dumps(slides, ensure_ascii=False)}
项目信息：
{json.dumps(request_context, ensure_ascii=False)}
模板 HTML：
{template_html[:12000]}
""".strip()
            try:
                raw = await self.llm.complete("你是资深视觉总监，只输出 JSON。", prompt, 0.35)
                data = json.loads(self._extract_json(raw))
                return self._normalize_quality_assets(data, fallback)
            except Exception:
                return fallback

        try:
            style_genes = await self.llm.complete("你是模板分析专家。", style_gene_prompt(template_name, template_html), 0.25)
            constitution = await self.llm.complete(
                "你是视觉总监。",
                global_constitution_prompt(title, theme, request_context, style_genes, slides),
                0.3,
            )
            briefs_raw = await self.llm.complete(
                "你是页面创意总监，只输出 JSON。",
                page_briefs_prompt(title, theme, request_context, style_genes, constitution, slides),
                0.35,
            )
            briefs = json.loads(self._extract_json(briefs_raw))
            return self._normalize_quality_assets({
                "style_genes": style_genes,
                "global_constitution": constitution,
                "page_briefs": briefs,
            }, fallback)
        except Exception:
            return fallback

    def _fast_quality_assets(self, template_name: str, theme: str, slides: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "style_genes": f"继承 {template_name} 模板的配色、标题锚点、页脚锚点、组件质感与装饰语言。主题风格：{theme}。",
            "global_constitution": f"全套页面必须固定 1280x720，严格保持 {theme}，不得混入其他模板风格；文字不溢出，页面不滚动。",
            "page_briefs": {str(i): self._fallback_page_brief(slide, i, len(slides)) for i, slide in enumerate(slides, 1)},
        }

    def _normalize_quality_assets(self, data: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(data, dict):
            return fallback
        page_briefs = data.get("page_briefs") if isinstance(data.get("page_briefs"), dict) else fallback["page_briefs"]
        return {
            "style_genes": str(data.get("style_genes") or fallback["style_genes"]),
            "global_constitution": str(data.get("global_constitution") or fallback["global_constitution"]),
            "page_briefs": {str(k): str(v) for k, v in page_briefs.items()},
        }

    async def _generate_slide_html(
        self,
        title: str,
        slide: dict[str, Any],
        slide_no: int,
        total: int,
        theme: str,
        template_name: str,
        template_html: str,
        request_context: dict[str, Any],
        all_slides: list[dict[str, Any]],
        quality_assets: dict[str, Any],
    ) -> str:
        if self.llm.available and self.settings.enable_quality_pipeline:
            prompt = slide_html_prompt(
                title=title,
                theme=theme,
                request_context=request_context,
                template_name=template_name,
                template_html=template_html,
                style_genes=quality_assets.get("style_genes", ""),
                global_constitution=quality_assets.get("global_constitution", ""),
                page_brief=quality_assets.get("page_briefs", {}).get(str(slide_no), ""),
                slide=slide,
                slide_no=slide_no,
                total=total,
                all_slides=all_slides,
            )
            slide_markup = await self._complete_html_with_retry(prompt, self._html_system_prompt(), slide, slide_no, total)
            if slide_markup:
                return slide_markup
        return self._fallback_slide_html(title, slide, slide_no, total, theme)

    async def _complete_html_with_retry(self, prompt: str, system_prompt: str, slide: dict[str, Any], slide_no: int, total: int) -> str:
        current_prompt = prompt
        last_html = ""
        for attempt in range(max(1, self.settings.max_html_retries)):
            try:
                raw = await self.llm.complete(system_prompt, current_prompt, 0.5 if attempt == 0 else 0.25)
            except Exception:
                continue
            slide_markup = auto_close_basic_tags(clean_html_response(raw))
            validation = validate_html(slide_markup, strict=True)
            if validation["valid"]:
                return slide_markup
            last_html = slide_markup
            if self.settings.quality_preset == "fast":
                break
            current_prompt = repair_html_prompt(prompt, slide_markup, validation["errors"], validation["warnings"])
        return last_html if last_html and validate_html(last_html)["valid"] else ""

    async def _generate_outline_with_model(self, req: OutlineGenerateRequest, slide_count: int) -> dict[str, Any]:
        prompt = self._outline_prompt(req, slide_count)
        try:
            raw = await self.llm.complete("你是资深教学设计专家，只输出可解析 JSON。", prompt, 0.25)
            data = json.loads(self._extract_json(raw))
            if isinstance(data, dict) and data.get("slides"):
                return self._normalize_outline(data, req.title)
        except Exception:
            pass
        return self._fallback_outline(req, slide_count)

    def _outline_prompt(self, req: OutlineGenerateRequest, slide_count: int) -> str:
        return f"""
Generate a teaching PPT outline. Return strict JSON only, no Markdown.

Required top-level fields:
- title
- summary
- teaching_design_chain
- slides
- interactive_assets
- diagram_assets

teaching_design_chain is for frontend display and must not replace slides. It must contain:
- teaching_goals: list[str]
- learner_analysis: string
- key_points: list[str]
- difficult_points: list[str]
- teaching_sequence: list[str]
- activity_design: list[str]
- assessment_design: list[str]
- homework: list[str]

slides must contain about {slide_count} pages and include cover, agenda, content pages, activity or practice page, and summary page.
Each slide must contain: slide_no, title, slide_type, content_points(list), teaching_intent, visual_suggestion, interactive_asset_ids(list), external_resource_notes.
interactive_assets items must contain: asset_id, title, type(animation|game|simulation), target_slide_no, preferred_format(html5|gif|mp4), integration(ppt_video|static_link), description.
If diagram context is provided, add diagram_assets items with asset_id, title, type, format, mermaid, usage.

Course title: {req.title}
Subject: {req.subject}
Grade: {req.grade}
Duration minutes: {req.duration_minutes or ""}
Expected slide count: {slide_count}
Teaching goals: {req.teaching_goals or ""}
Knowledge points: {", ".join(req.knowledge_points)}
Extra requirements: {req.requirements or ""}
Web enabled: {req.enable_web}
RAG enabled: {req.enable_rag}
Regenerate instruction: {req.regenerate_instruction or ""}
Interactive policy: {json.dumps(req.interactive_policy or {}, ensure_ascii=False)}
Reference material and RAG context:
{(req.reference_text or "")[:12000]}
""".strip()

    def _skip_string(self, text: str, i: int) -> int:
        """跳过位于 i 处（引号字符）之后的字符串字面量，返回字符串结束后的下一个下标。"""
        n = len(text)
        i += 1
        while i < n:
            if text[i] == "\\":
                i += 2
                continue
            if text[i] == '"':
                return i + 1
            i += 1
        return n

    def _object_end(self, text: str, start: int) -> int | None:
        """从 start（指向 '{'）开始找配对闭合的 '}'，返回其后的下标；对象未闭合返回 None。"""
        n = len(text)
        depth = 0
        i = start
        while i < n:
            ch = text[i]
            if ch == '"':
                i = self._skip_string(text, i)
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return i + 1
            i += 1
        return None

    def _extract_completed_slides(self, text: str, array_start: int, scan_from: int) -> tuple[list[dict[str, Any]], int]:
        """在 slides 数组区域内增量扫描，提取已完整闭合的 slide 对象。

        返回 (slides, new_scan_pos)：new_scan_pos 供下次从该位置继续扫描，避免重复解析。
        遇未闭合对象/结束数组则停止（保留新位置，等待更多 token 或进入结束阶段）。
        """
        results: list[dict[str, Any]] = []
        i = max(array_start, scan_from)
        n = len(text)
        while i < n:
            ch = text[i]
            if ch == '"':
                i = self._skip_string(text, i)
                continue
            if ch == "{":
                end = self._object_end(text, i)
                if end is None:
                    break
                raw = text[i:end]
                i = end
                try:
                    obj = json.loads(raw)
                except Exception:
                    break
                if isinstance(obj, dict):
                    results.append(obj)
                continue
            if ch == "}":
                # 到达某处多余的闭合（通常数组已结束但外层未闭合），无需处理
                i += 1
                continue
            if ch == "]":
                i += 1
                continue
            i += 1
        return results, i

    async def _with_reference_and_rag_context(self, req: OutlineGenerateRequest) -> OutlineGenerateRequest:
        context_parts = []
        if req.reference_text:
            context_parts.append(req.reference_text)

        # Uploaded resources are reference material. They enrich style, tone, cases,
        # and the RAG query, but they are not the vector-store search scope.
        if req.resource_ids:
            local_ids = [resource_id for resource_id in req.resource_ids if ":" not in resource_id]
            reference_context = build_rag_context(local_ids, limit=5000)
            if reference_context:
                context_parts.append("[Uploaded reference material]\n" + reference_context)

        if req.enable_rag:
            from ..tools.rag import rag_search
            query = "\n".join([
                req.title,
                req.subject,
                req.grade,
                req.teaching_goals or "",
                " ".join(req.knowledge_points or []),
                req.requirements or "",
                req.reference_text or "",
            ]).strip()
            rag_result = await rag_search(req.resource_ids, query)
            if rag_result.get("knowledge_context"):
                context_parts.append("[RAG knowledge base matches]\n" + rag_result["knowledge_context"])

        if not context_parts:
            return req
        data = req.model_dump()
        data["reference_text"] = "\n\n".join(part for part in context_parts if part.strip())[:16000]
        return OutlineGenerateRequest(**data)

    def _html_system_prompt(self) -> str:
        return "你是资深演示文稿视觉设计师和前端工程师。只输出完整、可独立渲染、视觉完成度高的 1280x720 HTML PPT 页面。"

    def _slide_modify_prompt(self, req: SlideModifyRequest) -> str:
        return f"""
请按修改要求更新下面这页 PPT HTML，并只返回完整 HTML。
必须保持 1280x720 固定画布、overflow:hidden、完整 <!DOCTYPE html> 文档结构。

页码：{req.slide_no}
修改要求：{req.instruction}
主题：{req.theme or "沿用原主题"}
是否保持风格：{req.keep_style}
上下文：{json.dumps(req.outline_context or {}, ensure_ascii=False)}

当前 HTML：
{req.current_html[:18000]}
""".strip()

    def _request_context(self, req: PresentationGenerateRequest) -> dict[str, Any]:
        outline = req.outline if isinstance(req.outline, dict) else {}
        return {
            "subject": outline.get("subject"),
            "grade": outline.get("grade"),
            "requirements": outline.get("requirements"),
            "description": outline.get("summary"),
            "language": req.language,
        }

    def _fallback_page_brief(self, slide: dict[str, Any], slide_no: int, total: int) -> str:
        title = str(slide.get("title") or f"第 {slide_no} 页")
        if slide_no == 1:
            return f"封面页。以“{title}”作为视觉中心，使用大标题、关键词和沉浸背景建立第一印象。"
        if slide_no == total:
            return f"总结页。围绕“{title}”做收束，使用结论墙或关键收获卡片。"
        return f"内容页。围绕“{title}”建立一个视觉焦点，用卡片、编号、流程或对比关系组织内容。"

    def _normalize_slides_for_deck(self, slides: list[dict[str, Any]]) -> list[dict[str, Any]]:
        total = len(slides)
        normalized: list[dict[str, Any]] = []
        for idx, slide in enumerate(slides, 1):
            item = dict(slide)
            item["slide_no"] = idx
            item.setdefault("title", f"第 {idx} 页")
            item.setdefault("content_points", item.get("points") or [])
            item.setdefault("slide_type", "cover" if idx == 1 else ("summary" if idx == total else "content"))
            normalized.append(item)
        return normalized

    def _fallback_outline(self, req: OutlineGenerateRequest, slide_count: int) -> dict[str, Any]:
        points = req.knowledge_points or self._split_points(req.teaching_goals or req.requirements or req.title)
        titles = ["课程导入", "学习目标", *points, "课堂活动", "知识总结", "课后拓展"]
        slides = []
        for idx in range(slide_count):
            base = titles[idx] if idx < len(titles) else f"重点解析 {idx}"
            slides.append({
                "slide_no": idx + 1,
                "slide_type": "cover" if idx == 0 else ("summary" if idx == slide_count - 1 else "content"),
                "title": req.title if idx == 0 else base,
                "content_points": [f"明确{base}的核心概念", "结合案例建立理解", "通过提问或活动完成课堂迁移"],
                "teaching_intent": "帮助学生建立清晰认知并完成课堂迁移。",
                "visual_suggestion": "使用层级卡片、流程线或重点数字强化理解。",
            })
        interactive_assets = self._fallback_interactive_assets(req, slide_count)
        for asset in interactive_assets:
            target = int(asset.get("target_slide_no") or 0)
            if 1 <= target <= len(slides):
                slide = slides[target - 1]
                slide.setdefault("interactive_asset_ids", []).append(asset["asset_id"])
                slide["external_resource_notes"] = asset["description"]
        return {
            "title": req.title,
            "summary": f"围绕 {req.subject} {req.grade}《{req.title}》组织的教学 PPT。",
            "slides": slides,
            "interactive_assets": interactive_assets,
        }

    def _fallback_outline_from_title(self, title: str, slide_count: int) -> list[dict[str, Any]]:
        return self._fallback_outline(OutlineGenerateRequest(title=title, subject="通用", grade="通用", slide_count=slide_count), slide_count)["slides"]

    def _ensure_interactive_assets(self, outline: dict[str, Any], req: OutlineGenerateRequest, slide_count: int) -> dict[str, Any]:
        if not (req.interactive_policy or {}).get("needs_interactive_assets"):
            return outline
        existing = self._normalize_interactive_assets(outline.get("interactive_assets") or [])
        if existing:
            outline["interactive_assets"] = existing
            return outline
        assets = self._fallback_interactive_assets(req, slide_count)
        slides = outline.get("slides") or []
        for asset in assets:
            target = int(asset.get("target_slide_no") or 0)
            if 1 <= target <= len(slides) and isinstance(slides[target - 1], dict):
                slide = slides[target - 1]
                slide.setdefault("interactive_asset_ids", []).append(asset["asset_id"])
                slide["external_resource_notes"] = asset["description"]
        outline["interactive_assets"] = assets
        return outline

    def _finalize_existing_outline(self, outline: dict[str, Any]) -> dict[str, Any]:
        slides = [slide for slide in outline.get("slides") or [] if isinstance(slide, dict)]
        options = outline.get("generation_options") if isinstance(outline.get("generation_options"), dict) else {}
        req = OutlineGenerateRequest(
            title=str(outline.get("title") or "Untitled outline"),
            subject=str(outline.get("subject") or "General"),
            grade=str(outline.get("grade") or "General"),
            teaching_goals="; ".join(self._as_list((outline.get("teaching_design_chain") or {}).get("teaching_goals"))) if isinstance(outline.get("teaching_design_chain"), dict) else None,
            knowledge_points=self._as_list((outline.get("teaching_design_chain") or {}).get("key_points")) if isinstance(outline.get("teaching_design_chain"), dict) else [],
            requirements=str(outline.get("requirements") or "") or None,
            resource_ids=list(options.get("resource_ids") or []),
            enable_web=bool(options.get("enable_web")),
            enable_rag=bool(options.get("enable_rag")),
            slide_count=max(1, len(slides) or 8),
            interactive_policy=dict(options.get("interactive_policy") or {}),
        )
        outline = self._ensure_teaching_design_chain(outline, req)
        return self._ensure_outline_quality(outline, req, req.slide_count or 8)

    def _ensure_teaching_design_chain(self, outline: dict[str, Any], req: OutlineGenerateRequest) -> dict[str, Any]:
        chain = outline.get("teaching_design_chain")
        if not isinstance(chain, dict):
            chain = {}
        fallback = self._fallback_teaching_design_chain(req, outline)
        normalized = {
            "teaching_goals": self._as_list(chain.get("teaching_goals")) or fallback["teaching_goals"],
            "learner_analysis": str(chain.get("learner_analysis") or fallback["learner_analysis"]),
            "key_points": self._as_list(chain.get("key_points")) or fallback["key_points"],
            "difficult_points": self._as_list(chain.get("difficult_points")) or fallback["difficult_points"],
            "teaching_sequence": self._as_list(chain.get("teaching_sequence")) or fallback["teaching_sequence"],
            "activity_design": self._as_list(chain.get("activity_design")) or fallback["activity_design"],
            "assessment_design": self._as_list(chain.get("assessment_design")) or fallback["assessment_design"],
            "homework": self._as_list(chain.get("homework")) or fallback["homework"],
        }
        outline["teaching_design_chain"] = normalized
        return outline

    def _fallback_teaching_design_chain(self, req: OutlineGenerateRequest, outline: dict[str, Any]) -> dict[str, Any]:
        knowledge_points = req.knowledge_points or self._slide_titles(outline) or self._split_points(req.teaching_goals or req.requirements or req.title)
        goals = self._split_points(req.teaching_goals or "") if req.teaching_goals else [
            f"Understand the core concepts of {req.title}.",
            f"Explain key ideas using examples from {req.subject}.",
            "Apply the knowledge through classroom activity or practice.",
        ]
        return {
            "teaching_goals": goals,
            "learner_analysis": f"Learners are {req.grade} students. The outline should connect prior experience with {req.title} and reduce abstract cognitive load.",
            "key_points": knowledge_points[:6],
            "difficult_points": (knowledge_points[:2] or [req.title]),
            "teaching_sequence": [
                "Create a problem situation and activate prior knowledge.",
                "Clarify learning goals and the lesson structure.",
                "Explain core concepts from easy to difficult.",
                "Use examples, visual prompts, and interaction to consolidate understanding.",
                "Summarize key takeaways and assign transfer practice.",
            ],
            "activity_design": [
                "Use questioning or a mini task before the main explanation.",
                "Arrange one classroom interaction around the key difficult point.",
            ],
            "assessment_design": [
                "Check understanding through quick questions during the lesson.",
                "Use a short exit ticket or practice task after the summary.",
            ],
            "homework": [
                f"Review the core concepts of {req.title}.",
                "Complete one application or reflection task based on the lesson.",
            ],
        }

    def _ensure_outline_quality(self, outline: dict[str, Any], req: OutlineGenerateRequest, slide_count: int) -> dict[str, Any]:
        slides = [slide for slide in outline.get("slides") or [] if isinstance(slide, dict)]
        if not slides:
            slides = self._fallback_outline(req, slide_count)["slides"]

        slides = [dict(slide) for slide in slides]
        if slides:
            slides[0]["slide_type"] = "cover"
            slides[0]["title"] = str(slides[0].get("title") or req.title)
        if slide_count >= 4:
            has_agenda = any(str(slide.get("slide_type") or "").lower() in {"agenda", "toc", "directory"} for slide in slides)
            if not has_agenda:
                agenda_slide = {
                    "slide_no": 2,
                    "slide_type": "agenda",
                    "title": "Learning Agenda",
                    "content_points": self._agenda_points(outline, req),
                    "teaching_intent": "Help learners establish the lesson path before detailed explanation.",
                    "visual_suggestion": "Use a numbered roadmap or process line.",
                    "interactive_asset_ids": [],
                    "external_resource_notes": "",
                }
                if len(slides) < slide_count:
                    slides.insert(1, agenda_slide)
                elif len(slides) >= 2:
                    slides[1] = {**agenda_slide, **{k: v for k, v in slides[1].items() if k not in {"slide_type"}}}
                    slides[1]["slide_type"] = "agenda"
        if slides:
            slides[-1]["slide_type"] = "summary"
            if not slides[-1].get("title"):
                slides[-1]["title"] = "Summary and Extension"

        normalized = []
        for index, slide in enumerate(slides[:slide_count], 1):
            item = dict(slide)
            item["slide_no"] = index
            item["slide_type"] = str(item.get("slide_type") or ("cover" if index == 1 else ("summary" if index == len(slides) else "content")))
            item["title"] = str(item.get("title") or f"Slide {index}")
            item["content_points"] = self._as_list(item.get("content_points") or item.get("points")) or [item["title"]]
            item["teaching_intent"] = str(item.get("teaching_intent") or self._default_teaching_intent(item, index))
            item["visual_suggestion"] = str(item.get("visual_suggestion") or "Use clear hierarchy, visual grouping, and concise classroom prompts.")
            item["interactive_asset_ids"] = list(item.get("interactive_asset_ids") or [])
            item["external_resource_notes"] = str(item.get("external_resource_notes") or "")
            normalized.append(item)
        outline["slides"] = normalized
        outline["quality_report"] = self._outline_quality_report(outline, req, slide_count)
        return outline

    def _outline_quality_report(self, outline: dict[str, Any], req: OutlineGenerateRequest, expected_count: int) -> dict[str, Any]:
        slides = outline.get("slides") or []
        slide_types = {str(slide.get("slide_type") or "").lower() for slide in slides if isinstance(slide, dict)}
        knowledge_points = req.knowledge_points or []
        covered_text = json.dumps(slides, ensure_ascii=False)
        missing_knowledge_points = [point for point in knowledge_points if point and point not in covered_text]
        checks = {
            "has_teaching_design_chain": isinstance(outline.get("teaching_design_chain"), dict),
            "has_cover": "cover" in slide_types,
            "has_agenda": bool(slide_types & {"agenda", "toc", "directory"}),
            "has_summary": "summary" in slide_types,
            "slide_count_close": abs(len(slides) - expected_count) <= 1,
            "all_slides_have_teaching_intent": all(bool(slide.get("teaching_intent")) for slide in slides if isinstance(slide, dict)),
            "all_slides_have_visual_suggestion": all(bool(slide.get("visual_suggestion")) for slide in slides if isinstance(slide, dict)),
            "knowledge_points_covered": not missing_knowledge_points,
        }
        return {
            "passed": all(checks.values()),
            "checks": checks,
            "expected_slide_count": expected_count,
            "actual_slide_count": len(slides),
            "missing_knowledge_points": missing_knowledge_points,
        }

    def _agenda_points(self, outline: dict[str, Any], req: OutlineGenerateRequest) -> list[str]:
        chain = outline.get("teaching_design_chain") or {}
        sequence = self._as_list(chain.get("teaching_sequence"))
        if sequence:
            return sequence[:5]
        points = req.knowledge_points or self._slide_titles(outline)
        return points[:5] or ["Learning goals", "Core concepts", "Classroom activity", "Summary"]

    def _slide_titles(self, outline: dict[str, Any]) -> list[str]:
        return [str(slide.get("title")) for slide in outline.get("slides") or [] if isinstance(slide, dict) and slide.get("title")]

    def _default_teaching_intent(self, slide: dict[str, Any], index: int) -> str:
        slide_type = str(slide.get("slide_type") or "").lower()
        if slide_type == "cover":
            return "Introduce the topic and create an initial learning expectation."
        if slide_type in {"agenda", "toc", "directory"}:
            return "Clarify the lesson structure and learning path."
        if slide_type == "summary":
            return "Consolidate key conclusions and guide transfer after class."
        return "Support understanding of this knowledge point through explanation, examples, and guided interaction."

    def _as_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, tuple):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return self._split_points(value)
        return [str(value).strip()] if str(value).strip() else []

    def _normalize_outline(self, data: dict[str, Any], title: str) -> dict[str, Any]:
        slides = []
        for idx, item in enumerate(data.get("slides") or []):
            if isinstance(item, dict):
                slides.append({
                    "slide_no": idx + 1,
                    "slide_type": str(item.get("slide_type") or item.get("type") or ("cover" if idx == 0 else "content")),
                    "title": str(item.get("title") or f"第 {idx + 1} 页"),
                    "content_points": item.get("content_points") or item.get("points") or [],
                    "teaching_intent": str(item.get("teaching_intent") or ""),
                    "visual_suggestion": str(item.get("visual_suggestion") or ""),
                    "interactive_asset_ids": list(item.get("interactive_asset_ids") or []),
                    "external_resource_notes": str(item.get("external_resource_notes") or ""),
                })
        data["title"] = data.get("title") or title
        data["slides"] = slides
        data["interactive_assets"] = self._normalize_interactive_assets(data.get("interactive_assets") or [])
        return data

    def _outline_response(self, outline: dict[str, Any]) -> dict[str, Any]:
        slides = outline.get("slides", [])
        return {
            "outline_id": f"outline_{uuid.uuid4().hex[:12]}",
            "title": outline.get("title", "未命名大纲"),
            "summary": outline.get("summary", ""),
            "slide_count": len(slides),
            "outline": outline,
            "slides": slides,
            "interactive_assets": outline.get("interactive_assets", []),
            "diagram_assets": outline.get("diagram_assets", []),
            "teaching_design_chain": outline.get("teaching_design_chain", {}),
            "quality_report": outline.get("quality_report", {}),
        }

    def _normalize_interactive_assets(self, assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for index, raw in enumerate(assets or [], 1):
            if not isinstance(raw, dict):
                continue
            asset_type = str(raw.get("type") or raw.get("module_type") or "animation").lower()
            if asset_type in {"quiz_game", "matching_game", "timeline_game"}:
                asset_type = "game"
            if asset_type not in {"animation", "game", "simulation"}:
                asset_type = "animation"
            preferred_format = str(raw.get("preferred_format") or raw.get("format") or "html5").lower()
            if preferred_format not in {"html5", "gif", "mp4"}:
                preferred_format = "html5"
            integration = str(raw.get("integration") or ("ppt_video" if preferred_format == "mp4" else "static_link"))
            try:
                target_slide_no = int(raw.get("target_slide_no") or raw.get("slide_no") or index + 1)
            except Exception:
                target_slide_no = index + 1
            asset_id = str(raw.get("asset_id") or raw.get("module_id") or f"interactive_{index}")
            asset_id = re.sub(r"[^a-zA-Z0-9_-]", "_", asset_id).strip("_") or f"interactive_{index}"
            normalized.append({
                **raw,
                "asset_id": asset_id,
                "title": str(raw.get("title") or ("课堂动画" if asset_type == "animation" else "课堂小游戏")),
                "type": asset_type,
                "target_slide_no": max(1, target_slide_no),
                "preferred_format": preferred_format,
                "integration": integration,
                "description": str(raw.get("description") or raw.get("usage") or "用于课堂演示或互动练习的补充资源。"),
            })
        return normalized

    def _fallback_interactive_assets(self, req: OutlineGenerateRequest, slide_count: int) -> list[dict[str, Any]]:
        policy = req.interactive_policy or {}
        if not policy.get("needs_interactive_assets"):
            return []
        formats = list(policy.get("preferred_formats") or ["html5"])
        preferred_format = str(formats[0] if formats else "html5")
        assets: list[dict[str, Any]] = []
        if policy.get("needs_animation"):
            target = 3 if slide_count >= 3 else max(1, slide_count)
            assets.append({
                "asset_id": "animation_1",
                "title": f"{req.title} process animation",
                "type": "animation",
                "target_slide_no": target,
                "preferred_format": preferred_format if preferred_format in {"html5", "gif", "mp4"} else "html5",
                "integration": "ppt_video" if preferred_format == "mp4" else "static_link",
                "description": "Use this resource to demonstrate the key process dynamically; include a text note and a package-relative link in the PPT when it is not an mp4 video.",
            })
        if policy.get("needs_game"):
            target = min(max(2, slide_count - 2), slide_count)
            assets.append({
                "asset_id": "game_1",
                "title": f"{req.title} classroom mini game",
                "type": "game",
                "target_slide_no": target,
                "preferred_format": preferred_format if preferred_format in {"html5", "gif", "mp4"} else "html5",
                "integration": "ppt_video" if preferred_format == "mp4" else "static_link",
                "description": "Use this resource as a playable classroom activity; package it under static/ and reference it from the PPT.",
            })
        return self._normalize_interactive_assets(assets)

    async def _materialize_interactive_assets(
        self,
        req: PresentationGenerateRequest,
        slides: list[dict[str, Any]],
        assets: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        html_assets = [asset for asset in assets if asset.get("preferred_format") == "html5" and not asset.get("html")]
        if not html_assets:
            return assets
        from ..interactive import InteractiveModuleGenerator

        module_generator = InteractiveModuleGenerator()
        materialized = [dict(asset) for asset in assets]
        for asset in materialized:
            if asset.get("preferred_format") != "html5" or asset.get("html"):
                continue
            target_idx = max(0, min(len(slides) - 1, int(asset.get("target_slide_no") or 1) - 1)) if slides else 0
            target_slide = slides[target_idx] if slides else {}
            module_type = "animation"
            if asset.get("type") == "game":
                module_type = "quiz_game"
            elif asset.get("type") == "simulation":
                module_type = "simulation"
            result = await module_generator.generate(InteractiveModuleGenerateRequest(
                title=str(asset.get("title") or target_slide.get("title") or req.title),
                topic=str(target_slide.get("title") or req.title),
                module_type=module_type,
                subject=str((req.outline or {}).get("subject") or "") or None,
                grade=str((req.outline or {}).get("grade") or "") or None,
                knowledge_points=list(target_slide.get("content_points") or []),
                requirements=str(asset.get("description") or (req.outline or {}).get("requirements") or ""),
                theme=req.theme,
                embed_mode="standalone",
                language=req.language,
            ))
            asset["html"] = result.get("html") or ""
            asset["module_id"] = result.get("module_id")
            asset["usage_suggestions"] = result.get("usage_suggestions", [])
        return materialized

    def _attach_interactive_assets(self, slides: list[dict[str, Any]], assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_slide: dict[int, list[dict[str, Any]]] = {}
        for asset in assets:
            by_slide.setdefault(int(asset.get("target_slide_no") or 1), []).append(asset)
        attached: list[dict[str, Any]] = []
        for index, slide in enumerate(slides, 1):
            item = dict(slide)
            slide_assets = by_slide.get(index, [])
            if slide_assets:
                ids = list(item.get("interactive_asset_ids") or [])
                for asset in slide_assets:
                    if asset["asset_id"] not in ids:
                        ids.append(asset["asset_id"])
                item["interactive_asset_ids"] = ids
                item["interactive_assets"] = slide_assets
                notes = [str(asset.get("description") or "") for asset in slide_assets if asset.get("description")]
                if notes:
                    item["external_resource_notes"] = "\n".join(notes)
            attached.append(item)
        return attached

    def _extract_slides(self, outline: dict[str, Any]) -> list[dict[str, Any]]:
        if not isinstance(outline, dict):
            return []
        candidates = outline.get("slides")
        if not candidates and isinstance(outline.get("outline"), dict):
            candidates = outline["outline"].get("slides")
        return [slide for slide in candidates or [] if isinstance(slide, dict)]

    def _fallback_slide_html(self, deck_title: str, slide: dict[str, Any], slide_no: int, total: int, theme: str) -> str:
        title = html.escape(str(slide.get("title") or f"第 {slide_no} 页"))
        points = slide.get("content_points") or slide.get("points") or []
        if isinstance(points, str):
            points = self._split_points(points)
        palette = self._palette(theme)
        cards = "".join(f"<article><b>{i:02d}</b><p>{html.escape(str(point))}</p></article>" for i, point in enumerate(points[:5], 1))
        if slide_no == 1:
            main = f'<div class="cover"><div class="kicker">{html.escape(deck_title)}</div><h1>{title}</h1><p>{html.escape(str(points[0])) if points else "A12 智能备课生成"}</p></div>'
        else:
            side_text = html.escape(str(slide.get("teaching_intent") or slide.get("visual_suggestion") or "围绕本页主题组织课堂讲解。"))
            if slide.get("external_resource_notes"):
                side_text = f"{side_text}<br><br><b>互动资源</b><br>{html.escape(str(slide.get('external_resource_notes') or ''))}"
            main = f'<header><div><div class="kicker">{html.escape(deck_title)}</div><h1>{title}</h1></div><div class="count">{slide_no:02d} / {total:02d}</div></header><main><section>{cards or "<p>围绕本页主题展开核心内容。</p>"}</section><aside>{side_text}</aside></main><footer><span>A12 智能备课</span><span>{html.escape(theme)}</span></footer>'
        style = """*{box-sizing:border-box}
html,body{margin:0;width:100%;height:100%;background:#111827;font-family:"Microsoft YaHei",Arial,sans-serif}
body{display:flex;align-items:center;justify-content:center;overflow:hidden}
.slide{width:1280px;height:720px;position:relative;overflow:hidden;color:__TEXT__;background:__BG__;padding:56px 68px}
.slide:before{content:"";position:absolute;inset:0;background:__TEXTURE__}
.slide>*{position:relative;z-index:2}
.cover{width:760px;margin-top:120px}
.kicker{color:__ACCENT__;font-weight:800;letter-spacing:0}
h1{font-size:__TITLE_SIZE__;line-height:1.08;margin:14px 0 28px}
p{font-size:24px;line-height:1.45;color:__MUTED__}
header,footer{display:flex;justify-content:space-between;align-items:center}
main{height:470px;margin-top:34px;display:grid;grid-template-columns:1fr 1fr;gap:24px}
article{display:grid;grid-template-columns:58px 1fr;gap:16px;align-items:center;background:__CARD__;border-left:4px solid __ACCENT__;padding:18px;margin-bottom:14px;border-radius:__RADIUS__}
b{color:__ACCENT__;font-size:24px}
aside{background:__PANEL__;border:1px solid __LINE__;padding:28px;font-size:22px;line-height:1.55;color:__MUTED__;border-radius:__RADIUS__}"""
        for key, value in {
            "__TEXT__": palette["text"],
            "__BG__": palette["bg"],
            "__TEXTURE__": palette["texture"],
            "__ACCENT__": palette["accent"],
            "__TITLE_SIZE__": "72px" if slide_no == 1 else "42px",
            "__MUTED__": palette["muted"],
            "__CARD__": palette["card"],
            "__RADIUS__": palette["radius"],
            "__PANEL__": palette["panel"],
            "__LINE__": palette["line"],
        }.items():
            style = style.replace(key, value)
        return f'<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>{title}</title><style>{style}</style></head><body><section class="slide">{main}</section></body></html>'

    def _fallback_modify(self, current_html: str, instruction: str) -> str:
        marker = f'<div style="position:absolute;right:34px;bottom:34px;padding:10px 14px;background:rgba(0,0,0,.45);color:#fff;font-size:14px;border-radius:6px;z-index:999;">已修改：{html.escape(instruction)}</div>'
        return current_html.replace("</section></body>", marker + "</section></body>") if "</body>" in current_html else current_html

    def _combine_deck(self, title: str, slides: list[dict[str, Any]]) -> str:
        frames = []
        for index, slide in enumerate(slides):
            encoded = base64.b64encode(slide["html"].encode("utf-8")).decode("ascii")
            display = "block" if index == 0 else "none"
            frames.append(f'<div class="slide" id="slide-{index}" style="display:{display}"><iframe src="data:text/html;charset=utf-8;base64,{encoded}"></iframe></div>')
        return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>{html.escape(title)}</title><style>body{{margin:0;background:#050816;color:white;font-family:Arial,"Microsoft YaHei",sans-serif;overflow:hidden}}.stage{{width:100vw;height:100vh;display:flex;align-items:center;justify-content:center}}.slide{{width:min(100vw,177.78vh);height:min(56.25vw,100vh)}}iframe{{width:100%;height:100%;border:0;background:white}}.nav{{position:fixed;left:50%;bottom:18px;transform:translateX(-50%);background:rgba(0,0,0,.55);padding:8px 14px;border-radius:999px;display:flex;gap:10px;align-items:center}}button{{border:0;border-radius:999px;padding:8px 12px;cursor:pointer}}</style></head><body><main class="stage">{''.join(frames)}</main><div class="nav"><button onclick="prev()">上一页</button><span id="counter">1 / {len(slides)}</span><button onclick="next()">下一页</button></div><script>let i=0,n={len(slides)};function show(x){{document.querySelectorAll('.slide').forEach((s,k)=>s.style.display=k===x?'block':'none');document.getElementById('counter').textContent=(x+1)+' / '+n}}function next(){{if(i<n-1)show(++i)}}function prev(){{if(i>0)show(--i)}}document.addEventListener('keydown',e=>{{if(e.key==='ArrowRight')next();if(e.key==='ArrowLeft')prev();}});</script></body></html>"""

    def _speaker_notes(self, slide: dict[str, Any]) -> str:
        return "；".join(str(point) for point in (slide.get("content_points") or [])[:4])

    def _split_points(self, text: str) -> list[str]:
        parts = re.split(r"[，。；、\n,.；;]", text or "")
        return [part.strip() for part in parts if part.strip()][:8] or ["核心概念", "关键方法", "实践应用"]

    def _extract_json(self, raw: str) -> str:
        match = re.search(r"```(?:json)?\s*(.*?)```", raw or "", flags=re.DOTALL)
        if match:
            return match.group(1)
        start = (raw or "").find("{")
        end = (raw or "").rfind("}")
        return raw[start:end + 1] if start >= 0 and end > start else raw

    def _palette(self, theme: str) -> dict[str, str]:
        clean_theme = theme or ""
        clean_keys = ["科技", "赛博", "终端", "中国", "中式", "宣纸", "竹简", "商务", "答辩", "星月蓝", "森林", "清新", "日落", "速度", "大气红", "星月夜", "五彩斑斓的黑"]
        if any(key in clean_theme for key in clean_keys):
            return fallback_palette(clean_theme)
        if any(key in theme for key in ["科技", "赛博"]):
            return {"bg": "radial-gradient(circle at 25% 20%,#12364f 0,#0b1220 45%,#050816 100%)", "texture": "linear-gradient(120deg,rgba(34,211,238,.15),transparent 35%,rgba(99,102,241,.12))", "text": "#e5f7ff", "muted": "#9fb6c5", "accent": "#22d3ee", "line": "rgba(34,211,238,.28)", "panel": "rgba(8,20,36,.66)", "card": "rgba(15,34,58,.74)", "radius": "6px"}
        if "终端" in theme:
            return {"bg": "linear-gradient(135deg,#0a0f0a,#101810)", "texture": "linear-gradient(rgba(74,222,128,.08) 1px,transparent 1px)", "text": "#dcfce7", "muted": "#86efac", "accent": "#22c55e", "line": "rgba(34,197,94,.32)", "panel": "rgba(6,20,12,.72)", "card": "rgba(8,32,18,.78)", "radius": "4px"}
        if any(key in theme for key in ["中国", "中式", "宣纸", "竹简"]):
            return {"bg": "linear-gradient(135deg,#fbf7ef,#efe3cf)", "texture": "radial-gradient(circle at 82% 16%,rgba(127,29,29,.12),transparent 28%)", "text": "#3f2416", "muted": "#7c5c45", "accent": "#9f1239", "line": "rgba(127,29,29,.20)", "panel": "rgba(255,251,235,.72)", "card": "rgba(255,247,237,.84)", "radius": "2px"}
        if any(key in theme for key in ["商务", "答辩", "星月蓝"]):
            return {"bg": "linear-gradient(135deg,#f8fafc,#dbeafe)", "texture": "linear-gradient(90deg,rgba(15,23,42,.06),transparent)", "text": "#0f172a", "muted": "#475569", "accent": "#2563eb", "line": "rgba(37,99,235,.28)", "panel": "rgba(255,255,255,.72)", "card": "rgba(255,255,255,.84)", "radius": "6px"}
        if any(key in theme for key in ["森林", "清新"]):
            return {"bg": "linear-gradient(135deg,#f7fee7,#dcfce7)", "texture": "radial-gradient(circle at 85% 18%,rgba(34,197,94,.16),transparent 28%)", "text": "#16351f", "muted": "#4b7057", "accent": "#16a34a", "line": "rgba(22,163,74,.24)", "panel": "rgba(255,255,255,.68)", "card": "rgba(240,253,244,.9)", "radius": "8px"}
        if any(key in theme for key in ["日落", "速度", "大气红"]):
            return {"bg": "linear-gradient(135deg,#fff7ed,#fee2e2)", "texture": "radial-gradient(circle at 82% 20%,rgba(239,68,68,.18),transparent 30%)", "text": "#431407", "muted": "#9a3412", "accent": "#dc2626", "line": "rgba(220,38,38,.24)", "panel": "rgba(255,247,237,.75)", "card": "rgba(255,237,213,.86)", "radius": "6px"}
        if any(key in theme for key in ["星月夜", "五彩斑斓的黑"]):
            return {"bg": "linear-gradient(135deg,#09090b,#1e1b4b)", "texture": "radial-gradient(circle at 80% 18%,rgba(250,204,21,.18),transparent 24%)", "text": "#fafafa", "muted": "#cbd5e1", "accent": "#facc15", "line": "rgba(250,204,21,.24)", "panel": "rgba(24,24,27,.68)", "card": "rgba(39,39,42,.82)", "radius": "6px"}
        return {"bg": "linear-gradient(135deg,#ffffff 0%,#f7f8fb 52%,#eef2f7 100%)", "texture": "linear-gradient(120deg,rgba(15,23,42,.035),transparent 42%),radial-gradient(circle at 86% 18%,rgba(148,163,184,.16),transparent 30%)", "text": "#111827", "muted": "#64748b", "accent": "#334155", "line": "rgba(15,23,42,.14)", "panel": "rgba(255,255,255,.78)", "card": "rgba(248,250,252,.9)", "radius": "6px"}
