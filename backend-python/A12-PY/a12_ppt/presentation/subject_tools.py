"""学科工具（subject tools）生成契约与后处理。

前端把学科工具实现为一套「容器标记 + 结构化 data」的组件协议：
``frontend/src/utils/subjectTool.js`` 定义 10 种类型与 data schema，
``CreationWorkspace.vue`` 的 ``subjectComponentsFromHtml`` 会扫描页面 HTML 中的
``[data-ppt-type="subject"][data-subject-type][data-subject-data]`` 节点，把它们
还原成可编辑的学科工具组件并回写 pages.components。

本模块为 AI 生成链路补上「产出侧」能力：

1. :func:`subject_tools_prompt_section` —— 注入逐页 HTML prompt，约定标记格式与每种类型的 data 结构；
2. :func:`subject_tools_preserve_note` —— 供「改页/新增页」prompt 复用，要求保留既有学科工具；
3. :func:`normalize_subject_tool_markup` —— 对模型输出做后处理：修复属性引号与 JSON 错误、
   归一化类型别名、补齐唯一 id 与默认 data，避免前端拿到脏数据后回退成错误组件。
"""

import copy
import json
import re
from typing import Any

SUBJECT_TOOL_TYPES: tuple[str, ...] = (
    "math_formula",
    "geometry",
    "coordinate_system",
    "solid_geometry",
    "chinese_tianzige",
    "english_four_line",
    "chemical_formula",
    "mermaid_diagram",
    "chart",
    "table",
)

# 与前端 normalizeSubjectToolType 的别名保持一致。
TYPE_ALIASES: dict[str, str] = {
    "math": "math_formula",
    "formula": "math_formula",
    "equation": "math_formula",
    "physics": "math_formula",
    "geometry_figure": "geometry",
    "coordinate": "coordinate_system",
    "coordinates": "coordinate_system",
    "axes": "coordinate_system",
    "solid": "solid_geometry",
    "solid_figure": "solid_geometry",
    "chinese": "chinese_tianzige",
    "tianzige": "chinese_tianzige",
    "pinyin": "chinese_tianzige",
    "english": "english_four_line",
    "four_line": "english_four_line",
    "chemical": "chemical_formula",
    "molecule": "chemical_formula",
    "diagram": "mermaid_diagram",
    "flowchart": "mermaid_diagram",
    "data_chart": "chart",
    "data_table": "table",
}

DEFAULT_SUBJECT_DATA: dict[str, dict[str, Any]] = {
    "math_formula": {"latex": "a^2 + b^2 = c^2", "display_mode": True},
    "geometry": {"construction": "right_triangle"},
    "coordinate_system": {
        "xRange": 5,
        "yRange": 4,
        "showGrid": True,
        "connectPoints": False,
        "segments": [],
        "points": [{"label": "A", "x": 2, "y": 3}, {"label": "B", "x": -2, "y": -1}],
    },
    "solid_geometry": {
        "solid": "cube",
        "dimensions": {"length": 4, "width": 3, "height": 5, "radius": 2},
        "show_hidden_edges": True,
        "show_dimensions": True,
    },
    "chinese_tianzige": {
        "entries": [{"character": "你", "pinyin": "nǐ"}, {"character": "好", "pinyin": "hǎo"}],
        "show_pinyin": True,
    },
    "english_four_line": {"text": "Aa Bb Cc"},
    "chemical_formula": {"formula": "H2O"},
    "mermaid_diagram": {"mermaid": "flowchart LR\nA[提出问题] --> B[观察与探究]\nB --> C[形成结论]"},
    "chart": {
        "option": {
            "xAxis": {"type": "category", "data": ["A 组", "B 组", "C 组"]},
            "yAxis": {"type": "value"},
            "series": [{"type": "bar", "data": [68, 82, 56]}],
        },
        "responsive": True,
    },
    "table": {"columns": ["项目", "观察结果"], "rows": [["实验组", ""], ["对照组", ""]]},
}

# prompt 里逐条展示的「类型 → 用途 → data 结构」说明。
SUBJECT_TOOL_SPECS: tuple[dict[str, str], ...] = (
    {
        "type": "math_formula",
        "label": "数学/物理公式",
        "usage": "呈现关键公式、定理或推导结果",
        "schema": '{"latex":"a^2+b^2=c^2","display_mode":true}',
    },
    {
        "type": "geometry",
        "label": "几何图形",
        "usage": "平面几何构图、证明题配图（顶点可由学生拖动）",
        "schema": '{"construction":"right_triangle","points":[{"x":18,"y":82},{"x":156,"y":82},{"x":156,"y":18}]}',
    },
    {
        "type": "coordinate_system",
        "label": "平面直角坐标系",
        "usage": "描点、函数图像、位置与坐标",
        "schema": '{"xRange":5,"yRange":4,"showGrid":true,"connectPoints":false,"points":[{"label":"A","x":2,"y":3}],"segments":[[0,1]]}',
    },
    {
        "type": "solid_geometry",
        "label": "立体图形",
        "usage": "正方体/长方体/棱锥/圆柱/圆锥/球的体积与展开",
        "schema": '{"solid":"cube","dimensions":{"length":4,"width":3,"height":5,"radius":2},"show_hidden_edges":true,"show_dimensions":true}',
    },
    {
        "type": "chinese_tianzige",
        "label": "语文田字格/拼音",
        "usage": "生字书写示范、笔顺与拼音认读",
        "schema": '{"entries":[{"character":"你","pinyin":"nǐ"}],"show_pinyin":true}',
    },
    {
        "type": "english_four_line",
        "label": "英语四线格",
        "usage": "字母与单词书写示范（每个词一个四线格组）",
        "schema": '{"text":"Aa Bb Cc\\nHello"}',
    },
    {
        "type": "chemical_formula",
        "label": "化学式/分子式",
        "usage": "化学式、结构式与分子模型",
        "schema": '{"formula":"H2O"}',
    },
    {
        "type": "mermaid_diagram",
        "label": "流程图",
        "usage": "实验步骤、思维路径、因果链",
        "schema": '{"mermaid":"flowchart LR\\nA[提出问题] --> B[形成结论]"}',
    },
    {
        "type": "chart",
        "label": "数据图表",
        "usage": "实验数据对比、统计图（ECharts option 结构）",
        "schema": '{"option":{"xAxis":{"type":"category","data":["A 组","B 组"]},"yAxis":{"type":"value"},"series":[{"type":"bar","data":[68,82]}]},"responsive":true}',
    },
    {
        "type": "table",
        "label": "探究数据表",
        "usage": "实验记录表、对照表、分类归纳表",
        "schema": '{"columns":["项目","观察结果"],"rows":[["实验组",""],["对照组",""]]}',
    },
)

SUBJECT_TOOL_CONTAINER_HINT = (
    '容器格式（class 与 data 属性缺一不可）：'
    '<div id="subject-1" class="a12-subject-tool" data-ppt-type="subject" '
    'data-subject-type="类型" data-subject-data=\'JSON\' data-name="工具名称">…</div>'
)


def subject_tools_prompt_section() -> str:
    """生成注入到逐页 HTML prompt 的学科工具契约说明。"""
    lines = [
        "学科工具（可选增强，仅当该页教学确实需要时使用，一页最多 2 个）：",
        f"- {SUBJECT_TOOL_CONTAINER_HINT}",
        "- data-subject-data 必须是用单引号包裹的合法 JSON，JSON 内部只能使用双引号，字符串里不得出现单引号。",
        "- 每个容器必须带全页唯一 id；同一页出现多个学科工具时 id 不能重复。",
        "- 容器内部必须同时给出自绘的 SVG/HTML 视觉内容（自适应容器尺寸、不得依赖外部 CDN），"
        "静态预览与 PPTX 导出会使用这份内容，工作台会在此基础上补齐可编辑能力。",
        "- 类型与 data 结构：",
    ]
    for spec in SUBJECT_TOOL_SPECS:
        lines.append(f"  · {spec['type']}（{spec['label']}，{spec['usage']}）：{spec['schema']}")
    return "\n".join(lines)


def subject_tools_preserve_note() -> str:
    """改页/新增页 prompt 复用的保留要求。"""
    return (
        "如果原页面包含学科工具容器（带 data-subject-type / data-subject-data 的元素），"
        "必须完整保留其 id、class 与全部 data-subject-* 属性，只允许更新容器内部的自绘内容。"
    )


# ---------------------------------------------------------------------------
# 后处理：规范化模型输出的学科工具标记
# ---------------------------------------------------------------------------

_ATTR_NAME_RE = re.compile(r"[A-Za-z_:][-A-Za-z0-9_:.]*")
_SUBJECT_MARKERS = ("data-subject-type", "data-subject-data", 'data-ppt-type="subject"')
_JSON_ESCAPES = (("&", "\\u0026"), ("<", "\\u003c"), (">", "\\u003e"), ("'", "\\u0027"))
_GEOMETRY_CONSTRUCTIONS = (
    "right_triangle",
    "triangle",
    "equilateral_triangle",
    "rectangle",
    "square",
    "parallelogram",
    "rhombus",
    "custom",
)
_SOLID_SHAPES = ("cube", "cuboid", "pyramid", "cylinder", "cone", "sphere")
_DIMENSION_KEYS = ("length", "width", "height", "radius")


def normalize_subject_tool_type(value: Any) -> str:
    """归一化类型名；未知类型回退 geometry（与前端一致）。"""
    token = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if token in SUBJECT_TOOL_TYPES:
        return token
    return TYPE_ALIASES.get(token, "geometry")


def default_subject_data(subject_type: str) -> dict[str, Any]:
    normalized = normalize_subject_tool_type(subject_type)
    return copy.deepcopy(DEFAULT_SUBJECT_DATA.get(normalized, DEFAULT_SUBJECT_DATA["geometry"]))


def normalize_subject_tool_markup(markup: str) -> str:
    """修复并规范化 HTML 中的学科工具容器；无标记时原样返回。"""
    source = markup or ""
    lowered = source.lower()
    if not any(marker in lowered for marker in _SUBJECT_MARKERS):
        return source

    pieces: list[str] = []
    cursor = 0
    changed = False
    counter = 0
    used_ids: set[str] = set()
    for start, end in _iter_tags(source):
        tag_text = source[start:end]
        if not _looks_like_subject_tag(tag_text):
            continue
        counter += 1
        rebuilt = _normalize_tag(tag_text, counter, used_ids)
        if not rebuilt or rebuilt == tag_text:
            continue
        pieces.append(source[cursor:start])
        pieces.append(rebuilt)
        cursor = end
        changed = True
    if not changed:
        return source
    pieces.append(source[cursor:])
    return "".join(pieces)


def _iter_tags(markup: str):
    """逐个产出标签的 [start, end) 区间。

    使用引号感知的扫描器而不是正则：模型常把 data-subject-data 的引号写错
    （如 ``data-subject-data="{"x":1}"``），或在 JSON 里含撇号，正则容易截断标签。
    """
    length = len(markup)
    cursor = 0
    while cursor < length:
        start = markup.find("<", cursor)
        if start < 0:
            return
        if start + 1 >= length or not markup[start + 1].isalpha():
            cursor = start + 1
            continue
        end = _find_tag_end(markup, start)
        if end < 0:
            return
        yield start, end
        cursor = end


def _find_tag_end(markup: str, start: int) -> int:
    end = _scan_tag_end_with_quotes(markup, start)
    if end > 0:
        return end
    # 模型常把属性引号写错（例如单引号包裹的 JSON 里出现撇号），
    # 引号感知扫描会失效，此时退化为「找第一个 >」，再交给属性解析器修复。
    return _scan_tag_end_plain(markup, start)


def _scan_tag_end_with_quotes(markup: str, start: int) -> int:
    quote = ""
    cursor = start + 1
    length = len(markup)
    while cursor < length:
        char = markup[cursor]
        if quote:
            if char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
        elif char == ">":
            return cursor + 1
        elif char == "<":
            return -1
        cursor += 1
    return -1


def _scan_tag_end_plain(markup: str, start: int) -> int:
    cursor = start + 1
    length = len(markup)
    while cursor < length:
        char = markup[cursor]
        if char == ">":
            return cursor + 1
        if char == "<":
            return -1
        cursor += 1
    return -1


def _looks_like_subject_tag(tag_text: str) -> bool:
    lowered = tag_text.lower()
    return any(marker in lowered for marker in _SUBJECT_MARKERS) or "data-subject-" in lowered


def _normalize_tag(tag_text: str, index: int, used_ids: set[str]) -> str:
    split = _split_tag(tag_text)
    if not split:
        return ""
    tag_name, body, self_closing = split
    tokens = _tokenize_attributes(body)
    if not tokens:
        return ""

    attributes: list[tuple[str, str, str]] = []  # (原始 name, 原始片段, 值)
    for name, start, end, value in tokens:
        attributes.append((name, body[start:end], value if value is not None else ""))

    lookup = {name.lower(): value for name, _raw, value in attributes}
    raw_type = lookup.get("data-subject-type") or ""
    raw_data = lookup.get("data-subject-data") or ""
    raw_name = lookup.get("data-name") or lookup.get("title") or ""

    payload = _parse_json_object(raw_data)
    if not raw_type and payload is not None:
        raw_type = payload.get("subject_type") or payload.get("subjectType") or payload.get("type") or ""
    if not raw_type:
        # 只有 data 没有类型：删除标记属性，避免前端把它当作 geometry 组件还原。
        return _render_tag(tag_name, self_closing, attributes, drop=_SUBJECT_ATTR_NAMES)

    subject_type = normalize_subject_tool_type(raw_type)
    data = _normalize_subject_data(subject_type, payload if isinstance(payload, dict) else None)
    title = str(raw_name or "").strip()[:80] or _spec_label(subject_type)

    rendered = {
        "data-ppt-type": 'data-ppt-type="subject"',
        "data-subject-type": f'data-subject-type="{subject_type}"',
        "data-subject-data": f"data-subject-data='{_dump_json_attribute(data)}'",
        "data-name": f'data-name="{_escape_attribute(title)}"',
    }
    existing_id = str(lookup.get("id") or "").strip()
    if existing_id and existing_id not in used_ids:
        used_ids.add(existing_id)
    else:
        # 缺 id 或 id 与前面的学科工具重复：前端按 id 去重会丢掉组件，这里统一换成唯一 id。
        fallback_id = f"a12-subject-{index}"
        used_ids.add(fallback_id)
        rendered["id"] = f'id="{fallback_id}"'
    return _render_tag(tag_name, self_closing, attributes, override=rendered)


_SUBJECT_ATTR_NAMES = {
    "data-ppt-type",
    "data-subject-type",
    "data-subject-data",
    "data-subject-render",
    "data-subject-render-hint",
}


def _render_tag(
    tag_name: str,
    self_closing: bool,
    attributes: list[tuple[str, str, str]],
    override: dict[str, str] | None = None,
    drop: set[str] | None = None,
) -> str:
    kept: list[str] = []
    seen: set[str] = set()
    for name, raw, _value in attributes:
        lowered = name.lower()
        if drop and lowered in drop:
            continue
        if override and lowered in override:
            continue
        if lowered in seen:
            continue
        seen.add(lowered)
        kept.append(raw)
    if override:
        for key in ("id", "data-ppt-type", "data-subject-type", "data-subject-data", "data-name"):
            value = override.get(key)
            if value:
                kept.append(value)
    inner = " ".join(part for part in kept if part.strip())
    tail = " />" if self_closing and not inner else ("/>" if self_closing else ">")
    if inner:
        return f"<{tag_name} {inner}{' />' if self_closing else '>'}"
    return f"<{tag_name}{tail}"


def _split_tag(tag_text: str) -> tuple[str, str, bool] | None:
    if not tag_text.startswith("<") or not tag_text.endswith(">"):
        return None
    inner = tag_text[1:-1]
    self_closing = inner.endswith("/")
    if self_closing:
        inner = inner[:-1]
    match = re.match(r"\s*([a-zA-Z][\w:-]*)", inner)
    if not match:
        return None
    return match.group(1), inner[match.end():], self_closing


def _tokenize_attributes(body: str) -> list[tuple[str, int, int, str | None]]:
    tokens: list[tuple[str, int, int, str | None]] = []
    cursor = 0
    length = len(body)
    while cursor < length:
        match = _ATTR_NAME_RE.search(body, cursor)
        if not match:
            break
        name = match.group(0)
        pointer = match.end()
        while pointer < length and body[pointer] in " \t\r\n":
            pointer += 1
        if pointer >= length or body[pointer] != "=":
            tokens.append((name, match.start(), match.end(), None))
            cursor = match.end()
            continue
        pointer += 1
        while pointer < length and body[pointer] in " \t\r\n":
            pointer += 1
        if pointer >= length:
            tokens.append((name, match.start(), pointer, None))
            break
        value, end = _scan_attribute_value(body, pointer)
        tokens.append((name, match.start(), end, value))
        cursor = max(end, pointer + 1)
    return tokens


def _scan_attribute_value(text: str, position: int) -> tuple[str, int]:
    char = text[position]
    if char in "\"'":
        quote = char
        inner_start = position + 1
        if inner_start < len(text) and text[inner_start] in "{[":
            # 兼容 data-subject-data="{"a":1}" 这类把引号写错的 JSON 属性值。
            value, end = _scan_balanced(text, inner_start)
            if value is not None:
                if end < len(text) and text[end] == quote:
                    end += 1
                return value, end
        end = text.find(quote, inner_start)
        if end == -1:
            return text[inner_start:], len(text)
        return text[inner_start:end], end + 1
    if char in "{[":
        value, end = _scan_balanced(text, position)
        if value is not None:
            return value, end
    end = position
    while end < len(text) and text[end] not in " \t\r\n>":
        end += 1
    return text[position:end], end


def _scan_balanced(text: str, start: int) -> tuple[str | None, int]:
    if start >= len(text) or text[start] not in "{[":
        return None, start
    stack = [text[start]]
    cursor = start + 1
    while cursor < len(text):
        char = text[cursor]
        if char in "\"'":
            quote = char
            cursor += 1
            while cursor < len(text):
                if text[cursor] == "\\":
                    cursor += 2
                    continue
                if text[cursor] == quote:
                    break
                cursor += 1
            cursor += 1
            continue
        if char in "{[":
            stack.append(char)
        elif char in "}]":
            if not stack:
                break
            stack.pop()
            if not stack:
                return text[start:cursor + 1], cursor + 1
        cursor += 1
    return None, start


def _parse_json_object(raw: str) -> dict[str, Any] | None:
    text = str(raw or "").strip()
    if not text:
        return None
    for candidate in (text, _repair_json(text)):
        if not candidate:
            continue
        try:
            value = json.loads(candidate)
        except Exception:
            continue
        if isinstance(value, dict):
            return value
    return None


def _repair_json(text: str) -> str:
    fixed = text.strip().replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    fixed = re.sub(r",\s*([}\]])", r"\1", fixed)
    if '"' not in fixed and "'" in fixed:
        fixed = fixed.replace("'", '"')
    return fixed


def _normalize_subject_data(subject_type: str, data: dict[str, Any] | None) -> dict[str, Any]:
    normalized_type = normalize_subject_tool_type(subject_type)
    defaults = default_subject_data(normalized_type)
    source = data if isinstance(data, dict) else {}
    try:
        if normalized_type == "math_formula":
            return {
                "latex": _text(source.get("latex"), defaults["latex"], 2000),
                "display_mode": _flag(source.get("display_mode"), True),
            }
        if normalized_type == "geometry":
            construction = str(source.get("construction") or "").strip().lower()
            if construction not in _GEOMETRY_CONSTRUCTIONS:
                construction = defaults["construction"]
            result: dict[str, Any] = {"construction": construction}
            points = _geometry_points(source.get("points"))
            if points:
                result["points"] = points
            segments = _index_pairs(source.get("segments"), len(points) or 12)
            if segments:
                result["segments"] = segments
            commands = source.get("commands")
            if isinstance(commands, list) and commands:
                result["commands"] = [_text(item, "", 200) for item in commands[:12] if str(item or "").strip()]
            return result
        if normalized_type == "coordinate_system":
            x_range = _int_range(source.get("xRange"), 2, 10, defaults["xRange"])
            y_range = _int_range(source.get("yRange"), 2, 10, defaults["yRange"])
            points = _coordinate_points(source.get("points"), x_range, y_range) or defaults["points"]
            return {
                "xRange": x_range,
                "yRange": y_range,
                "showGrid": _flag(source.get("showGrid"), True),
                "connectPoints": _flag(source.get("connectPoints"), False),
                "points": points,
                "segments": _index_pairs(source.get("segments"), len(points)),
            }
        if normalized_type == "solid_geometry":
            solid = str(source.get("solid") or "").strip().lower()
            if solid not in _SOLID_SHAPES:
                solid = defaults["solid"]
            dimensions = source.get("dimensions") if isinstance(source.get("dimensions"), dict) else {}
            return {
                "solid": solid,
                "dimensions": {
                    key: _number_range(dimensions.get(key), 1, 20, defaults["dimensions"][key])
                    for key in _DIMENSION_KEYS
                },
                "show_hidden_edges": _flag(source.get("show_hidden_edges"), True),
                "show_dimensions": _flag(source.get("show_dimensions"), True),
            }
        if normalized_type == "chinese_tianzige":
            entries = source.get("entries")
            normalized_entries: list[dict[str, str]] = []
            if isinstance(entries, list):
                for entry in entries[:80]:
                    if isinstance(entry, dict):
                        character = _first_char(entry.get("character"))
                        pinyin = _text(entry.get("pinyin"), "", 32)
                    else:
                        character = _first_char(entry)
                        pinyin = ""
                    if character or pinyin:
                        normalized_entries.append({"character": character, "pinyin": pinyin})
            if not normalized_entries:
                text_value = str(source.get("text") or "")
                pinyin_tokens = str(source.get("pinyin") or "").split()
                for position, character in enumerate(re.sub(r"\s", "", text_value)[:80]):
                    normalized_entries.append({
                        "character": character,
                        "pinyin": pinyin_tokens[position] if position < len(pinyin_tokens) else "",
                    })
            return {
                "entries": normalized_entries or defaults["entries"],
                "show_pinyin": _flag(source.get("show_pinyin"), True),
            }
        if normalized_type == "english_four_line":
            raw_text = str(source.get("text") if source.get("text") is not None else defaults["text"])
            lines = raw_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")[:40]
            return {"text": "\n".join(lines)[:1000]}
        if normalized_type == "chemical_formula":
            result = {"formula": _text(source.get("formula"), defaults["formula"], 300)}
            smiles = _text(source.get("smiles"), "", 4000)
            molfile = _text(source.get("molfile"), "", 24000)
            if smiles:
                result["smiles"] = smiles
            if molfile:
                result["molfile"] = molfile
            return result
        if normalized_type == "mermaid_diagram":
            return {"mermaid": _text(source.get("mermaid"), defaults["mermaid"], 8000)}
        if normalized_type == "chart":
            option = source.get("option")
            if isinstance(option, str):
                parsed = _parse_json_object(option) or _parse_json_array(option)
                option = parsed if parsed is not None else option.strip()
            if not isinstance(option, (dict, list, str)) or option in ("", {}):
                option = defaults["option"]
            return {"option": option, "responsive": _flag(source.get("responsive"), True)}
        if normalized_type == "table":
            columns = source.get("columns")
            if not isinstance(columns, list):
                columns = defaults["columns"]
            rows = source.get("rows")
            if not isinstance(rows, list):
                rows = defaults["rows"]
            return {
                "columns": [_text(item, "", 80) for item in columns[:20]],
                "rows": [
                    [_text(cell, "", 200) for cell in (row if isinstance(row, list) else [row])[:20]]
                    for row in rows[:60]
                ],
            }
    except Exception:
        return defaults
    return defaults


def _parse_json_array(text: str) -> list[Any] | None:
    try:
        value = json.loads(_repair_json(text))
    except Exception:
        return None
    return value if isinstance(value, list) else None


def _spec_label(subject_type: str) -> str:
    for spec in SUBJECT_TOOL_SPECS:
        if spec["type"] == subject_type:
            return spec["label"]
    return "学科探究工具"


def _text(value: Any, fallback: str, limit: int) -> str:
    text = str(value if value is not None else "").strip()
    return (text or fallback)[:limit]


def _flag(value: Any, fallback: bool) -> bool:
    if value is None:
        return fallback
    if isinstance(value, str):
        token = value.strip().lower()
        if token in ("true", "1", "yes", "on"):
            return True
        if token in ("false", "0", "no", "off"):
            return False
        return fallback
    return bool(value)


def _number_range(value: Any, minimum: float, maximum: float, fallback: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    if number != number or number in (float("inf"), float("-inf")):
        return fallback
    return round(min(maximum, max(minimum, number)) * 10) / 10


def _int_range(value: Any, minimum: int, maximum: int, fallback: int) -> int:
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        return fallback
    return min(maximum, max(minimum, number))


def _first_char(value: Any) -> str:
    text = str(value if value is not None else "").strip()
    return text[0] if text else ""


def _geometry_points(value: Any) -> list[dict[str, float]]:
    if not isinstance(value, list):
        return []
    points: list[dict[str, float]] = []
    for item in value[:12]:
        if not isinstance(item, dict):
            continue
        try:
            x = float(item.get("x"))
            y = float(item.get("y"))
        except (TypeError, ValueError):
            continue
        points.append({
            "x": round(min(172, max(8, x)) * 10) / 10,
            "y": round(min(92, max(8, y)) * 10) / 10,
        })
    return points


def _coordinate_points(value: Any, x_range: int, y_range: int) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    points: list[dict[str, Any]] = []
    for index, item in enumerate(value[:10]):
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()[:8] or chr(ord("A") + index % 26)
        try:
            x = float(item.get("x"))
            y = float(item.get("y"))
        except (TypeError, ValueError):
            x, y = 0.0, 0.0
        points.append({
            "label": label,
            "x": round(min(x_range, max(-x_range, x)) * 100) / 100,
            "y": round(min(y_range, max(-y_range, y)) * 100) / 100,
        })
    return points


def _index_pairs(value: Any, point_count: int) -> list[list[int]]:
    if not isinstance(value, list) or point_count <= 1:
        return []
    pairs: list[list[int]] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, list) or len(item) != 2:
            continue
        try:
            start, end = int(item[0]), int(item[1])
        except (TypeError, ValueError):
            continue
        if start == end or not (0 <= start < point_count) or not (0 <= end < point_count):
            continue
        pair = sorted((start, end))
        key = f"{pair[0]}-{pair[1]}"
        if key in seen:
            continue
        seen.add(key)
        pairs.append(pair)
        if len(pairs) >= 36:
            break
    return pairs


def _dump_json_attribute(data: dict[str, Any]) -> str:
    dumped = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    for raw, escaped in _JSON_ESCAPES:
        dumped = dumped.replace(raw, escaped)
    return dumped


def _escape_attribute(value: str) -> str:
    return value.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
