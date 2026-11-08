"""Teacher-scoped prompt releases with human approval and attributable outcomes."""
import asyncio
import hashlib
import json
import logging
from contextlib import asynccontextmanager
from contextvars import ContextVar
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row

from .config import get_settings
from .ai_runtime import current_runtime

logger = logging.getLogger(__name__)
_policy = ContextVar("a12_prompt_policy", default={})
SUGGESTIONS = {
    "less_slide_text": "精简学生主画面中的重复表述，保留关键定义、公式和任务要求，详细解释放入讲解备注。",
    "more_cases": "在适合的知识点安排贴合学生经验的具体案例，并说明案例与概念的对应关系。",
    "more_practice": "为重要知识点安排可检查结果的课堂练习，明确学生任务与反馈方式。",
    "less_theory": "以具体问题和案例承接理论说明，保留必要的原理与适用条件。",
    "boppps": "在适用场景中明确导入、目标、前测、参与式学习、后测与总结的衔接。",
}


def connect():
    return psycopg.connect(get_settings().postgres_dsn, row_factory=dict_row, connect_timeout=3)


def current_policy():
    return _policy.get()


def template_snapshot():
    from .presentation.template_store import load_templates
    return {value["_file_theme"]: value for value in load_templates().values()}


def public_run_metadata():
    policy = current_policy()
    return {key: policy[key] for key in ("prompt_run_id", "prompt_version", "release_revision", "cohort") if key in policy}


def begin_run(user_id, theme):
    with connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM a12_prompt_release WHERE id=1")
        release = cur.fetchone()
        bucket = int(hashlib.sha256(f"{user_id}:{release['revision']}".encode()).hexdigest()[:8], 16) % 100
        canary = release["canary_version"] is not None and bucket < release["canary_percent"]
        version = release["canary_version"] if canary else release["active_version"]
        cur.execute("SELECT * FROM a12_prompt_version WHERE id=%s AND approved_by IS NOT NULL", (version,))
        policy = dict(cur.fetchone())
        if not policy["template_bundle"]:
            bundle = json.dumps(template_snapshot(), ensure_ascii=False)
            cur.execute("""UPDATE a12_prompt_version SET template_bundle=%s::jsonb
                WHERE id=%s AND template_bundle='{}'::jsonb""", (bundle, version))
            cur.execute("SELECT template_bundle FROM a12_prompt_version WHERE id=%s", (version,))
            policy["template_bundle"] = cur.fetchone()["template_bundle"]
        run_id = uuid4().hex
        cohort = "canary" if canary else "control"
        cur.execute("""INSERT INTO a12_prompt_run
            (id,user_id,version_id,release_revision,cohort,runtime_run_id,theme)
            VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (run_id, user_id, version, release["revision"], cohort, current_runtime().run_id, theme))
    return {"prompt_run_id": run_id, "prompt_version": version, "release_revision": release["revision"],
            "cohort": cohort, "instruction": policy["instruction"], "layout_rule": policy["layout_rule"],
            "template_bundle": policy["template_bundle"]}


@asynccontextmanager
async def prompt_session(user_id, theme):
    policy = {}
    if user_id:
        try:
            policy = await asyncio.to_thread(begin_run, user_id, theme)
        except psycopg.Error:
            logger.warning("Prompt release store unavailable; using built-in generation policy")
    token = _policy.set(policy)
    completed = False
    try:
        yield policy
        completed = True
    finally:
        _policy.reset(token)
        if policy:
            try:
                await asyncio.to_thread(finish_run, policy["prompt_run_id"], completed, policy.get("runtime_run_id"),
                                        policy.get("template_sha256"))
            except psycopg.Error:
                logger.warning("Prompt run outcome could not be recorded")


def finish_run(run_id, success, runtime_run_id=None, template_sha256=None):
    with connect() as conn:
        conn.execute("""UPDATE a12_prompt_run SET status=%s,completed_at=NOW(),
            runtime_run_id=COALESCE(NULLIF(%s,''),runtime_run_id),template_sha256=%s WHERE id=%s""",
                     ("success" if success else "failed", runtime_run_id, template_sha256, run_id))


def record_outcome(user_id, run_id, action, event_key, *, project_id=None):
    if not run_id:
        return False
    with connect() as conn:
        result = conn.execute("""INSERT INTO a12_prompt_outcome(run_id,action,event_key,project_id)
            SELECT id,%s,%s,%s FROM a12_prompt_run WHERE id=%s AND user_id=%s AND status='success'
            ON CONFLICT(run_id,event_key) DO NOTHING""", (action, event_key, project_id, run_id, user_id))
        return result.rowcount > 0


def recent_guidance(user_id):
    with connect() as conn:
        profile = conn.execute("SELECT profile FROM a12_teacher_style_profile WHERE user_id=%s", (user_id,)).fetchone()
        if profile and (profile["profile"] or {}).get("enabled") is False:
            return []
        rows = conn.execute("""SELECT metadata FROM a12_ai_feedback WHERE user_id=%s
            AND action IN ('accept','manual_edit') AND created_at >= NOW()-INTERVAL '30 days'
            ORDER BY created_at DESC,id DESC LIMIT 20""", (user_id,)).fetchall()
    signals = []
    for row in rows:
        for signal in (row["metadata"] or {}).get("style_signals", []):
            if signal in SUGGESTIONS and signal not in signals:
                signals.append(signal)
    return [SUGGESTIONS[signal] for signal in signals[:3]]


def effects(revision=None):
    with connect() as conn:
        return conn.execute("""WITH outcomes AS (
          SELECT run_id, BOOL_OR(action IN ('accept','export_success')) AS accepted,
            MIN(created_at) FILTER (WHERE action='export_success') AS first_export,
            MIN(created_at) FILTER (WHERE action='export_failed') AS first_failure,
            MIN(created_at) FILTER (WHERE action='revision') AS first_revision,
            COUNT(*) FILTER (WHERE action='revision') AS revision_rounds,
            COUNT(*) FILTER (WHERE action='export_success') AS exports_ok,
            COUNT(*) FILTER (WHERE action IN ('export_success','export_failed')) AS exports
          FROM a12_prompt_outcome GROUP BY run_id)
        SELECT r.version_id,r.cohort,COUNT(*) AS attempts,
          COUNT(*) FILTER (WHERE r.status='success') AS generated,
          COUNT(*) FILTER (WHERE r.status='success' AND o.accepted) AS adopted,
          COUNT(*) FILTER (WHERE r.status='success' AND o.first_export IS NOT NULL
            AND (o.first_failure IS NULL OR o.first_failure > o.first_export)
            AND (o.first_revision IS NULL OR o.first_revision > o.first_export)) AS first_pass,
          COUNT(*) FILTER (WHERE r.status='success' AND o.first_export IS NOT NULL) AS exported_runs,
          COALESCE(SUM(o.exports_ok),0) AS exports_ok,COALESCE(SUM(o.exports),0) AS exports,
          COALESCE(SUM(o.revision_rounds),0) AS revision_rounds
        FROM a12_prompt_run r LEFT JOIN outcomes o ON o.run_id=r.id
        WHERE (%s::int IS NULL OR r.release_revision=%s)
          AND r.created_at >= NOW()-INTERVAL '90 days'
        GROUP BY r.version_id,r.cohort ORDER BY r.version_id DESC""", (revision, revision)).fetchall()


def dashboard():
    with connect() as conn:
        release = conn.execute("SELECT * FROM a12_prompt_release WHERE id=1").fetchone()
        versions = conn.execute("""SELECT id,name,instruction,layout_rule,evidence,approved_by,
            created_at,(SELECT COUNT(*) FROM jsonb_object_keys(template_bundle)) AS template_count
            FROM a12_prompt_version ORDER BY id DESC LIMIT 50""").fetchall()
        history = conn.execute("SELECT * FROM a12_prompt_release_history ORDER BY id DESC LIMIT 20").fetchall()
    return {"release": release, "versions": versions, "history": history, "effects": effects(release["revision"])}


def derive_candidate(actor, template_update=False):
    # 聚类仅使用系统支持的风格信号，同一项目最多计一次，避免把教师私有文本发布为全局策略。
    with connect() as conn:
        rows = conn.execute("""SELECT user_id,project_id,session_id,metadata FROM a12_ai_feedback
            WHERE action IN ('accept','manual_edit') AND created_at >= NOW()-INTERVAL '90 days'
            ORDER BY created_at DESC LIMIT 2000""").fetchall()
        release = conn.execute("SELECT * FROM a12_prompt_release WHERE id=1").fetchone()
        clusters = {key: set() for key in SUGGESTIONS}
        teachers = {key: set() for key in SUGGESTIONS}
        for row in rows:
            unit = row["project_id"] or row["session_id"]
            if not unit:
                continue
            for signal in (row["metadata"] or {}).get("style_signals", []):
                if signal in clusters:
                    clusters[signal].add((row["user_id"], unit))
                    teachers[signal].add(row["user_id"])
        selected = [key for key in SUGGESTIONS if len(clusters[key]) >= 5 and len(teachers[key]) >= 2]
        if not selected and not template_update:
            raise ValueError("至少需要 2 位教师、5 个独立项目或会话的相同反馈，才能生成候选")
        instruction = "\n".join(SUGGESTIONS[key] for key in selected[:3])
        evidence = {key: {"units": len(clusters[key]), "teachers": len(teachers[key])} for key in selected[:3]}
        if template_update:
            active = conn.execute("SELECT instruction FROM a12_prompt_version WHERE id=%s", (release["active_version"],)).fetchone()
            instruction = active["instruction"]
            evidence = {}
        bundle = json.dumps(template_snapshot(), ensure_ascii=False, sort_keys=True)
        fingerprint = hashlib.sha256(f"{release['active_version']}:{instruction}:{bundle}".encode()).hexdigest()
        return conn.execute("""INSERT INTO a12_prompt_version
            (name,instruction,layout_rule,evidence,parent_version,created_by,fingerprint,template_bundle)
            VALUES (%s,%s,%s,%s::jsonb,%s,%s,%s,%s::jsonb) ON CONFLICT(fingerprint) DO UPDATE
            SET fingerprint=EXCLUDED.fingerprint RETURNING *""",
            ("模板更新候选" if template_update else "反馈聚类候选", instruction, "每页围绕一个核心任务组织内容，保留必要的定义、公式和来源标注。",
             json.dumps(evidence), release["active_version"], actor, fingerprint, bundle)).fetchone()


def approve(version_id, actor):
    with connect() as conn:
        row = conn.execute("""UPDATE a12_prompt_version SET approved_by=%s,approved_at=NOW()
            WHERE id=%s AND approved_by IS NULL RETURNING id""", (actor, version_id)).fetchone()
        if not row:
            raise ValueError("候选不存在或已确认")


def change_release(action, expected_revision, version_id, percent, actor, reason):
    if not reason.strip():
        raise ValueError("请填写发布或回滚原因")
    with connect() as conn:
        current = conn.execute("SELECT * FROM a12_prompt_release WHERE id=1 FOR UPDATE").fetchone()
        if current["revision"] != expected_revision:
            raise ValueError("发布状态已变化，请刷新后重试")
        active, canary, ratio = current["active_version"], current["canary_version"], current["canary_percent"]
        if action == "canary":
            if percent not in (5, 10, 20) or version_id == active:
                raise ValueError("请选择候选版本及 5%、10% 或 20% 灰度比例")
            approved = conn.execute("SELECT id FROM a12_prompt_version WHERE id=%s AND approved_by IS NOT NULL", (version_id,)).fetchone()
            if not approved:
                raise ValueError("候选必须先人工确认")
            if canary is not None:
                raise ValueError("已有灰度试验，请先结束当前试验")
            canary, ratio = version_id, percent
        elif action == "promote":
            if canary is None:
                raise ValueError("没有正在灰度的候选")
            groups = {row["cohort"]: row for row in effects(current["revision"])}
            if not all(key in groups and groups[key]["exported_runs"] >= 5 for key in ("control", "canary")):
                raise ValueError("对照组和灰度组各需至少 5 份已导出的课件")
            control, trial = groups["control"], groups["canary"]
            cpass, tpass = control["exports_ok"]/control["exports"], trial["exports_ok"]/trial["exports"]
            crev, trev = control["revision_rounds"]/control["generated"], trial["revision_rounds"]/trial["generated"]
            if tpass < cpass or trev > crev or not (tpass > cpass or trev < crev):
                raise ValueError("候选尚未在导出通过率或平均修改轮次上取得改善")
            active, canary, ratio = canary, None, 0
        elif action == "rollback":
            known = conn.execute("""SELECT 1 FROM a12_prompt_release_history
                WHERE before_state->>'active_version'=%s OR after_state->>'active_version'=%s LIMIT 1""",
                (str(version_id), str(version_id))).fetchone()
            if not known or not conn.execute("SELECT 1 FROM a12_prompt_version WHERE id=%s AND approved_by IS NOT NULL", (version_id,)).fetchone():
                raise ValueError("只能回滚到曾经正式使用的已确认版本")
            active, canary, ratio = version_id, None, 0
        elif action == "stop":
            canary, ratio = None, 0
        else:
            raise ValueError("不支持的发布操作")
        updated = conn.execute("""UPDATE a12_prompt_release SET active_version=%s,canary_version=%s,
            canary_percent=%s,revision=revision+1,updated_at=NOW() WHERE id=1 RETURNING *""",
            (active, canary, ratio)).fetchone()
        conn.execute("""INSERT INTO a12_prompt_release_history(actor,action,reason,before_state,after_state)
            VALUES (%s,%s,%s,%s::jsonb,%s::jsonb)""",
            (actor, action, reason, json.dumps(current, default=str), json.dumps(updated, default=str)))
        return updated
