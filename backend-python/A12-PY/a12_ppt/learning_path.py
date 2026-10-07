"""课程先修路径与有预算的检索子图，不调用模型，不执行用户代码。"""
import json
import math
import time


def estimated_tokens(value: object) -> int:
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    non_ascii = sum(ord(char) > 127 for char in text)
    return non_ascii + math.ceil((len(text) - non_ascii) / 4)


def topological_ids(nodes: list[dict], edges: list[dict]) -> list[str]:
    ids = [node["id"] for node in nodes]
    indegree = dict.fromkeys(ids, 0)
    children = {node_id: [] for node_id in ids}
    for edge in edges:
        if edge["relation"] != "prerequisite":
            continue
        if edge["source"] == edge["target"]:
            raise ValueError("先修关系不能指向自身")
        children[edge["source"]].append(edge["target"])
        indegree[edge["target"]] += 1
    ready = [node_id for node_id in ids if indegree[node_id] == 0]
    ordered = []
    while ready:
        current = ready.pop(0)
        ordered.append(current)
        for child in children[current]:
            indegree[child] -= 1
            if not indegree[child]:
                ready.append(child)
    if len(ordered) != len(ids):
        raise ValueError("先修关系存在循环，请修改关系后重试")
    return ordered


def plan_learning_path(graph: dict, targets: list[str], start: str | None = None,
                       mastered: list[str] | None = None, max_nodes: int = 24) -> dict:
    nodes = {node["id"]: node for node in graph["nodes"]}
    if not targets or any(node_id not in nodes for node_id in [*targets, *(mastered or []), *([start] if start else [])]):
        raise ValueError("请选择有效的目标知识点、起点或已掌握节点")
    prerequisites = {node_id: [] for node_id in nodes}
    for edge in graph["edges"]:
        if edge["relation"] == "prerequisite":
            prerequisites[edge["target"]].append(edge["source"])
    selected = set(targets)
    queue = list(targets)
    while queue:
        for parent in prerequisites[queue.pop(0)]:
            if parent not in selected:
                selected.add(parent)
                queue.append(parent)
    if start and start not in selected:
        raise ValueError("起点不在所选目标的先修路径中")
    selected -= set(mastered or []) - set(targets)
    if len(selected) > max_nodes:
        raise ValueError(f"必要先修路径超过{max_nodes}个节点，请缩小目标范围或标记已掌握节点")
    ordered = topological_ids(graph["nodes"], graph["edges"])
    path = [nodes[node_id] for node_id in ordered if node_id in selected]
    skill_ids = {edge["target"] for edge in graph["edges"] if edge["source"] in selected
                 and edge["relation"] in {"supports", "applies", "assesses"} and nodes[edge["target"]]["kind"] == "skill"}
    return {"course_id": graph.get("course_id"), "course_version": graph.get("version"),
            "nodes": path, "skills": [nodes[node_id] for node_id in sorted(skill_ids)],
            "edges": [edge for edge in graph["edges"] if edge["source"] in selected and edge["target"] in selected],
            "target_ids": list(dict.fromkeys(targets)), "mastered_ids": mastered or [],
            "context": "\n".join(f"{index + 1}. {node['label']}：{node.get('description', '')}" for index, node in enumerate(path))}


def prune_graph(graph: dict, seed_ids: list[str], hops: int = 1, max_nodes: int = 16,
                token_budget: int = 3000) -> dict:
    started = time.perf_counter()
    nodes = {node["id"]: node for node in graph["nodes"]}
    seeds = list(dict.fromkeys(seed_ids))
    if any(node_id not in nodes for node_id in seeds):
        raise ValueError("检索节点不存在")
    selected = list(seeds)
    seen = set(selected)
    frontier = set(selected)
    for _ in range(hops):
        candidates = []
        for edge in graph["edges"]:
            other = None
            if edge["target"] in frontier and edge["relation"] in {"prerequisite", "contains"}:
                other = edge["source"]
            elif edge["source"] in frontier and edge["relation"] in {"supports", "applies", "assesses"}:
                other = edge["target"]
            elif edge["relation"] == "related":
                if edge["source"] in frontier:
                    other = edge["target"]
                elif edge["target"] in frontier:
                    other = edge["source"]
            if other and other not in seen:
                candidates.append(other)
        frontier = set()
        for node_id in sorted(set(candidates), key=lambda key: (-nodes[key].get("exam_frequency", 0) * nodes[key].get("difficulty", 0.5), key)):
            if len(selected) < max_nodes:
                selected.append(node_id)
                seen.add(node_id)
                frontier.add(node_id)
    def subset(ids):
        return {"nodes": [nodes[node_id] for node_id in ids],
                "edges": [edge for edge in graph["edges"] if edge["source"] in ids and edge["target"] in ids]}
    if len(seeds) > max_nodes or estimated_tokens(subset(seeds)) > token_budget:
        raise ValueError("主题节点超出上下文预算，请缩小主题或提高预算")
    while len(selected) > len(seeds) and estimated_tokens(subset(selected)) > token_budget:
        selected.pop()
    result = subset(selected)
    before = estimated_tokens({"nodes": graph["nodes"], "edges": graph["edges"]})
    after = estimated_tokens(result)
    result["pruning_metrics"] = {"nodes_before": len(nodes), "nodes_after": len(selected),
        "estimated_tokens_before": before, "estimated_tokens_after": after,
        "estimated_token_saving_ratio": round(1 - after / max(1, before), 4),
        "seed_coverage": 1.0 if seeds else 0.0, "hops": hops, "token_budget": token_budget,
        "truncated": len(selected) < len(nodes), "latency_ms": round((time.perf_counter() - started) * 1000),
        "token_measurement": "estimate_not_provider_usage"}
    return result
