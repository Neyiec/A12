import json
import uuid
from datetime import datetime, timezone
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
    ) -> bool:
        memory_saved = self._execute(
            """
            INSERT INTO a12_teacher_style_memory
              (user_id, session_id, source_message, extracted_style, necessity_score, reason)
            VALUES (%s, %s, %s, %s::jsonb, %s, %s)
            """,
            (user_id, session_id, source_message, json.dumps(extracted_style, ensure_ascii=False), score, reason),
        )
        profile_saved = self._execute(
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
        return memory_saved and profile_saved

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

    def get_session(self, user_id: str, session_id: str) -> dict[str, Any] | None:
        return self._fetch_session(user_id, session_id)

    def update_session_title(self, user_id: str, session_id: str, title: str) -> dict[str, Any] | None:
        try:
            import psycopg
            from psycopg.rows import dict_row

            with psycopg.connect(self.settings.postgres_dsn, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE a12_outline_chat_session
                        SET title = %s, updated_at = NOW()
                        WHERE user_id = %s AND session_id = %s
                        RETURNING user_id, session_id, title, intent, status, last_message_at, created_at, updated_at
                        """,
                        (title, user_id, session_id),
                    )
                    row = cur.fetchone()
                conn.commit()
                return dict(row) if row else None
        except Exception:
            self.available = False
            return None

    def delete_session(self, user_id: str, session_id: str) -> bool:
        try:
            import psycopg

            with psycopg.connect(self.settings.postgres_dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        DELETE FROM a12_outline_chat_session
                        WHERE user_id = %s AND session_id = %s
                        """,
                        (user_id, session_id),
                    )
                    deleted = cur.rowcount > 0
                conn.commit()
                return deleted
        except Exception:
            self.available = False
            return False

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
                    if not row:
                        return None
                    result = dict(row)
                    cur.execute("""SELECT action,target_type,instruction,change_summary,metadata,created_at
                                   FROM a12_ai_feedback WHERE user_id=%s
                                   ORDER BY created_at DESC LIMIT 20""", (user_id,))
                    result["recent_feedback"] = [dict(item) for item in cur.fetchall()]
                    # Confidence decays slowly when a profile has not received evidence for a long time.
                    age_days = (datetime.now(timezone.utc) - result["updated_at"]).days if result.get("updated_at") else 0
                    result["effective_confidence"] = round(float(result.get("confidence") or 0) * 0.995 ** min(365, max(0, age_days)), 4)
                    return result
        except Exception:
            self.available = False
            return None

    def record_feedback(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Store explicit/implicit teacher feedback and update a bounded preference summary."""
        user_id = str(payload.get("user_id") or "").strip()
        action = str(payload.get("action") or "").strip()
        metadata = dict(payload.get("metadata") or {})
        try:
            import psycopg
            with psycopg.connect(self.settings.postgres_dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO a12_ai_feedback
                          (event_id,user_id,session_id,project_id,action,target_type,instruction,change_summary,before_data,after_data,metadata)
                          VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb)
                          ON CONFLICT DO NOTHING RETURNING id""",
                        (payload.get("event_id"), user_id, payload.get("session_id"), payload.get("project_id"), action,
                         payload.get("target_type") or "presentation", payload.get("instruction"),
                         payload.get("change_summary"), json.dumps(payload.get("before_data") or {}, ensure_ascii=False),
                         json.dumps(payload.get("after_data") or {}, ensure_ascii=False), json.dumps(metadata, ensure_ascii=False)),
                    )
                    inserted = cur.fetchone() is not None
                    if inserted and action in {"accept", "manual_edit"}:
                        preference = {
                            "last_positive_action": action,
                            "last_change_summary": str(payload.get("change_summary") or "")[:500],
                            "last_instruction": str(payload.get("instruction") or "")[:500],
                            "subject": metadata.get("subject"), "grade": metadata.get("grade"),
                        }
                        cur.execute(
                            """INSERT INTO a12_teacher_style_profile(user_id,style_summary,profile,evidence_count,confidence)
                               VALUES (%s,%s,%s::jsonb,1,0.55)
                               ON CONFLICT(user_id) DO UPDATE SET profile=a12_teacher_style_profile.profile || EXCLUDED.profile,
                               style_summary=EXCLUDED.style_summary,evidence_count=a12_teacher_style_profile.evidence_count+1,
                               confidence=LEAST(0.98, a12_teacher_style_profile.confidence + 0.03),updated_at=NOW()""",
                            (user_id, preference["last_change_summary"] or preference["last_instruction"],
                             json.dumps(preference, ensure_ascii=False)),
                        )
            return {"stored": True, "duplicate": not inserted, "action": action,
                    "profile_updated": bool(inserted and action in {"accept", "manual_edit"})}
        except Exception as exc:
            self.available = False
            return {"stored": False, "action": action, "profile_updated": False, "error": str(exc)[:300]}

    def ai_metrics(self, limit: int = 50) -> dict[str, Any]:
        try:
            import psycopg
            from psycopg.rows import dict_row
            with psycopg.connect(self.settings.postgres_dsn, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute("""SELECT operation,status,model,COUNT(*) runs,
                              ROUND(AVG(latency_ms)) avg_latency_ms,SUM(input_tokens) input_tokens,
                              SUM(output_tokens) output_tokens
                              FROM a12_ai_run_log GROUP BY operation,status,model ORDER BY runs DESC LIMIT %s""", (limit,))
                    runs = [dict(row) for row in cur.fetchall()]
                    cur.execute("SELECT action, COUNT(*) count FROM a12_ai_feedback GROUP BY action ORDER BY count DESC")
                    feedback = [dict(row) for row in cur.fetchall()]
            return {"runs": runs, "feedback": feedback, "postgres_available": True}
        except Exception as exc:
            self.available = False
            return {"runs": [], "feedback": [], "postgres_available": False, "error": str(exc)[:300]}

    def record_classroom_event(self, payload: dict[str, Any]) -> bool:
        return self._execute("""INSERT INTO a12_classroom_event
          (event_id,user_id,project_id,session_id,student_key,event_type,question_id,answer,correct,response_ms,metadata)
          VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb) ON CONFLICT DO NOTHING""", (
            payload.get("event_id"), payload.get("user_id"), payload.get("project_id"), payload.get("session_id"),
            payload.get("student_key"), payload.get("event_type"), payload.get("question_id"),
            payload.get("answer"), payload.get("correct"), payload.get("response_ms"),
            json.dumps(payload.get("metadata") or {}, ensure_ascii=False),
        ))

    def classroom_insights(self, user_id: str, project_id: str) -> dict[str, Any]:
        try:
            import psycopg
            from psycopg.rows import dict_row
            with psycopg.connect(self.settings.postgres_dsn, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute("""SELECT question_id,COUNT(*) responses,
                              COUNT(*) FILTER (WHERE correct IS TRUE) correct_count,
                              ROUND(AVG(response_ms)) avg_response_ms
                              FROM a12_classroom_event WHERE user_id=%s AND project_id=%s AND event_type='answer'
                              GROUP BY question_id
                              ORDER BY (COUNT(*) FILTER (WHERE correct IS TRUE))::float / NULLIF(COUNT(*),0) ASC""",
                                (user_id, project_id))
                    questions = [dict(row) for row in cur.fetchall()]
                    cur.execute("""SELECT event_type,COUNT(*) count FROM a12_classroom_event
                              WHERE user_id=%s AND project_id=%s GROUP BY event_type""", (user_id, project_id))
                    events = [dict(row) for row in cur.fetchall()]
            for item in questions:
                item["accuracy"] = round(int(item.get("correct_count") or 0) / max(1, int(item.get("responses") or 0)), 4)
            return {"project_id": project_id, "questions": questions, "events": events,
                    "weak_question_ids": [item.get("question_id") for item in questions if item.get("accuracy", 1) < 0.6]}
        except Exception as exc:
            return {"project_id": project_id, "questions": [], "events": [], "error": str(exc)[:300]}

    def _fetch_session(self, user_id: str, session_id: str) -> dict[str, Any] | None:
        try:
            import psycopg
            from psycopg.rows import dict_row

            with psycopg.connect(self.settings.postgres_dsn, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT s.user_id, s.session_id, s.title, s.intent, s.final_prompt, s.outline_data,
                               s.status, s.last_message_at, s.created_at, s.updated_at,
                               COALESCE(
                                 jsonb_agg(jsonb_build_object(
                                   'role', m.role,
                                   'content', m.content,
                                   'metadata', m.metadata,
                                   'created_at', m.created_at
                                 ) ORDER BY m.created_at)
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
                        "user_id": row.get("user_id"),
                        "session_id": row.get("session_id"),
                        "title": row.get("title"),
                        "messages": row.get("messages") or [],
                        "intent": row.get("intent") or {},
                        "final_prompt": row.get("final_prompt") or "",
                        "outline": row.get("outline_data") or {},
                        "status": row.get("status"),
                        "last_message_at": row.get("last_message_at"),
                        "created_at": row.get("created_at"),
                        "updated_at": row.get("updated_at"),
                    }
        except Exception:
            self.available = False
            return None

    def _execute(self, sql: str, params: tuple[Any, ...]) -> bool:
        try:
            import psycopg

            with psycopg.connect(self.settings.postgres_dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                conn.commit()
            return True
        except Exception:
            self.available = False
            return False


postgres_memory_store = PostgresOutlineMemoryStore()
