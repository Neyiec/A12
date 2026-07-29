import json
import uuid
from typing import Any

from ..config import get_settings


class PostgresOutlineMemoryStore:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.available = True

    def load_or_create_session(self, user_id: str, session_id: str | None) -> tuple[str, dict[str, Any]]:
        session_id = session_id or f"outline_chat_{uuid.uuid4().hex[:12]}"
        row = self._fetch_session(user_id, session_id)
        if row:
            return session_id, row
        state = {"messages": [], "intent": {}, "final_prompt": "", "outline": {}}
        self._execute(
            """
            INSERT INTO a12_outline_chat_session
              (user_id, session_id, intent, final_prompt, outline_data, status)
            VALUES (%s, %s, %s::jsonb, %s, %s::jsonb, %s)
            ON CONFLICT (user_id, session_id) DO NOTHING
            """,
            (user_id, session_id, json.dumps({}), "", json.dumps({}), "active"),
        )
        return session_id, state

    def save_session(self, user_id: str, session_id: str, state: dict[str, Any], status: str = "active") -> None:
        self._execute(
            """
            INSERT INTO a12_outline_chat_session
              (user_id, session_id, title, intent, final_prompt, outline_data, status, last_message_at)
            VALUES (%s, %s, %s, %s::jsonb, %s, %s::jsonb, %s, NOW())
            ON CONFLICT (user_id, session_id) DO UPDATE SET
              title = EXCLUDED.title,
              intent = EXCLUDED.intent,
              final_prompt = EXCLUDED.final_prompt,
              outline_data = EXCLUDED.outline_data,
              status = EXCLUDED.status,
              last_message_at = NOW(),
              updated_at = NOW()
            """,
            (
                user_id,
                session_id,
                (state.get("intent") or {}).get("title"),
                json.dumps(state.get("intent") or {}, ensure_ascii=False),
                state.get("final_prompt") or "",
                json.dumps(state.get("outline") or {}, ensure_ascii=False),
                status,
            ),
        )

    def append_message(self, user_id: str, session_id: str, role: str, content: str, metadata: dict[str, Any] | None = None) -> None:
        self._execute(
            """
            INSERT INTO a12_outline_chat_message (user_id, session_id, role, content, metadata)
            VALUES (%s, %s, %s, %s, %s::jsonb)
            """,
            (user_id, session_id, role, content, json.dumps(metadata or {}, ensure_ascii=False)),
        )

    def save_generation(self, user_id: str, session_id: str, response: dict[str, Any], final_prompt: str) -> None:
        self._execute(
            """
            INSERT INTO a12_outline_generation_record
              (user_id, session_id, outline_id, title, final_prompt, outline_data, slide_count)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)
            """,
            (
                user_id,
                session_id,
                response.get("outline_id"),
                response.get("title"),
                final_prompt,
                json.dumps(response.get("outline") or {}, ensure_ascii=False),
                response.get("slide_count") or 0,
            ),
        )

    def save_teacher_style_memory(
        self,
        user_id: str,
        session_id: str,
        source_message: str,
        extracted_style: dict[str, Any],
        score: float,
        reason: str,
    ) -> None:
        self._execute(
            """
            INSERT INTO a12_teacher_style_memory
              (user_id, session_id, source_message, extracted_style, necessity_score, reason)
            VALUES (%s, %s, %s, %s::jsonb, %s, %s)
            """,
            (user_id, session_id, source_message, json.dumps(extracted_style, ensure_ascii=False), score, reason),
        )
        self._execute(
            """
            INSERT INTO a12_teacher_style_profile
              (user_id, style_summary, profile, evidence_count, confidence)
            VALUES (%s, %s, %s::jsonb, 1, %s)
            ON CONFLICT (user_id) DO UPDATE SET
              style_summary = CASE
                WHEN a12_teacher_style_profile.style_summary IS NULL OR a12_teacher_style_profile.style_summary = ''
                THEN EXCLUDED.style_summary
                ELSE a12_teacher_style_profile.style_summary || E'\n' || EXCLUDED.style_summary
              END,
              profile = a12_teacher_style_profile.profile || EXCLUDED.profile,
              evidence_count = a12_teacher_style_profile.evidence_count + 1,
              confidence = GREATEST(a12_teacher_style_profile.confidence, EXCLUDED.confidence),
              updated_at = NOW()
            """,
            (
                user_id,
                str(extracted_style.get("summary") or reason),
                json.dumps(extracted_style, ensure_ascii=False),
                score,
            ),
        )

    def list_sessions(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        try:
            import psycopg
            from psycopg.rows import dict_row

            with psycopg.connect(self.settings.postgres_dsn, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT user_id, session_id, title, intent, status, last_message_at, created_at, updated_at
                        FROM a12_outline_chat_session
                        WHERE user_id = %s
                        ORDER BY updated_at DESC
                        LIMIT %s
                        """,
                        (user_id, limit),
                    )
                    return [dict(row) for row in cur.fetchall()]
        except Exception:
            self.available = False
            return []

    def get_teacher_profile(self, user_id: str) -> dict[str, Any] | None:
        try:
            import psycopg
            from psycopg.rows import dict_row

            with psycopg.connect(self.settings.postgres_dsn, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT user_id, style_summary, profile, evidence_count, confidence, created_at, updated_at
                        FROM a12_teacher_style_profile
                        WHERE user_id = %s
                        """,
                        (user_id,),
                    )
                    row = cur.fetchone()
                    return dict(row) if row else None
        except Exception:
            self.available = False
            return None

    def _fetch_session(self, user_id: str, session_id: str) -> dict[str, Any] | None:
        try:
            import psycopg
            from psycopg.rows import dict_row

            with psycopg.connect(self.settings.postgres_dsn, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT s.intent, s.final_prompt, s.outline_data,
                               COALESCE(
                                 jsonb_agg(jsonb_build_object('role', m.role, 'content', m.content) ORDER BY m.created_at)
                                   FILTER (WHERE m.id IS NOT NULL),
                                 '[]'::jsonb
                               ) AS messages
                        FROM a12_outline_chat_session s
                        LEFT JOIN a12_outline_chat_message m
                          ON m.user_id = s.user_id AND m.session_id = s.session_id
                        WHERE s.user_id = %s AND s.session_id = %s
                        GROUP BY s.id
                        """,
                        (user_id, session_id),
                    )
                    row = cur.fetchone()
                    if not row:
                        return None
                    return {
                        "messages": row.get("messages") or [],
                        "intent": row.get("intent") or {},
                        "final_prompt": row.get("final_prompt") or "",
                        "outline": row.get("outline_data") or {},
                    }
        except Exception:
            self.available = False
            return None

    def _execute(self, sql: str, params: tuple[Any, ...]) -> None:
        try:
            import psycopg

            with psycopg.connect(self.settings.postgres_dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                conn.commit()
        except Exception:
            self.available = False


postgres_memory_store = PostgresOutlineMemoryStore()
