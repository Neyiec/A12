import re
from typing import Any


async def diagram_tool(intent: dict[str, Any], query: str, max_nodes: int = 6) -> dict[str, Any]:
    text = " ".join([
        query or "",
        str(intent.get("title") or ""),
        str(intent.get("subject") or ""),
        str(intent.get("requirements") or ""),
        " ".join(str(item) for item in intent.get("knowledge_points") or []),
    ])
    diagram_type = _diagram_type(text)
    topic = str(intent.get("title") or "Teaching Topic")
    nodes = _knowledge_nodes(intent, text, max_nodes=max_nodes)
    mermaid = _build_mermaid(topic, nodes, diagram_type)
    return {
        "query": query,
        "requested": True,
        "diagram_type": diagram_type,
        "title": f"{topic} {diagram_type}",
        "format": "mermaid",
        "mermaid": mermaid,
        "usage": "Use this diagram as a visual suggestion in PPT pages, or render it on the frontend as Mermaid/SVG.",
        "nodes": nodes,
    }


def should_call_diagram_tool(intent: dict[str, Any], query: str) -> bool:
    text = " ".join([
        query or "",
        str(intent.get("title") or ""),
        str(intent.get("subject") or ""),
        str(intent.get("requirements") or ""),
        " ".join(str(item) for item in intent.get("knowledge_points") or []),
    ]).lower()
    keywords = [
        "diagram", "flowchart", "mindmap", "concept map", "timeline", "chart",
        "流程图", "思维导图", "概念图", "结构图", "关系图", "时间线", "图解", "示意图", "对比图", "画图", "绘图",
    ]
    process_keywords = ["过程", "流程", "步骤", "结构", "关系", "循环", "变化", "路径", "演化", "对比"]
    return any(keyword in text for keyword in keywords + process_keywords)


def _diagram_type(text: str) -> str:
    lowered = text.lower()
    if any(keyword in lowered for keyword in ["timeline", "时间线", "演化"]):
        return "timeline"
    if any(keyword in lowered for keyword in ["mindmap", "思维导图", "概念图", "关系图"]):
        return "concept_map"
    if any(keyword in lowered for keyword in ["compare", "对比", "比较"]):
        return "comparison"
    return "flowchart"


def _knowledge_nodes(intent: dict[str, Any], text: str, max_nodes: int) -> list[str]:
    raw_nodes = [str(item).strip() for item in intent.get("knowledge_points") or [] if str(item).strip()]
    if not raw_nodes:
        parts = re.split(r"[\n,，。；;、]+", text)
        raw_nodes = [part.strip() for part in parts if 2 <= len(part.strip()) <= 24]
    deduped: list[str] = []
    for node in raw_nodes:
        if node not in deduped:
            deduped.append(node)
        if len(deduped) >= max_nodes:
            break
    return deduped or ["导入", "核心概念", "案例分析", "课堂活动", "总结迁移"]


def _build_mermaid(topic: str, nodes: list[str], diagram_type: str) -> str:
    topic_id = "T"
    safe_topic = _safe_label(topic)
    if diagram_type == "timeline":
        lines = ["timeline", f"    title {safe_topic}"]
        for index, node in enumerate(nodes, 1):
            lines.append(f"    Step {index} : {_safe_label(node)}")
        return "\n".join(lines)
    if diagram_type == "comparison":
        midpoint = max(1, len(nodes) // 2)
        left = nodes[:midpoint]
        right = nodes[midpoint:] or ["课堂应用"]
        lines = ["flowchart LR", f'    {topic_id}["{safe_topic}"]']
        lines.append(f'    A["{_safe_label("维度 A")}"]')
        lines.append(f'    B["{_safe_label("维度 B")}"]')
        lines.append("    T --> A")
        lines.append("    T --> B")
        for index, node in enumerate(left, 1):
            lines.append(f'    A --> A{index}["{_safe_label(node)}"]')
        for index, node in enumerate(right, 1):
            lines.append(f'    B --> B{index}["{_safe_label(node)}"]')
        return "\n".join(lines)
    lines = ["flowchart TD", f'    {topic_id}["{safe_topic}"]']
    previous = topic_id
    for index, node in enumerate(nodes, 1):
        node_id = f"N{index}"
        lines.append(f'    {node_id}["{_safe_label(node)}"]')
        if diagram_type == "concept_map":
            lines.append(f"    {topic_id} --> {node_id}")
        else:
            lines.append(f"    {previous} --> {node_id}")
            previous = node_id
    return "\n".join(lines)


def _safe_label(value: str) -> str:
    return str(value or "").replace('"', "'").replace("\n", " ").strip()[:40] or "Node"
