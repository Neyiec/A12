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
