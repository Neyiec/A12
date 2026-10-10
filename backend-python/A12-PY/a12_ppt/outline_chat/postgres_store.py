import json
import re
import time
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from ..config import get_settings


STYLE_SIGNALS = {
    "more_cases": ("多案例", "增加案例", "案例多一点", "更多案例"),
    "more_practice": ("多练习", "增加练习", "更多练习", "实践多一点"),
    "less_theory": ("少理论", "减少理论", "理论少一点"),
    "less_slide_text": ("少文字", "减少文字", "每页字少", "字太多"),
    "boppps": ("BOPPPS", "boppps"),
}


def extract_style_signals(text: str) -> list[str]:
    normalized = re.sub(r"\s+", "", text).lower()
    return [name for name, phrases in STYLE_SIGNALS.items() if any(phrase.lower() in normalized for phrase in phrases)]


def infer_style_signals_from_edit(metadata: dict[str, Any]) -> list[str]:
    before = metadata.get("style_before") or {}
    after = metadata.get("style_after") or {}
    if not isinstance(before, dict) or not isinstance(after, dict):
        return []
    signals = []
    try:
        if float(before.get("avg_text_chars") or 0) >= 80 and float(after.get("avg_text_chars") or 0) <= float(before["avg_text_chars"]) * 0.75:
            signals.append("less_slide_text")
        if int(after.get("activity_pages") or 0) > int(before.get("activity_pages") or 0):
            signals.append("more_practice")
        if int(after.get("case_pages") or 0) > int(before.get("case_pages") or 0):
            signals.append("more_cases")
    except (TypeError, ValueError, KeyError):
        return []
    return signals


def _json_default(value: Any) -> Any:
    """psycopg 原生类型(Decimal/datetime)在 json.dumps 时的兜底转换"""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


class PostgresOutlineMemoryStore:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.available = True
        self._profile_refresh_at: dict[str, float] = {}

    def refresh_teacher_profile(self, user_id: str) -> dict[str, Any] | None:
        """生成前按需刷新历史证据，每个教师最多每日重算一次；失败短暂退避。"""
        profile = self.get_teacher_profile(user_id)
        if not profile or not profile.get("enabled", True):
            return profile
        now = time.monotonic()
        if now < self._profile_refresh_at.get(user_id, 0):
            return profile
        last = (profile.get("profile") or {}).get("last_relearn_at")
        try:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(last)).total_seconds() if last else 86400
        except (ValueError, TypeError):
            age = 86400
        if len(self._profile_refresh_at) >= 4096:
            self._profile_refresh_at.clear()
        self._profile_refresh_at[user_id] = now + 300
        if age < 86400:
            self._profile_refresh_at[user_id] = now + max(300, 86400 - age)
            return profile
        result = self.relearn_teacher_profile(user_id)
        if not result.get("error"):
            self._profile_refresh_at[user_id] = now + 86400
        return self.get_teacher_profile(user_id) if result.get("updated") else profile

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
                json.dumps(state.get("intent") or {}, ensure_ascii=False, default=_json_default),
                state.get("final_prompt") or "",
                json.dumps(state.get("outline") or {}, ensure_ascii=False, default=_json_default),
                status,
            ),
        )

    def append_message(self, user_id: str, session_id: str, role: str, content: str, metadata: dict[str, Any] | None = None) -> None:
        self._execute(
            """
            INSERT INTO a12_outline_chat_message (user_id, session_id, role, content, metadata)
            VALUES (%s, %s, %s, %s, %s::jsonb)
            """,
            (user_id, session_id, role, content, json.dumps(metadata or {}, ensure_ascii=False, default=_json_default)),
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
                json.dumps(response.get("outline") or {}, ensure_ascii=False, default=_json_default),
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
            (user_id, session_id, source_message, json.dumps(extracted_style, ensure_ascii=False, default=_json_default), score, reason),
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
                json.dumps(extracted_style, ensure_ascii=False, default=_json_default),
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
                    result["enabled"] = (result.get("profile") or {}).get("enabled", True)
                    manual_tags = (result.get("profile") or {}).get("manual_tags") or []
                    if manual_tags:
                        result["style_summary"] = "教师明确设置：" + "、".join(manual_tags) + "。历史学习：" + str(result.get("style_summary") or "暂无")
                    material_style = (result.get("profile") or {}).get("material_style") or {}
                    if isinstance(material_style, dict) and material_style:
                        result["style_summary"] = str(result.get("style_summary") or "") + "。历史材料风格参考：" + "；".join(
                            str(value)[:150] for value in material_style.values() if isinstance(value, str))
                    cur.execute("""SELECT action,target_type,instruction,change_summary,metadata,created_at
                                   FROM a12_ai_feedback WHERE user_id=%s
                                   ORDER BY created_at DESC LIMIT 20""", (user_id,))
                    result["recent_feedback"] = [dict(item) for item in cur.fetchall()]
                    # Confidence decays slowly when a profile has not received evidence for a long time.
                    age_days = (datetime.now(timezone.utc) - result["updated_at"]).days if result.get("updated_at") else 0
                    result["effective_confidence"] = round(float(result.get("confidence") or 0) * 0.995 ** min(365, max(0, age_days)), 4)
                    # 输出为 JSON 安全类型：该画像会嵌入 intent 并被 jsonb 持久化
                    result["confidence"] = float(result.get("confidence") or 0)
                    for item in [result, *(result.get("recent_feedback") or [])]:
                        for key, value in item.items():
                            if isinstance(value, Decimal):
                                item[key] = float(value)
                            elif isinstance(value, (datetime, date)):
                                item[key] = value.isoformat()
                    return result
        except Exception:
            self.available = False
            return None

    def save_teacher_material_style(self, user_id: str, style: dict, evidence: dict) -> bool:
        payload = {"material_style": style, "material_evidence": evidence}
        return self._execute("""INSERT INTO a12_teacher_style_profile
            (user_id,style_summary,profile,evidence_count,confidence)
            VALUES (%s,'',%s::jsonb,1,0.5)
            ON CONFLICT(user_id) DO UPDATE SET
            profile=COALESCE(a12_teacher_style_profile.profile,'{}'::jsonb) || EXCLUDED.profile,
            updated_at=NOW()""", (user_id, json.dumps(payload, ensure_ascii=False)))

    def set_teacher_profile_enabled(self, user_id: str, enabled: bool) -> bool:
        """只切换长期画像是否参与生成，不清除教师已有的偏好证据。"""
        try:
            import psycopg
            with psycopg.connect(self.settings.postgres_dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO a12_teacher_style_profile
                           (user_id, style_summary, profile, evidence_count, confidence)
                           VALUES (%s, '', jsonb_build_object('enabled', %s), 0, 0)
                           ON CONFLICT (user_id) DO UPDATE SET
                           profile = jsonb_set(COALESCE(a12_teacher_style_profile.profile, '{}'::jsonb),
                                               '{enabled}', to_jsonb(%s::boolean)), updated_at = NOW()""",
                        (user_id, enabled, enabled),
                    )
                conn.commit()
            return True
        except Exception:
            self.available = False
            return False

    def set_teacher_profile_tags(self, user_id: str, tags: list[str]) -> bool:
        """手动标签存入画像 JSON，不覆盖历史反馈产生的风格证据。"""
        try:
            import psycopg
            with psycopg.connect(self.settings.postgres_dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO a12_teacher_style_profile
                           (user_id, style_summary, profile, evidence_count, confidence)
                           VALUES (%s, '', jsonb_build_object('manual_tags', %s::jsonb), 0, 0)
                           ON CONFLICT (user_id) DO UPDATE SET
                           profile = jsonb_set(COALESCE(a12_teacher_style_profile.profile, '{}'::jsonb),
                                               '{manual_tags}', %s::jsonb), updated_at = NOW()""",
                        (user_id, json.dumps(tags, ensure_ascii=False), json.dumps(tags, ensure_ascii=False)),
                    )
                conn.commit()
            return True
        except Exception:
            self.available = False
            return False

    def get_teacher_preferences(self, user_id: str) -> dict[str, Any]:
        # Read separately from the profile enrichment query; distinguish no row from DB failure.
        import psycopg
        with psycopg.connect(self.settings.postgres_dsn, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT profile->'preferences' FROM a12_teacher_style_profile WHERE user_id=%s", (user_id,))
                row = cur.fetchone()
        defaults = {"teaching_style": "", "template_style": "", "interaction_forms": ["group_discussion", "quiz"]}
        return {**defaults, **(row[0] if row and isinstance(row[0], dict) else {})}

    def save_teacher_preferences(self, user_id: str, preferences: dict[str, Any]) -> bool:
        # Update only explicit preferences, preserving learned evidence and manual tags.
        payload = json.dumps({"preferences": preferences}, ensure_ascii=False)
        return self._execute("""INSERT INTO a12_teacher_style_profile
            (user_id,style_summary,profile,evidence_count,confidence)
            VALUES (%s,'',%s::jsonb,0,0)
            ON CONFLICT(user_id) DO UPDATE SET
            profile=COALESCE(a12_teacher_style_profile.profile,'{}'::jsonb) || EXCLUDED.profile,
            updated_at=NOW()""", (user_id, payload))

    def relearn_teacher_profile(self, user_id: str) -> dict[str, Any]:
        """根据已记录的历史接受/编辑反馈重算稳定偏好；单次指令不晋升为长期记忆。"""
        try:
            import psycopg
            from psycopg.rows import dict_row
            counts = {name: 0 for name in STYLE_SIGNALS}
            with psycopg.connect(self.settings.postgres_dsn, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT instruction,change_summary,metadata FROM a12_ai_feedback
                           WHERE user_id=%s AND action IN ('accept','manual_edit')
                           ORDER BY created_at DESC LIMIT 100""", (user_id,),
                    )
                    rows = cur.fetchall()
                    for row in rows:
                        metadata = row.get("metadata") or {}
                        signals = set(metadata.get("style_signals") or [])
                        signals.update(infer_style_signals_from_edit(metadata))
                        signals.update(extract_style_signals(" ".join([
                            str(row.get("instruction") or ""), str(row.get("change_summary") or ""),
                        ])))
                        for signal in signals & counts.keys():
                            counts[signal] += 1
                    stable = [name for name, count in counts.items() if count >= 2]
                    if not stable:
                        cur.execute("""UPDATE a12_teacher_style_profile SET profile =
                            COALESCE(profile, '{}'::jsonb) || %s::jsonb WHERE user_id=%s""",
                            (json.dumps({"last_relearn_at": datetime.now(timezone.utc).isoformat()}), user_id))
                        conn.commit()
                        return {"updated": False, "evidence_count": len(rows), "stable_preferences": []}
                    summary = "；".join(STYLE_SIGNALS[name][0] for name in stable)
                    cur.execute(
                        """INSERT INTO a12_teacher_style_profile
                           (user_id,style_summary,profile,evidence_count,confidence)
                           VALUES (%s,%s,%s::jsonb,%s,%s)
                           ON CONFLICT (user_id) DO UPDATE SET
                             style_summary=EXCLUDED.style_summary,
                             profile=a12_teacher_style_profile.profile || EXCLUDED.profile,
                             evidence_count=EXCLUDED.evidence_count,
                             confidence=EXCLUDED.confidence,updated_at=NOW()""",
                        (user_id, summary, json.dumps({"style_preferences": stable,
                          "last_relearn_at": datetime.now(timezone.utc).isoformat()}, ensure_ascii=False),
                         len(rows), min(0.9, 0.5 + len(rows) * 0.01)),
                    )
                conn.commit()
            return {"updated": True, "evidence_count": len(rows), "stable_preferences": stable}
        except Exception:
            self.available = False
            return {"updated": False, "error": "教师反馈数据库暂时不可用"}

    def record_feedback(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Store explicit/implicit teacher feedback and update a bounded preference summary."""
        user_id = str(payload.get("user_id") or "").strip()
        action = str(payload.get("action") or "").strip()
        metadata = dict(payload.get("metadata") or {})
        metadata.pop("style_signals", None)
        signals = list(dict.fromkeys([
            *extract_style_signals(" ".join([str(payload.get("instruction") or ""),
                                            str(payload.get("change_summary") or "")])),
            *infer_style_signals_from_edit(metadata),
        ]))
        if signals and action in {"accept", "manual_edit"}:
            metadata["style_signals"] = signals
        saved = self._execute(
            """INSERT INTO a12_ai_feedback
              (user_id,session_id,project_id,action,target_type,instruction,change_summary,before_data,after_data,metadata)
              VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb)""",
            (user_id, payload.get("session_id"), payload.get("project_id"), action,
             payload.get("target_type") or "presentation", payload.get("instruction"),
             payload.get("change_summary"), json.dumps(payload.get("before_data") or {}, ensure_ascii=False, default=_json_default),
             json.dumps(payload.get("after_data") or {}, ensure_ascii=False, default=_json_default), json.dumps(metadata, ensure_ascii=False, default=_json_default)),
        )
        # A single edit can be task-specific. Only repeat signals promote to
        # long-term preference; rejection stays negative evidence.
        repeated: list[str] = []
        if saved and signals and action in {"accept", "manual_edit"}:
            try:
                import psycopg
                from psycopg.rows import dict_row
                with psycopg.connect(self.settings.postgres_dsn, row_factory=dict_row) as conn:
                    with conn.cursor() as cur:
                        cur.execute("""SELECT metadata FROM a12_ai_feedback WHERE user_id=%s
                            AND action IN ('accept','manual_edit') ORDER BY created_at DESC LIMIT 20""", (user_id,))
                        evidence = [dict(row.get("metadata") or {}) for row in cur.fetchall()]
                repeated = [signal for signal in signals if sum(signal in row.get("style_signals", []) for row in evidence) >= 2]
            except Exception:
                self.available = False
        profile_saved = False
        if saved and repeated:
            preference = {
                "style_preferences": repeated,
                "last_positive_action": action,
                "last_change_summary": str(payload.get("change_summary") or "")[:500],
                "last_instruction": str(payload.get("instruction") or "")[:500],
                "subject": metadata.get("subject"), "grade": metadata.get("grade"),
            }
            profile_saved = self._execute(
                """INSERT INTO a12_teacher_style_profile(user_id,style_summary,profile,evidence_count,confidence)
                   VALUES (%s,%s,%s::jsonb,1,0.55)
                   ON CONFLICT(user_id) DO UPDATE SET profile=a12_teacher_style_profile.profile || EXCLUDED.profile,
                   style_summary=EXCLUDED.style_summary,evidence_count=a12_teacher_style_profile.evidence_count+1,
                   confidence=LEAST(0.98, a12_teacher_style_profile.confidence + 0.03),updated_at=NOW()""",
                (user_id, "；".join(STYLE_SIGNALS[name][0] for name in repeated),
                 json.dumps(preference, ensure_ascii=False, default=_json_default)),
            )
        return {"stored": bool(saved), "action": action, "profile_updated": bool(profile_saved),
                "style_signals": signals}

    def ai_metrics(self, limit: int = 50, user_id: str | None = None) -> dict[str, Any]:
        try:
            import psycopg
            from psycopg.rows import dict_row
            with psycopg.connect(self.settings.postgres_dsn, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    run_scope = "WHERE user_id = %s" if user_id else ""
                    feedback_scope = "WHERE user_id = %s" if user_id else ""
                    cur.execute("""SELECT operation,status,model,COUNT(*) runs,
                              ROUND(AVG(latency_ms)) avg_latency_ms,SUM(input_tokens) input_tokens,
                              SUM(output_tokens) output_tokens
                              FROM a12_ai_run_log {scope} GROUP BY operation,status,model ORDER BY runs DESC LIMIT %s"""
                                .replace("{scope}", run_scope), ((user_id,) if user_id else ()) + (limit,))
                    runs = [dict(row) for row in cur.fetchall()]
                    cur.execute(f"SELECT action, COUNT(*) count FROM a12_ai_feedback {feedback_scope} GROUP BY action ORDER BY count DESC",
                                (user_id,) if user_id else ())
                    feedback = [dict(row) for row in cur.fetchall()]
            return {"runs": runs, "feedback": feedback, "postgres_available": True}
        except Exception as exc:
            self.available = False
            return {"runs": [], "feedback": [], "postgres_available": False, "error": str(exc)[:300]}

    def record_classroom_event(self, payload: dict[str, Any]) -> bool:
        return self._execute("""INSERT INTO a12_classroom_event
          (user_id,project_id,session_id,student_key,event_type,question_id,answer,correct,response_ms,metadata)
          VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)""", (
            payload.get("user_id"), payload.get("project_id"), payload.get("session_id"),
            payload.get("student_key"), payload.get("event_type"), payload.get("question_id"),
            payload.get("answer"), payload.get("correct"), payload.get("response_ms"),
            json.dumps(payload.get("metadata") or {}, ensure_ascii=False, default=_json_default),
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
