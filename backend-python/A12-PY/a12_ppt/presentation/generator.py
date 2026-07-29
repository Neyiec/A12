import asyncio
import base64
import html
import json
import re
import uuid
from typing import Any

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
from ..models import OutlineGenerateRequest, OutlineUpdateRequest, PresentationGenerateRequest, SlideModifyRequest
from ..resources import build_rag_context
from .template_store import DEFAULT_THEME, get_template


class PPTGenerator:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.llm = LLMClient()

    async def generate_outline(self, req: OutlineGenerateRequest) -> dict[str, Any]:
        slide_count = req.slide_count or 8
        req = self._with_resource_context(req)
        outline = await self._generate_outline_with_model(req, slide_count) if self.llm.available else self._fallback_outline(req, slide_count)
        outline["subject"] = req.subject
        outline["grade"] = req.grade
        outline["requirements"] = req.requirements
        outline["generation_options"] = {
            "resource_ids": req.resource_ids,
            "enable_web": req.enable_web,
            "enable_rag": req.enable_rag,
            "regenerate_instruction": req.regenerate_instruction,
        }
        return self._outline_response(outline)

    async def update_outline(self, req: OutlineUpdateRequest) -> dict[str, Any]:
        outline = dict(req.outline or {})
        if not self.llm.available:
            outline["revision_note"] = req.instruction
            return self._outline_response(outline)

        rag_context = build_rag_context(req.resource_ids) if req.enable_rag else ""
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
        return self._outline_response(outline)

    async def generate_presentation(self, req: PresentationGenerateRequest) -> dict[str, Any]:
        slides = self._normalize_slides_for_deck(self._extract_slides(req.outline) or self._fallback_outline_from_title(req.title, 6))
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
                    "metadata": {
                        "theme": requested_theme,
                        "requested_theme": requested_theme,
                        "template_name": template_name,
                        "missing_template": missing_template,
                        "aspect_ratio": req.aspect_ratio,
                        "quality_pipeline": self.llm.available and self.settings.enable_quality_pipeline,
                        "quality_preset": self.settings.quality_preset,
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
                raw = await self.llm.complete("你是  资深视觉总监，只输出 JSON。", prompt, 0.35)
                data = json.loads(self._extract_json(raw))
                return self._normalize_quality_assets(data, fallback)
            except Exception:
                return fallback

        try:
            style_genes = await self.llm.complete("你是  模板分析专家。", style_gene_prompt(template_name, template_html), 0.25)
            constitution = await self.llm.complete(
                "你是  视觉总监。",
                global_constitution_prompt(title, theme, request_context, style_genes, slides),
                0.3,
            )
            briefs_raw = await self.llm.complete(
                "你是  页面创意总监，只输出 JSON。",
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
        prompt = f"""
请生成教学 PPT 大纲，返回严格 JSON，不要 Markdown。
字段：title, summary, slides。
slides 每项字段：slide_no, title, slide_type, content_points(list), teaching_intent, visual_suggestion。

课程：{req.title}
学科：{req.subject}
年级：{req.grade}
页数：{slide_count}
教学目标：{req.teaching_goals or ""}
知识点：{", ".join(req.knowledge_points)}
补充要求：{req.requirements or ""}
是否启用联网增强：{req.enable_web}
是否启用 RAG 增强：{req.enable_rag}
重生成/附加要求：{req.regenerate_instruction or ""}
参考资料：{(req.reference_text or "")[:9000]}
""".strip()
        try:
            raw = await self.llm.complete("你是资深教学设计专家，只输出可解析 JSON。", prompt, 0.25)
            data = json.loads(self._extract_json(raw))
            if isinstance(data, dict) and data.get("slides"):
                return self._normalize_outline(data, req.title)
        except Exception:
            pass
        return self._fallback_outline(req, slide_count)

    def _with_resource_context(self, req: OutlineGenerateRequest) -> OutlineGenerateRequest:
        if not req.resource_ids:
            return req
        limit = 12000 if req.enable_rag else 5000
        rag_context = build_rag_context(req.resource_ids, limit=limit)
        merged_reference = "\n\n".join(part for part in [req.reference_text or "", rag_context] if part.strip())
        data = req.model_dump()
        data["reference_text"] = merged_reference
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
        return {
            "title": req.title,
            "summary": f"围绕 {req.subject} {req.grade}《{req.title}》组织的教学 PPT。",
            "slides": slides,
        }

    def _fallback_outline_from_title(self, title: str, slide_count: int) -> list[dict[str, Any]]:
        return self._fallback_outline(OutlineGenerateRequest(title=title, subject="通用", grade="通用", slide_count=slide_count), slide_count)["slides"]

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
                })
        data["title"] = data.get("title") or title
        data["slides"] = slides
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
        }

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
