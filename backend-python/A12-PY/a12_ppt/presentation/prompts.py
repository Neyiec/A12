import json
from typing import Any


def compact_template_html(template_html: str, limit: int = 12000) -> str:
    value = (template_html or "").strip()
    if len(value) <= limit:
        return value
    return value[:limit] + "\n<!-- template truncated for prompt budget -->"


def slides_summary(slides: list[dict[str, Any]], max_chars: int = 3500) -> str:
    lines: list[str] = []
    used = 0
    for idx, slide in enumerate(slides, 1):
        title = str(slide.get("title") or f"第 {idx} 页").strip()
        slide_type = str(slide.get("slide_type") or slide.get("type") or "content").strip()
        points = slide.get("content_points") or slide.get("points") or []
        if isinstance(points, list):
            point_text = "；".join(str(p).strip()[:42] for p in points[:3] if str(p).strip())
        else:
            point_text = str(points).strip()[:120]
        line = f"{idx}. {title}（类型：{slide_type}"
        if point_text:
            line += f"；要点：{point_text}"
        line += "）"
        if used + len(line) > max_chars:
            lines.append(f"... 其余 {len(slides) - idx + 1} 页略写，请延续整体节奏。")
            break
        lines.append(line)
        used += len(line)
    return "\n".join(lines) if lines else "无大纲"


def project_brief(title: str, theme: str, req: dict[str, Any]) -> str:
    return "\n".join([
        f"- 主题：{title}",
        f"- 学科：{req.get('subject') or '未指定'}",
        f"- 年级/受众：{req.get('grade') or req.get('target_audience') or '未指定'}",
        f"- 风格偏好：{theme}",
        f"- 补充要求：{req.get('requirements') or req.get('description') or '无'}",
        f"- 语言：{req.get('language') or 'zh-CN'}",
    ])


def style_gene_prompt(template_name: str, template_html: str) -> str:
    return f"""
请从下面的 LandPPT 模板中提炼“风格基因”，用于后续生成整套 HTML PPT。

模板名称：{template_name}

你必须输出结构化中文，不要写 HTML，不要写 Markdown 代码块。重点提炼：
1. 配色系统：背景、主色、强调色、文字色、透明度。
2. 版式骨架：标题位置、内容区结构、留白、页码/页脚。
3. 组件语言：卡片、线条、标签、图形、装饰元素。
4. 字体与层级：标题、正文、数字、注释。
5. 禁止事项：哪些视觉元素不能混入其他模板风格。

模板 HTML：
{compact_template_html(template_html)}
""".strip()


def global_constitution_prompt(
    title: str,
    theme: str,
    request_context: dict[str, Any],
    style_genes: str,
    slides: list[dict[str, Any]],
) -> str:
    return f"""
请为整套 HTML PPT 制定全局视觉宪法，用于约束所有页面保持同一模板风格。

项目信息：
{project_brief(title, theme, request_context)}

页面大纲：
{slides_summary(slides)}

风格基因：
{style_genes}

输出要求：
- 只输出中文规则，不要 Markdown 代码块。
- 明确每页必须继承的背景、色彩、字体层级、装饰语言和页脚/页码规则。
- 明确每种页面类型（封面、目录/过渡、内容、对比、总结）应如何变化。
- 明确禁止混入其他模板风格。例如用户选择“素白风”时，不得混用“科技风”的深色霓虹、网格线、赛博蓝光。
- 固定画布为 1280x720，页面不得滚动，文字不得溢出或遮挡。
""".strip()


def page_briefs_prompt(
    title: str,
    theme: str,
    request_context: dict[str, Any],
    style_genes: str,
    global_constitution: str,
    slides: list[dict[str, Any]],
) -> str:
    return f"""
请为每一页 PPT 生成独立创意 brief，供后续并发生成 HTML 使用。

项目信息：
{project_brief(title, theme, request_context)}

整套大纲：
{slides_summary(slides)}

风格基因：
{style_genes}

全局视觉宪法：
{global_constitution}

输出严格 JSON，不要 Markdown。格式：
{{
  "1": "第 1 页 brief",
  "2": "第 2 页 brief"
}}

每页 brief 必须包含：页面目的、视觉中心、布局、组件、强调元素、应避免的问题。所有 brief 必须严格使用当前模板风格：{theme}。
""".strip()


def slide_html_prompt(
    title: str,
    theme: str,
    request_context: dict[str, Any],
    template_name: str,
    template_html: str,
    style_genes: str,
    global_constitution: str,
    page_brief: str,
    slide: dict[str, Any],
    slide_no: int,
    total: int,
    all_slides: list[dict[str, Any]],
) -> str:
    return f"""
请生成一页高质量 HTML PPT。只输出完整 HTML，不要解释，不要 Markdown。

项目信息：
{project_brief(title, theme, request_context)}

当前模板：
- theme：{theme}
- template_name：{template_name}

风格基因：
{style_genes}

全局视觉宪法：
{global_constitution}

本页创意 brief：
{page_brief}

整套页面摘要：
{slides_summary(all_slides)}

当前页数据：
{json.dumps(slide, ensure_ascii=False)}

硬性要求：
- 必须输出完整 `<!DOCTYPE html><html>...</html>`。
- 固定 1280x720 画布，body 和主 slide 容器必须 `overflow:hidden`。
- 只生成第 {slide_no}/{total} 页，不要生成多页。
- 必须严格继承 `{theme}` 模板风格，不得混入其他模板的配色和装饰。
- 可参考模板 HTML 的结构和视觉语言，但不要留下模板占位文字。
- 内容必须来自当前页数据和大纲，不要胡编事实。
- 中文排版要精致，文字不能超出容器；必要时减少字数。
- CSS 写在 `<style>` 中，不能依赖外部 CDN。

模板 HTML 参考：
{compact_template_html(template_html)}
""".strip()


def repair_html_prompt(original_prompt: str, broken_html: str, errors: list[str], warnings: list[str]) -> str:
    return f"""
上一次生成的 HTML 未通过校验，请在保留原设计意图的前提下修复。只输出修复后的完整 HTML。

校验错误：
{json.dumps(errors, ensure_ascii=False)}

校验警告：
{json.dumps(warnings, ensure_ascii=False)}

上一次 HTML：
{broken_html[:16000]}

原始任务：
{original_prompt[:12000]}
""".strip()
