"""Versioned, course-scoped knowledge and skill graph.

Only explicit course manifests define nodes/relations. Parsed documents can add
source evidence to existing nodes, never silently create curriculum facts.
"""

import json
import hashlib
import re
import math
from typing import Any

from .config import get_settings
from .learning_path import topological_ids, prune_graph, estimated_tokens

RELATIONS = {"prerequisite", "contains", "supports", "assesses", "applies", "related"}
KINDS = {"concept", "skill"}


class GraphVersionConflict(ValueError):
    pass


def validate_graph(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("图谱必须是JSON对象")
    nodes = payload.get("nodes") or []
    edges = payload.get("edges") or []
    if not isinstance(nodes, list) or not isinstance(edges, list) or not nodes or len(nodes) > 300 or len(edges) > 900:
        raise ValueError("图谱节点或关系数量超出限制")
    ids: set[str] = set()
    clean_nodes = []
    for node in nodes:
        if not isinstance(node, dict):
            raise ValueError("节点格式不正确")
        node_id = str(node.get("id") or "").strip()
        label = str(node.get("label") or "").strip()
        kind = str(node.get("kind") or "")
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", node_id) or not label or len(label) > 120 or kind not in KINDS or node_id in ids:
            raise ValueError(f"节点无效或重复: {node_id}")
        ids.add(node_id)
        try:
            difficulty = float(node.get("difficulty", 0.5))
            exam_frequency = float(node.get("exam_frequency", 0))
            if not math.isfinite(difficulty) or not math.isfinite(exam_frequency) or not 0 <= difficulty <= 1 or not 0 <= exam_frequency <= 1:
                raise ValueError("节点难度和考频应在0到1之间")
        except (TypeError, ValueError) as exc:
            raise ValueError("节点难度和考频应在0到1之间") from exc
        bloom = str(node.get("bloom") or "understand")
        if bloom not in {"remember", "understand", "apply", "analyze", "evaluate", "create"}:
            raise ValueError("认知层级无效")
        refs = node.get("resource_ids") or []
        if not isinstance(refs, list) or len(refs) > 20 or any(not isinstance(ref, str) or len(ref) > 180 for ref in refs):
            raise ValueError("节点资料引用无效")
        clean_nodes.append({"id": node_id, "label": label, "kind": kind, "description": str(node.get("description") or "")[:500],
                            "subject": str(node.get("subject") or "")[:80], "difficulty": difficulty,
                            "exam_frequency": exam_frequency, "bloom": bloom, "resource_ids": refs,
                            "mastery_standard": str(node.get("mastery_standard") or "")[:500]})
        clean_nodes[-1]['task'] = str(node.get('task') or '')[:500]
        clean_nodes[-1]['assessment'] = str(node.get('assessment') or node.get('mastery_standard') or '')[:500]
        position = node.get("position")
        if isinstance(position, dict):
            try:
                x, y = float(position["x"]), float(position["y"])
                if math.isfinite(x) and math.isfinite(y):
                    clean_nodes[-1]["position"] = {"x": max(0, min(520, x)), "y": max(0, min(12000, y))}
            except (KeyError, ValueError, TypeError):
                pass
    clean_edges = []
    kinds = {node["id"]: node["kind"] for node in clean_nodes}
    seen_edges = set()
    for edge in edges:
        if not isinstance(edge, dict) or edge.get("source") not in ids or edge.get("target") not in ids or edge.get("relation") not in RELATIONS:
            raise ValueError("关系类型或端点无效")
        key = (edge["source"], edge["target"], edge["relation"])
        if edge["source"] == edge["target"] or key in seen_edges:
            raise ValueError("关系不能重复或指向自身")
        if edge["relation"] == "supports" and (kinds[edge["source"]] != "concept" or kinds[edge["target"]] != "skill"):
            raise ValueError("知识与技能映射应从知识点指向技能节点")
        seen_edges.add(key)
        clean_edges.append({"source": edge["source"], "target": edge["target"], "relation": edge["relation"]})
    topological_ids(clean_nodes, clean_edges)
    return {"nodes": clean_nodes, "edges": clean_edges,
            "subject": str(payload.get('subject') or '')[:80], "grade": str(payload.get('grade') or '')[:80]}


class CourseGraphStore:
    def _connect(self):
        import psycopg
        from psycopg.rows import dict_row
        return psycopg.connect(get_settings().postgres_dsn, row_factory=dict_row)

    def put(self, user_id: str, course_id: str, title: str, graph: dict[str, Any], expected_version: int | None = None) -> dict[str, Any]:
        clean = validate_graph(graph)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"course:{user_id}:{course_id}",))
            cur.execute("SELECT title,version,graph_data FROM a12_course_graph WHERE user_id=%s AND course_id=%s FOR UPDATE", (user_id, course_id))
            previous = cur.fetchone()
            if expected_version is not None and expected_version != (previous["version"] if previous else 0):
                raise GraphVersionConflict("图谱已被更新，请重新加载后保存")
            if previous:
                cur.execute("""INSERT INTO a12_course_graph_version(user_id,course_id,version,title,graph_data)
                    VALUES (%s,%s,%s,%s,%s::jsonb) ON CONFLICT DO NOTHING""",
                    (user_id, course_id, previous["version"], previous["title"], json.dumps(previous["graph_data"], ensure_ascii=False)))
            cur.execute("""INSERT INTO a12_course_graph(user_id,course_id,title,graph_data)
                VALUES (%s,%s,%s,%s::jsonb) ON CONFLICT(user_id,course_id) DO UPDATE SET
                title=EXCLUDED.title,graph_data=EXCLUDED.graph_data,
                version=a12_course_graph.version+1,updated_at=NOW()
                RETURNING version""", (user_id, course_id, title, json.dumps(clean, ensure_ascii=False)))
            version = cur.fetchone()["version"]
            cur.execute("""INSERT INTO a12_course_graph_version(user_id,course_id,version,title,graph_data)
                VALUES (%s,%s,%s,%s,%s::jsonb)""", (user_id, course_id, version, title, json.dumps(clean, ensure_ascii=False)))
            # A reused node ID may have a new meaning in the revised curriculum.
            # Require resources to be re-indexed before old excerpts are trusted.
            cur.execute("DELETE FROM a12_graph_evidence WHERE user_id=%s AND course_id=%s", (user_id, course_id))
        return {"course_id": course_id, "title": title, "version": version, **clean}

    def list_courses(self, user_id: str) -> list[dict]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("""SELECT course_id,title,version,updated_at,
                jsonb_array_length(graph_data->'nodes') AS node_count FROM a12_course_graph
                WHERE user_id=%s ORDER BY updated_at DESC LIMIT 100""", (user_id,))
            return [dict(row) for row in cur.fetchall()]

    def versions(self, user_id: str, course_id: str) -> list[dict]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("""SELECT version,title,created_at FROM a12_course_graph_version
                WHERE user_id=%s AND course_id=%s ORDER BY version DESC LIMIT 50""", (user_id, course_id))
            return [dict(row) for row in cur.fetchall()]

    def get_version(self, user_id: str, course_id: str, version: int) -> dict | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT title,graph_data FROM a12_course_graph_version WHERE user_id=%s AND course_id=%s AND version=%s", (user_id, course_id, version))
            row = cur.fetchone()
        return {"title": row["title"], **row["graph_data"]} if row else None

    def get(self, user_id: str, course_id: str) -> dict[str, Any] | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT course_id,title,version,graph_data FROM a12_course_graph WHERE user_id=%s AND course_id=%s", (user_id, course_id))
            row = cur.fetchone()
        return {"course_id": row["course_id"], "title": row["title"], "version": row["version"], **row["graph_data"]} if row else None

    def match_course(self, user_id: str, query: str) -> str | None:
        if not query.strip():
            return None
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT course_id,title,graph_data FROM a12_course_graph WHERE user_id=%s ORDER BY updated_at DESC LIMIT 50", (user_id,))
            rows = cur.fetchall()
        query_lower = query.lower()
        matches = []
        for row in rows:
            labels = [node.get("label", "") for node in row["graph_data"].get("nodes", [])]
            score = sum(1 for label in labels if len(label) >= 3 and label.lower() in query_lower)
            if row["title"].lower() in query_lower:
                score += 2
            if score:
                matches.append((score, row["course_id"]))
        matches.sort(reverse=True)
        return matches[0][1] if matches and (len(matches) == 1 or matches[0][0] > matches[1][0]) else None

    def retrieve(self, user_id: str, course_id: str, query: str, limit: int = 12) -> dict[str, Any]:
        graph = self.get(user_id, course_id)
        if not graph:
            return {"course_id": course_id, "nodes": [], "edges": [], "version": None}
        query_lower = query.lower()
        scored = []
        for node in graph["nodes"]:
            label = node["label"].lower()
            score = 2 if label in query_lower else (1 if any(part in query_lower for part in re.split(r"[\s、，,]+", label) if len(part) > 1) else 0)
            if score:
                scored.append((score, node))
        seeds = [node["id"] for _, node in sorted(scored, key=lambda item: -item[0])[:limit]]
        pruned = prune_graph(graph, seeds, hops=1, max_nodes=limit + 4, token_budget=4500)
        selected, edges = pruned["nodes"], pruned["edges"]
        selected_ids = {node["id"] for node in selected}
        evidence: list[dict[str, Any]] = []
        if selected_ids:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute("""SELECT node_id,resource_key,content_sha256,excerpt FROM a12_graph_evidence
                    WHERE user_id=%s AND course_id=%s AND node_id=ANY(%s) ORDER BY created_at DESC LIMIT 20""",
                    (user_id, course_id, list(selected_ids)))
                evidence = [dict(row) for row in cur.fetchall()]
        result = {"course_id": course_id, "version": graph["version"], "nodes": selected, "edges": edges, "evidence": evidence}
        while evidence and estimated_tokens(result) > 5000:
            evidence.pop()
        pruned["pruning_metrics"]["context_estimated_tokens"] = estimated_tokens(result)
        pruned["pruning_metrics"]["context_token_budget"] = 5000
        return {**result, "pruning_metrics": pruned["pruning_metrics"]}

    def add_resource_evidence(self, user_id: str, course_id: str, resource_key: str, digest: str, text: str) -> int:
        graph = self.get(user_id, course_id)
        if not graph:
            return 0
        evidence = []
        text_lower = text.lower()
        for node in graph["nodes"]:
            label = node["label"]
            if len(label) < 3:
                continue
            position = text_lower.find(label.lower())
            if position >= 0:
                evidence.append((node["id"], text[max(0, position - 80):position + len(label) + 120]))
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM a12_graph_evidence WHERE user_id=%s AND course_id=%s AND resource_key=%s",
                        (user_id, course_id, resource_key))
            for node_id, excerpt in evidence:
                cur.execute("""INSERT INTO a12_graph_evidence(user_id,course_id,resource_key,content_sha256,node_id,excerpt)
                    VALUES (%s,%s,%s,%s,%s,%s)""", (user_id, course_id, resource_key, digest, node_id, excerpt))
        return len(evidence)

    def strategy_effects(self, user_id: str, course_id: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("""WITH outcomes AS (
                SELECT session_id, BOOL_OR(action='accept') AS accepted,
                    BOOL_OR(action IN ('manual_edit','reject','regenerate','undo')) AS revised
                FROM a12_ai_feedback
                WHERE user_id=%s AND target_type='outline'
                  AND created_at >= NOW() - INTERVAL '90 days'
                GROUP BY session_id
            )
            SELECT r.strategy, COUNT(*) AS runs,
                COUNT(o.session_id) FILTER (WHERE o.accepted OR o.revised) AS samples,
                COUNT(*) FILTER (WHERE o.accepted) AS accepted,
                COUNT(*) FILTER (WHERE o.revised) AS revisions
            FROM a12_outline_strategy_run r LEFT JOIN outcomes o USING (session_id)
            WHERE r.user_id=%s AND (%s::text IS NULL OR r.course_id=%s)
              AND r.created_at >= NOW() - INTERVAL '90 days'
            GROUP BY r.strategy ORDER BY r.strategy""", (user_id, user_id, course_id, course_id))
            rows = cur.fetchall()
        return [{**row, "revision_rate": row["revisions"] / row["samples"] if row["samples"] else None}
                for row in rows]

    def choose_strategy(self, user_id: str, course_id: str, graph_available: bool, rag_enabled: bool,
                        session_id: str | None = None) -> dict[str, Any]:
        if not graph_available:
            return {"name": "rag" if rag_enabled else "direct", "reason": "无课程图谱，使用现有路径"}
        alternative, default = ("rag", "graph_rag") if rag_enabled else ("direct", "graph")
        if session_id:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute("""SELECT strategy FROM a12_outline_strategy_run
                    WHERE user_id=%s AND session_id=%s AND course_id=%s""", (user_id, session_id, course_id))
                previous = cur.fetchone()
            if previous and previous["strategy"] in (alternative, default):
                return {"name": previous["strategy"], "reason": "延续当前大纲会话的策略"}
        rows = self.strategy_effects(user_id, course_id)
        rates = {row["strategy"]: row["revision_rate"] for row in rows if row["samples"] >= 5}
        preferred, reason = default, "可比较的历史反馈不足，优先使用课程图谱"
        if default in rates and alternative in rates:
            preferred = alternative if rates[default] - rates[alternative] >= 0.15 else default
            reason = "根据本课程近 90 天的大纲返工率选择"
        elif default in rates and session_id:
            bucket = int(hashlib.sha256(f"{user_id}:{session_id}".encode()).hexdigest()[:8], 16) % 10
            if bucket == 0:
                preferred, reason = alternative, "小流量试用备选策略，收集对照反馈"
        return {"name": preferred, "reason": reason, "observed_revision_rates": rates}

    def record_strategy(self, user_id: str, session_id: str, course_id: str | None, strategy: str, graph_version: int | None) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("""INSERT INTO a12_outline_strategy_run(user_id,session_id,course_id,strategy,graph_version)
                VALUES (%s,%s,%s,%s,%s) ON CONFLICT(user_id,session_id) DO NOTHING""",
                (user_id, session_id, course_id, strategy, graph_version))


course_graph_store = CourseGraphStore()
