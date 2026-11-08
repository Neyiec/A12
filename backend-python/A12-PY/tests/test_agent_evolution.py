import asyncio
import hashlib
import json
import os
from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock, patch

import httpx
import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row
import pytest

from a12_ppt import agent_evolution as evolution
from a12_ppt import database


@pytest.fixture
def isolated_evolution(monkeypatch):
    dsn = os.getenv("A12_TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("Set A12_TEST_POSTGRES_DSN to run isolated PostgreSQL evolution integration")
    schema = "test_evolution_" + uuid4().hex
    with psycopg.connect(dsn, connect_timeout=3) as conn:
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    scoped = make_conninfo(dsn, options="-c search_path=" + schema)
    monkeypatch.setattr(database, "get_settings", lambda: SimpleNamespace(postgres_dsn=scoped))
    monkeypatch.setattr(evolution, "connect", lambda: psycopg.connect(scoped, row_factory=dict_row))
    try:
        assert database.ensure_ai_schema()
        yield True
    finally:
        with psycopg.connect(dsn, connect_timeout=3) as conn:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def seed_feedback():
    with evolution.connect() as conn:
        for index in range(5):
            conn.execute("""INSERT INTO a12_ai_feedback(user_id,project_id,action,instruction,metadata)
                VALUES (%s,%s,'manual_edit','PRIVATE CONTENT',%s::jsonb)""",
                ("teacher-" + str(index % 2), str(index), json.dumps({"style_signals": ["less_slide_text"]})))


def test_candidate_gray_evaluation_promotion_and_rollback(isolated_evolution):
    baseline = evolution.dashboard()["release"]
    seed_feedback()
    candidate = evolution.derive_candidate("admin")
    assert "PRIVATE CONTENT" not in candidate["instruction"]
    assert candidate["evidence"]["less_slide_text"] == {"units": 5, "teachers": 2}
    with pytest.raises(ValueError, match="人工确认"):
        evolution.change_release("canary", baseline["revision"], candidate["id"], 10, "admin", "test")
    evolution.approve(candidate["id"], "admin")
    release = evolution.change_release("canary", baseline["revision"], candidate["id"], 10, "admin", "test")
    with pytest.raises(ValueError, match="至少 5"):
        evolution.change_release("promote", release["revision"], None, 10, "admin", "test")
    recorded = {"control": 0, "canary": 0}
    index = 0
    while min(recorded.values()) < 5:
        user = "cohort-" + str(index)
        index += 1
        cohort = "canary" if int(hashlib.sha256(f"{user}:{release['revision']}".encode()).hexdigest()[:8], 16) % 100 < 10 else "control"
        if recorded[cohort] >= 5:
            continue
        run = evolution.begin_run(user, "test-theme")
        assert run["cohort"] == cohort
        evolution.finish_run(run["prompt_run_id"], True)
        if cohort == "control":
            evolution.record_outcome(user, run["prompt_run_id"], "revision", "edit-1")
            evolution.record_outcome(user, run["prompt_run_id"], "export_failed", "export-1")
        assert not evolution.record_outcome("other-user", run["prompt_run_id"], "accept", "spoof")
        assert evolution.record_outcome(user, run["prompt_run_id"], "export_success", "export-2")
        assert not evolution.record_outcome(user, run["prompt_run_id"], "export_success", "export-2")
        recorded[cohort] += 1
    metrics = {row["cohort"]: row for row in evolution.effects(release["revision"])}
    assert metrics["control"]["first_pass"] == 0
    assert metrics["canary"]["first_pass"] == 5
    assert metrics["control"]["adopted"] == metrics["canary"]["adopted"] == 5
    assert metrics["control"]["revision_rounds"] == 5
    promoted = evolution.change_release("promote", release["revision"], None, 10, "admin", "better export results")
    assert promoted["active_version"] == candidate["id"]
    with pytest.raises(ValueError, match="状态已变化"):
        evolution.change_release("rollback", release["revision"], baseline["active_version"], 10, "admin", "stale")
    restored = evolution.change_release("rollback", promoted["revision"], baseline["active_version"], 10, "admin", "rollback test")
    assert restored["active_version"] == baseline["active_version"]


def test_recent_feedback_is_teacher_scoped_and_respects_pause(isolated_evolution):
    seed_feedback()
    assert evolution.recent_guidance("teacher-0")
    assert not evolution.recent_guidance("other-teacher")
    with evolution.connect() as conn:
        conn.execute("""INSERT INTO a12_teacher_style_profile(user_id,profile)
            VALUES ('teacher-0','{"enabled":false}')""")
    assert not evolution.recent_guidance("teacher-0")


def test_evolution_api_enforces_admin_and_serializes_metrics(isolated_evolution):
    from main import app

    async def probe():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            headers = {"Authorization": "Bearer test-token"}
            with patch("main.verify_active_token", new_callable=AsyncMock), \
                 patch("main.authenticate_browser", new_callable=AsyncMock, return_value=("7", "test-token", "teacher")):
                assert (await client.get("/api/v1/python/agent-evolution", headers=headers)).status_code == 403
            with patch("main.verify_active_token", new_callable=AsyncMock), \
                 patch("main.authenticate_browser", new_callable=AsyncMock, return_value=("7", "test-token", "admin")):
                result = await client.get("/api/v1/python/agent-evolution", headers=headers)
                assert result.status_code == 200
                assert result.json()["data"]["release"]["active_version"]
                failed = await client.post("/api/v1/python/agent-evolution/candidates", headers=headers, json={})
                assert failed.status_code == 409
    asyncio.run(probe())


def test_template_snapshot_is_pinned_and_rollback_restores_it(isolated_evolution, monkeypatch):
    monkeypatch.setattr(evolution, 'template_snapshot', lambda: {'test': {'html': 'old'}})
    baseline = evolution.begin_run('teacher', 'test')
    monkeypatch.setattr(evolution, 'template_snapshot', lambda: {'test': {'html': 'new'}})
    candidate = evolution.derive_candidate('admin', template_update=True)
    assert candidate['template_bundle']['test']['html'] == 'new'
    evolution.approve(candidate['id'], 'admin')
    release = evolution.change_release('canary', 1, candidate['id'], 20, 'admin', 'template experiment')
    # 同轮次、同教师分组不变，外部模板更新不改变该轮版本快照。
    first = evolution.begin_run('teacher', 'test')
    second = evolution.begin_run('teacher', 'test')
    assert (first['cohort'], first['prompt_version']) == (second['cohort'], second['prompt_version'])
    restored = evolution.change_release('rollback', release['revision'], baseline['prompt_version'], 10, 'admin', 'restore')
    assert restored['active_version'] == baseline['prompt_version']
    assert evolution.begin_run('teacher', 'test')['template_bundle']['test']['html'] == 'old'


def test_sse_and_export_api_attribute_real_database_outcomes(isolated_evolution, tmp_path):
    import main

    @asynccontextmanager
    async def admission(*args, **kwargs):
        job = SimpleNamespace(completed_pages=0, update=AsyncMock())
        yield job

    observed = []
    async def stream(request):
        metadata = evolution.public_run_metadata()
        observed.append(metadata)
        assert metadata['prompt_run_id'] and metadata['prompt_version']
        yield {'type': 'slide', 'slide': {'slide_no': 1, 'html': '<html>test</html>', 'metadata': metadata}}
        yield {'type': 'final', 'response': {'title': 'test', 'slides': [], 'metadata': metadata}}

    artifact = tmp_path / 'test.pptx'
    artifact.write_bytes(b'export-test')
    async def probe():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url='http://test') as client:
            headers = {'Authorization': 'Bearer test-token'}
            with patch('main.verify_active_token', new_callable=AsyncMock), \
                 patch('main.authenticate_browser', new_callable=AsyncMock, return_value=('7', 'test-token', 'teacher')), \
                 patch('main.limit_job', admission), \
                 patch.object(main.generator, 'stream_presentation', stream):
                response = await client.post('/api/v1/python/presentations/generate/stream', headers=headers,
                                             json={'title': 'test', 'outline': {'slides': [{'title': 'test'}]}})
                assert response.status_code == 200 and 'event: done' in response.text
                run_id = observed[0]['prompt_run_id']
                with evolution.connect() as conn:
                    assert conn.execute('SELECT status FROM a12_prompt_run WHERE id=%s', (run_id,)).fetchone()['status'] == 'success'
                payload = {'title': 'test', 'slides': [{'html': '<html>test</html>', 'metadata': {'prompt_run_id': run_id}}]}
                with patch('main.export_html_slides_to_pptx', new_callable=AsyncMock, return_value=artifact):
                    result = await client.post('/api/v1/python/presentations/export/pptx', headers=headers, json=payload)
                    assert result.status_code == 200 and result.content == b'export-test'
                from fastapi import HTTPException
                with patch('main.export_html_slides_to_pptx', new_callable=AsyncMock, side_effect=HTTPException(503, 'export unavailable')):
                    result = await client.post('/api/v1/python/presentations/export/pptx', headers=headers, json=payload)
                    assert result.status_code == 503
                # 同一运行号属于教师 7，教师 8 不能给它记采纳或导出结果。
                with patch('main.authenticate_browser', new_callable=AsyncMock, return_value=('8', 'test-token', 'teacher')), \
                     patch('main.export_html_slides_to_pptx', new_callable=AsyncMock, return_value=artifact):
                    assert (await client.post('/api/v1/python/presentations/export/pptx', headers=headers, json=payload)).status_code == 200
                row = evolution.effects()[0]
                assert row['generated'] == row['adopted'] == row['first_pass'] == 1
                assert row['exports'] == 2 and row['exports_ok'] == 1
                assert not evolution.current_policy()
    asyncio.run(probe())


def test_failed_generation_does_not_count_as_success(isolated_evolution):
    async def probe():
        with pytest.raises(RuntimeError):
            async with evolution.prompt_session('teacher', 'test'):
                raise RuntimeError('model unavailable')
        assert not evolution.current_policy()
        row = evolution.effects()[0]
        assert row['attempts'] == 1 and row['generated'] == row['adopted'] == 0
    asyncio.run(probe())


def test_second_generation_reads_feedback_and_selected_prompt_version(isolated_evolution):
    from a12_ppt.direct_auth import direct_user_id
    from a12_ppt.models import PresentationGenerateRequest
    from a12_ppt.presentation import PPTGenerator
    from a12_ppt.presentation.prompts import slide_html_prompt
    html = '<!doctype html><html><body><section>教学内容</section></body></html>'
    seed_feedback()
    flow = PPTGenerator.__new__(PPTGenerator)
    flow.settings = SimpleNamespace(max_slide_concurrency=1, enable_quality_pipeline=False,
                                    quality_preset='fast', max_html_retries=1, max_generated_images=0)
    flow.llm = SimpleNamespace(available=False)
    flow.image_generator = SimpleNamespace(available=False)
    prompts = []
    async def page(**kwargs):
        context = kwargs['request_context']
        assert context['recent_teacher_feedback']
        assert context['generation_policy']['instruction'] == '教学策略灰度测试'
        prompt_args = {key: value for key, value in kwargs.items() if key != 'quality_assets'}
        prompt = slide_html_prompt(**prompt_args, style_genes='', global_constitution='', page_brief='')
        assert '必须保留教师指定公式' in prompt
        assert '精简学生主画面' in prompt
        assert '教学策略灰度测试' in prompt
        assert '只输出完整 HTML' in prompt
        prompts.append(prompt)
        return html
    flow._generate_slide_html = page
    async def probe():
        identity = direct_user_id.set('teacher-0')
        try:
            with evolution.connect() as conn:
                conn.execute("UPDATE a12_prompt_version SET instruction='教学策略灰度测试'")
            with patch('a12_ppt.outline_chat.postgres_store.postgres_memory_store.refresh_teacher_profile', return_value={'enabled': True}), \
                 patch('a12_ppt.direct_auth.require_active_browser_token', new_callable=AsyncMock):
                async with evolution.prompt_session('teacher-0', '素白风'):
                    request = PresentationGenerateRequest(title='test', asset_policy='none',
                        outline={'requirements': '必须保留教师指定公式', 'slides': [{'title': '第一页'}]})
                    events = [event async for event in flow.stream_presentation(request)]
                    assert events[-1]['response']['metadata']['prompt_run_id']
                    assert events[0]['slide']['metadata']['prompt_run_id']
        finally:
            direct_user_id.reset(identity)
        assert len(prompts) == 1
    asyncio.run(probe())
