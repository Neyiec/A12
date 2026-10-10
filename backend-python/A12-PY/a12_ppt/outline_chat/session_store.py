import copy
import time
import uuid
from typing import Any

from .postgres_store import postgres_memory_store


class OutlineSessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}

    def load_or_create(self, user_id: str, session_id: str | None) -> tuple[str, dict[str, Any]]:
        pg_session_id, pg_state = postgres_memory_store.load_or_create_session(user_id, session_id)
        if postgres_memory_store.available:
            return pg_session_id, pg_state

        key = self._key(user_id, session_id or "")
        if session_id and key in self._sessions:
            return session_id, copy.deepcopy(self._sessions[key])
        new_id = session_id or f"outline_chat_{uuid.uuid4().hex[:12]}"
        state = {
            "session_id": new_id,
            "user_id": user_id,
            "messages": [],
            "intent": {},
            "final_prompt": "",
            "outline": {},
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        self._sessions[self._key(user_id, new_id)] = copy.deepcopy(state)
        return new_id, state

    def create(self, user_id: str, title: str | None = None) -> dict[str, Any]:
        session_id, state = self.load_or_create(user_id, None)
        if title:
            state["title"] = title
            state.setdefault("intent", {})["title"] = title
            self.save(user_id, session_id, state)
        return self.get(user_id, session_id) or state

    def save(self, user_id: str, session_id: str, state: dict[str, Any], status: str = "active") -> None:
        postgres_memory_store.save_session(user_id, session_id, state, status=status)
        state = copy.deepcopy(state)
        state["user_id"] = user_id
        state["session_id"] = session_id
        state["status"] = status
        state["updated_at"] = time.time()
        self._sessions[self._key(user_id, session_id)] = state

    def append_message(self, user_id: str, session_id: str, role: str, content: str, metadata: dict[str, Any] | None = None) -> None:
        postgres_memory_store.append_message(user_id, session_id, role, content, metadata)
        key = self._key(user_id, session_id)
        if key in self._sessions:
            self._sessions[key].setdefault("messages", []).append({"role": role, "content": content,
                                                                     "metadata": metadata or {}})

    def get(self, user_id: str, session_id: str) -> dict[str, Any] | None:
        row = postgres_memory_store.get_session(user_id, session_id)
        if postgres_memory_store.available and row:
            return row
        key = self._key(user_id, session_id)
        state = self._sessions.get(key)
        return copy.deepcopy(state) if state else None

    def update_title(self, user_id: str, session_id: str, title: str) -> dict[str, Any] | None:
        row = postgres_memory_store.update_session_title(user_id, session_id, title)
        if postgres_memory_store.available:
            return row
        key = self._key(user_id, session_id)
        if key not in self._sessions:
            return None
        self._sessions[key]["title"] = title
        self._sessions[key].setdefault("intent", {})["title"] = title
        self._sessions[key]["updated_at"] = time.time()
        return copy.deepcopy(self._sessions[key])

    def update_skill_graph(self, user_id: str, session_id: str, skill: dict[str, Any]) -> dict[str, Any]:
        from .learning_graphs import validate_skill_edit
        state = self.get(user_id, session_id)
        if not state:
            raise LookupError("备课会话不存在")
        pending = (state.get("outline") or {}).get("pending_graph_review")
        if state.get("status") != "awaiting_graph_confirmation" or not isinstance(pending, dict):
            raise ValueError("当前不处于双图谱确认阶段，不能修改技能图谱")
        graphs = pending["learning_graphs"]
        previous = copy.deepcopy(graphs["skill"])
        graphs["skill"] = validate_skill_edit(skill, graphs["knowledge"])
        graphs["status"] = "teacher_modified_draft"
        self.save(user_id, session_id, state, status="awaiting_graph_confirmation")
        self.append_message(user_id, session_id, "user", "教师修改了技能图谱", {
            "type": "skill_graph_edit", "before": previous, "after": graphs["skill"],
        })
        return copy.deepcopy(graphs)

    def graph_review(self, user_id: str, session_id: str) -> dict[str, Any]:
        state = self.get(user_id, session_id)
        if not state:
            raise LookupError("备课会话不存在")
        if state.get("status") != "awaiting_graph_confirmation" or not isinstance((state.get("outline") or {}).get("pending_graph_review"), dict):
            raise ValueError("当前不处于双图谱确认阶段")
        return state

    def update_learning_graphs(self, user_id: str, session_id: str, graphs: dict[str, Any]) -> dict[str, Any]:
        from .learning_graphs import validate_graph_edit
        state = self.graph_review(user_id, session_id)
        pending = state["outline"]["pending_graph_review"]
        previous = copy.deepcopy(pending["learning_graphs"])
        updated = {**previous, **validate_graph_edit(graphs), "status": "teacher_modified_draft"}
        pending["learning_graphs"] = updated
        self.save(user_id, session_id, state, status="awaiting_graph_confirmation")
        self.append_message(user_id, session_id, "user", "教师确认保存了双图谱修改", {
            "type": "learning_graph_edit", "before": previous, "after": updated,
        })
        return copy.deepcopy(updated)

    def delete(self, user_id: str, session_id: str) -> bool:
        deleted = postgres_memory_store.delete_session(user_id, session_id)
        if postgres_memory_store.available:
            return deleted
        key = self._key(user_id, session_id)
        return self._sessions.pop(key, None) is not None

    def list_sessions(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        rows = postgres_memory_store.list_sessions(user_id, limit=limit)
        if rows:
            return rows
        values = []
        for state in self._sessions.values():
            if state.get("user_id") == user_id:
                values.append({
                    "user_id": user_id,
                    "session_id": state.get("session_id"),
                    "title": (state.get("intent") or {}).get("title"),
                    "intent": state.get("intent") or {},
                    "status": "active",
                    "updated_at": state.get("updated_at"),
                })
        return sorted(values, key=lambda item: item.get("updated_at") or 0, reverse=True)[:limit]

    def _key(self, user_id: str, session_id: str) -> str:
        return f"{user_id}:{session_id}"


outline_session_store = OutlineSessionStore()
