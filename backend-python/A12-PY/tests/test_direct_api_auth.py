import os
import json
import tempfile
import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import HTTPException

from a12_ppt.direct_auth import direct_user_id


class DirectApiAuthTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from main import app

        self.redis_guard = patch("main.verify_active_token", new_callable=AsyncMock)
        self.redis_guard.start()
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver")

    async def asyncTearDown(self):
        await self.client.aclose()
        self.redis_guard.stop()

    async def test_browser_requires_token_and_cors_exposes_unauthorized(self):
        response = await self.client.get("/api/v1/python/health", headers={"Origin": "http://localhost:5173"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://localhost:5173")

    async def test_browser_token_and_identity_checks(self):
        async def authenticated(_authorization):
            return "7", "valid-token"

        with patch("main.authenticate_browser", side_effect=authenticated):
            allowed = await self.client.get("/api/v1/python/health", headers={"Authorization": "Bearer valid-token"})
            self.assertEqual(allowed.status_code, 200)
            query_spoof = await self.client.get("/api/v1/python/teacher-style/profile?user_id=8",
                                                headers={"Authorization": "Bearer valid-token"})
            self.assertEqual(query_spoof.status_code, 403)
            body_spoof = await self.client.post("/api/v1/python/workspace/chat/route",
                                                json={"user_id": "8", "messages": [{"role": "user", "content": "你好"}]},
                                                headers={"Authorization": "Bearer valid-token"})
            self.assertEqual(body_spoof.status_code, 403)
            admin_only = await self.client.post("/api/v1/python/templates", json={"name": "unauthorized"},
                                                headers={"Authorization": "Bearer valid-token"})
            self.assertEqual(admin_only.status_code, 403)

    async def test_teacher_feedback_uses_authenticated_identity_and_reports_storage_failure(self):
        headers = {"Authorization": "Bearer valid-token"}
        payload = {"session_id": "outline-1", "action": "accept", "target_type": "outline"}
        with patch("main.authenticate_browser", new_callable=AsyncMock, return_value=("7", "valid-token")), \
             patch("main.postgres_memory_store.record_feedback", return_value={"stored": True}) as record:
            response = await self.client.post("/api/v1/python/teacher-style/feedback", json=payload, headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(record.call_args.args[0]["user_id"], "7")
            record.return_value = {"stored": False}
            response = await self.client.post("/api/v1/python/teacher-style/feedback", json=payload, headers=headers)
            self.assertEqual(response.status_code, 503)

    async def test_replaced_token_is_rejected_before_python_route_runs(self):
        async def authenticated(_authorization):
            return "7", "old-token", "teacher"

        with patch("main.authenticate_browser", side_effect=authenticated), \
             patch("main.verify_active_token", new_callable=AsyncMock,
                   side_effect=HTTPException(status_code=401, detail="令牌已过期或已被替换")):
            response = await self.client.get("/api/v1/python/health",
                                             headers={"Authorization": "Bearer old-token"})
        self.assertEqual(response.status_code, 401)

    async def test_java_internal_key_is_required_and_never_a_browser_header(self):
        with patch.dict(os.environ, {"A12_PYTHON_INTERNAL_KEY": "test-only-secret"}):
            response = await self.client.get("/api/v1/python/health", headers={"X-A12-Internal-Key": "test-only-secret"})
            self.assertEqual(response.status_code, 200)
            wrong = await self.client.get("/api/v1/python/health", headers={"X-A12-Internal-Key": "wrong"})
            self.assertEqual(wrong.status_code, 401)

    async def test_admin_browser_can_call_python_template_api_without_java_proxy(self):
        async def authenticated(_authorization):
            return "7", "valid-token", "admin"

        with patch("main.authenticate_browser", side_effect=authenticated), \
                patch("main.create_template", return_value={"theme": "teaching-blue"}) as create:
            response = await self.client.post("/api/v1/python/templates",
                                              json={"name": "teaching-blue", "template_data": "{}"},
                                              headers={"Authorization": "Bearer valid-token"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["theme"], "teaching-blue")
        create.assert_called_once()

    async def test_stream_keeps_verified_identity_until_stream_finishes(self):
        from a12_ppt.direct_auth import direct_user_id

        async def authenticated(_authorization):
            return "7", "valid-token"

        async def streamed(_request):
            yield 'data: ' + str(direct_user_id.get()) + '\n\n'

        with patch("main.authenticate_browser", side_effect=authenticated), \
                patch("main.stream_workspace_chat", side_effect=streamed):
            response = await self.client.post("/api/v1/python/workspace/chat/stream",
                                              json={"user_id": "7", "messages": [{"role": "user", "content": "你好"}]},
                                              headers={"Authorization": "Bearer valid-token"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("data: 7", response.text)

    async def test_compact_ppt_stream_sends_html_once_and_keeps_validation_metadata(self):
        async def authenticated(_authorization):
            return "7", "valid-token", "teacher"

        async def generated(_request):
            page = {"slide_no": 1, "html": "<html>独立HTML页面</html>", "metadata": {"html_validation": {"valid": True}}}
            yield {"type": "slide", "slide": page, "completed": 1, "total": 1}
            yield {"type": "final", "response": {"slide_count": 1, "slides": [page], "html": "", "metadata": {}}}

        @asynccontextmanager
        async def admitted(*args, **kwargs):
            yield SimpleNamespace(completed_pages=0, update=AsyncMock())

        with patch("main.authenticate_browser", side_effect=authenticated), \
             patch("main.limit_job", side_effect=admitted), \
             patch("main.generator.stream_presentation", side_effect=generated):
            response = await self.client.post("/api/v1/python/presentations/generate/stream",
                json={"title":"函数","outline":{},"stream_compact":True}, headers={"Authorization":"Bearer valid-token"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text.count("独立HTML页面"), 1)
        blocks = response.text.split("\n\n")
        final = next(json.loads(block.split("data: ",1)[1]) for block in blocks if block.startswith("event: final"))
        self.assertTrue(final["stream_compact"])
        self.assertNotIn("html", final["slides"][0])
        self.assertTrue(final["slides"][0]["metadata"]["html_validation"]["valid"])

    async def test_resource_sync_uses_java_signed_url_not_browser_url(self):
        from unittest.mock import AsyncMock

        async def authenticated(_authorization):
            return "7", "valid-token"

        signed = AsyncMock(return_value="https://oss.example/signed")
        synced = AsyncMock(return_value={"status": "indexed"})
        with patch("main.authenticate_browser", side_effect=authenticated), \
                patch("main.signed_personal_resource_url", signed), \
                patch("main.resource_index_store.sync_resource", synced):
            response = await self.client.post("/api/v1/python/resources/index/sync", json={
                "source_type": "personal", "resource_id": "42", "title": "教材",
                "file_url": "https://attacker.example/file", "metadata": {},
            }, headers={"Authorization": "Bearer valid-token"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(synced.await_args.args[0].file_url, "https://oss.example/signed")
        self.assertEqual(synced.await_args.args[0].owner_user_id, "7")

    async def test_course_graph_api_is_scoped_to_logged_in_teacher(self):
        async def authenticated(_authorization):
            return "7", "valid-token"

        with patch("main.authenticate_browser", side_effect=authenticated), \
                patch("main.course_graph_store.put", return_value={"course_id": "java", "version": 1}) as put:
            denied = await self.client.put("/api/v1/python/courses/graph", json={
                "user_id": "8", "course_id": "java", "title": "Java", "nodes": [], "edges": []},
                headers={"Authorization": "Bearer valid-token"})
            self.assertEqual(denied.status_code, 403)
            allowed = await self.client.put("/api/v1/python/courses/graph", json={
                "user_id": "7", "course_id": "java", "title": "Java", "nodes": [{"id": "a", "label": "基础", "kind": "concept"}], "edges": []},
                headers={"Authorization": "Bearer valid-token"})
            self.assertEqual(allowed.status_code, 200)
            self.assertEqual(put.call_args.args[0], "7")


class IndexScopeTests(unittest.TestCase):
    def test_fallback_index_excludes_other_users_resources(self):
        from a12_ppt.resources.index_store import ResourceIndexStore

        store = object.__new__(ResourceIndexStore)
        store.available = False
        store.embedding_dimensions = 1024
        rows = {
            "personal:1": {"resource_key": "personal:1", "resource_id": "1", "source_type": "personal",
                           "metadata": {"owner_user_id": "7"}},
            "personal:2": {"resource_key": "personal:2", "resource_id": "2", "source_type": "personal",
                           "metadata": {"owner_user_id": "8"}},
            "public:3": {"resource_key": "public:3", "resource_id": "3", "source_type": "public", "metadata": {}},
        }
        store._read_fallback = lambda: {"resources": rows, "chunks": {key: [] for key in rows}}
        store.list_retrieval_logs = lambda _limit: {"total": 0}
        scoped = direct_user_id.set("7")
        try:
            result = store.list_resources()
            self.assertEqual({row["resource_key"] for row in result["items"]}, {"personal:1", "public:3"})
            self.assertIsNone(store.get_resource("personal", "2"))
            self.assertEqual(store.overview()["resource_count"], 2)
        finally:
            direct_user_id.reset(scoped)

    def test_local_upload_text_is_owner_scoped_and_rejects_path_traversal(self):
        from a12_ppt.resources import upload_store

        with tempfile.TemporaryDirectory() as directory, patch.object(upload_store, "DATA_DIR", Path(directory)):
            resource_id = "res_0123456789abcdef"
            resource_dir = Path(directory) / resource_id
            resource_dir.mkdir()
            (resource_dir / "metadata.json").write_text(json.dumps({"owner_user_id": "7"}), encoding="utf-8")
            (resource_dir / "content.txt").write_text("private lesson", encoding="utf-8")
            scope = direct_user_id.set("8")
            try:
                self.assertEqual(upload_store.load_resource_text(resource_id), "")
                self.assertEqual(upload_store.load_resource_text("../../secret"), "")
            finally:
                direct_user_id.reset(scope)
            scope = direct_user_id.set("7")
            try:
                self.assertEqual(upload_store.load_resource_text(resource_id), "private lesson")
            finally:
                direct_user_id.reset(scope)


if __name__ == "__main__":
    unittest.main()
