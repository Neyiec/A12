"""Versioned, course-scoped knowledge and skill graph.

Only explicit course manifests define nodes/relations. Parsed documents can add
source evidence to existing nodes, never silently create curriculum facts.
"""

import json
import re
from typing import Any

from .config import get_settings

RELATIONS = {"prerequisite", "contains", "supports", "assesses", "applies"}
KINDS = {"concept", "skill"}


def validate_graph(payload: dict[str, Any]) -> dict[str, Any]:
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
        clean_nodes.append({"id": node_id, "label": label, "kind": kind, "description": str(node.get("description") or "")[:500]})
    clean_edges = []
    for edge in edges:
        if not isinstance(edge, dict) or edge.get("source") not in ids or edge.get("target") not in ids or edge.get("relation") not in RELATIONS:
            raise ValueError("关系类型或端点无效")
        clean_edges.append({"source": edge["source"], "target": edge["target"], "relation": edge["relation"]})
    return {"nodes": clean_nodes, "edges": clean_edges}


class CourseGraphStore:
    def _connect(self):
        import psycopg
        from psycopg.rows import dict_row
        return psycopg.connect(get_settings().postgres_dsn, row_factory=dict_row)

    def put(self, user_id: str, course_id: str, title: str, graph: dict[str, Any]) -> dict[str, Any]:
        clean = validate_graph(graph)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("""INSERT INTO a12_course_graph(user_id,course_id,title,graph_data)
                VALUES (%s,%s,%s,%s::jsonb) ON CONFLICT(user_id,course_id) DO UPDATE SET
                title=EXCLUDED.title,graph_data=EXCLUDED.graph_data,
                version=a12_course_graph.version+1,updated_at=NOW()
                RETURNING version""", (user_id, course_id, title, json.dumps(clean, ensure_ascii=False)))
            version = cur.fetchone()["version"]
            # A reused node ID may have a new meaning in the revised curriculum.
            # Require resources to be re-indexed before old excerpts are trusted.
            cur.execute("DELETE FROM a12_graph_evidence WHERE user_id=%s AND course_id=%s", (user_id, course_id))
        return {"course_id": course_id, "title": title, "version": version, **clean}

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
        selected = [node for _, node in sorted(scored, key=lambda item: -item[0])[:limit]]
        selected_ids = {node["id"] for node in selected}
        # One-hop prerequisites are essential when planning a lesson.
        for edge in graph["edges"]:
            if (edge["relation"] == "prerequisite" and edge["target"] in selected_ids) or (
                edge["relation"] == "contains" and edge["target"] in selected_ids
            ) or (
                edge["relation"] in {"supports", "applies", "assesses"} and edge["source"] in selected_ids
            ):
                related_id = edge["target"] if edge["source"] in selected_ids else edge["source"]
                parent = next((node for node in graph["nodes"] if node["id"] == related_id), None)
                if parent and parent["id"] not in selected_ids and len(selected) < limit + 4:
                    selected.append(parent)
                    selected_ids.add(parent["id"])
        edges = [edge for edge in graph["edges"] if edge["source"] in selected_ids and edge["target"] in selected_ids]
        evidence: list[dict[str, Any]] = []
        if selected_ids:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute("""SELECT node_id,resource_key,content_sha256,excerpt FROM a12_graph_evidence
                    WHERE user_id=%s AND course_id=%s AND node_id=ANY(%s) ORDER BY created_at DESC LIMIT 20""",
                    (user_id, course_id, list(selected_ids)))
                evidence = [dict(row) for row in cur.fetchall()]
        return {"course_id": course_id, "version": graph["version"], "nodes": selected, "edges": edges, "evidence": evidence}

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

    def choose_strategy(self, user_id: str, course_id: str, graph_available: bool, rag_enabled: bool) -> dict[str, Any]:
        if not graph_available:
            return {"name": "rag" if rag_enabled else "direct", "reason": "无课程图谱，使用现有路径"}
        # Conservative policy: require enough real feedback before preferring one route.
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("""SELECT r.strategy, COUNT(*) AS samples,
                    COUNT(*) FILTER (WHERE f.action IN ('manual_edit','reject','regenerate')) AS revisions
                FROM a12_outline_strategy_run r JOIN a12_ai_feedback f
                  ON f.user_id=r.user_id AND f.session_id=r.session_id
                WHERE r.user_id=%s AND r.course_id=%s AND f.target_type='outline'
                GROUP BY r.strategy""", (user_id, course_id))
            rows = cur.fetchall()
        rates = {row["strategy"]: row["revisions"] / row["samples"] for row in rows if row["samples"] >= 5}
        candidates = ("rag", "graph_rag") if rag_enabled else ("direct", "graph")
        # Compare routes only after both have enough evidence, otherwise keep
        # the graph-assisted default rather than overfitting one-sided feedback.
        preferred = min(candidates, key=lambda name: rates[name]) if all(name in rates for name in candidates) else candidates[1]
        return {"name": preferred, "reason": "基于至少 5 条大纲反馈的修改率" if rates else "冷启动默认图谱与 RAG 结合",
                "observed_revision_rates": rates}

    def record_strategy(self, user_id: str, session_id: str, course_id: str, strategy: str, graph_version: int | None) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("""INSERT INTO a12_outline_strategy_run(user_id,session_id,course_id,strategy,graph_version)
                VALUES (%s,%s,%s,%s,%s) ON CONFLICT(user_id,session_id) DO NOTHING""",
                (user_id, session_id, course_id, strategy, graph_version))


course_graph_store = CourseGraphStore()
