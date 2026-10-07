"""AI 页面中的学科组件协议；与前端 subjectTool 的 type/data 字段对齐。"""

from __future__ import annotations

import html
import json
import math
import re

_FIELDS = {
    "math_formula": ("latex", "display_mode"),
    "chemical_formula": ("formula",),
    "mermaid_diagram": ("mermaid",),
    "chart": ("option",),
    "table": ("columns", "rows"),
}


def _function_chart(data: dict) -> dict | None:
    """仅接受多项式系数，不执行模型提供的表达式或 JavaScript。"""
    coefficients = data.get("coefficients")
    if not isinstance(coefficients, list) or not 1 <= len(coefficients) <= 6:
        return None
    try:
        coefficients = [float(value) for value in coefficients]
        start, end = float(data.get("x_min", -5)), float(data.get("x_max", 5))
        if not all(math.isfinite(value) for value in [*coefficients, start, end]) or not -100 <= start < end <= 100:
            return None
        xs = [round(start + (end - start) * index / 40, 4) for index in range(41)]
        ys = [sum(coefficient * x ** power for power, coefficient in enumerate(coefficients)) for x in xs]
        if any(not math.isfinite(value) or abs(value) > 1e9 for value in ys):
            return None
    except (TypeError, ValueError, OverflowError):
        return None
    return {"option": {"title": {"text": str(data.get("label") or "函数图像")[:80]},
                       "xAxis": {"type": "category", "name": "x", "data": xs},
                       "yAxis": {"type": "value", "name": "y"},
                       "series": [{"type": "line", "data": [round(y, 5) for y in ys]}],
                       "a12_function_graph": True}}


def normalize_subject_components(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    result = []
    for raw in value[:2]:
        if not isinstance(raw, dict):
            continue
        kind = str(raw.get("type") or "")
        data = raw.get("data")
        if kind == "function_graph" and isinstance(data, dict):
            data = _function_chart(data)
            kind = "chart"
        if kind not in _FIELDS or not isinstance(data, dict):
            continue
        clean = {field: data[field] for field in _FIELDS[kind] if field in data}
        required = _FIELDS[kind][0]
        if required not in clean or not clean[required]:
            continue
        if kind in {"math_formula", "chemical_formula", "mermaid_diagram"} and not isinstance(clean[required], str):
            continue
        if kind == "chart" and not isinstance(clean[required], dict):
            continue
        if kind == "table" and (not isinstance(clean.get("columns"), list) or not isinstance(clean.get("rows"), list)):
            continue
        encoded = json.dumps(clean, ensure_ascii=False)
        if len(encoded) > 4000:
            continue
        result.append({"type": kind, "data": clean})
    return result


def embed_subject_component(markup: str, slide: dict, slide_no: int, *, fallback: bool = False) -> str:
    """注入可恢复的 DSL；视觉由前端同一组件渲染器输出。"""
    components = normalize_subject_components(slide.get("subject_components"))
    if not components or re.search(r'data-subject-type\s*=', markup, flags=re.IGNORECASE):
        return markup
    nodes = []
    for index, component in enumerate(components):
        kind = component["type"]
        data = html.escape(json.dumps(component["data"], ensure_ascii=False), quote=True)
        label = html.escape(str(component["data"].get("latex") or component["data"].get("formula") or "学科组件")[:100])
        position = "position:relative;width:100%;min-height:150px;margin-top:14px;" if fallback else (
            f"position:absolute;right:64px;top:{230 + index * 215}px;width:440px;height:200px;z-index:10;"
            if len(components) == 2 else "position:absolute;right:64px;top:270px;width:440px;height:230px;z-index:10;"
        )
        nodes.append(f'<div id="a12-subject-{slide_no}-{index}" class="a12-subject-tool" '
                     f'data-ppt-type="subject" data-subject-type="{kind}" data-subject-data="{data}" '
                     f'data-a12-generated-subject="1" style="{position}box-sizing:border-box;overflow:hidden;'
                     'padding:16px;border:1px solid #cbd5e1;border-radius:16px;background:#fff;color:#172554;">'
                     f'{label}</div>')
    node = "".join(nodes)
    if fallback and "</aside>" in markup:
        return markup.replace("</aside>", f"{node}</aside>", 1)
    match = re.search(r"</(?:section|main|body)>", markup, flags=re.IGNORECASE)
    return markup[:match.start()] + node + markup[match.start():] if match else markup + node
