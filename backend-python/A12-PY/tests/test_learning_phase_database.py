"""显式启用的真实PostgreSQL回归，仅清理本测试随机用户的数据。"""
import asyncio
import os
import unittest
import uuid
from a12_ppt.database import ensure_ai_schema
from a12_ppt.course_graph import course_graph_store, GraphVersionConflict
from a12_ppt.learning_video import video_job_store


@unittest.skipUnless(os.getenv("A12_TEST_DATABASE") == "1", "设置A12_TEST_DATABASE=1启用数据库集成回归")
class LearningDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.user_id = "test_phase2_" + uuid.uuid4().hex
        self.assertTrue(ensure_ai_schema())

    def tearDown(self):
        with course_graph_store._connect() as conn, conn.cursor() as cur:
            for table in ("a12_learning_video_job", "a12_course_graph_version", "a12_graph_evidence", "a12_course_graph"):
                cur.execute(f"DELETE FROM {table} WHERE user_id=%s", (self.user_id,))

    def test_graph_versions_optimistic_lock_and_restore(self):
        data = {"nodes": [{"id": "k1", "label": "知识点", "kind": "concept"}], "edges": []}
        first = course_graph_store.put(self.user_id, "test", "测试课程", data, 0)
        self.assertEqual(first["version"], 1)
        with self.assertRaises(GraphVersionConflict):
            course_graph_store.put(self.user_id, "test", "冲突", data, 0)
        second = course_graph_store.put(self.user_id, "test", "新版", data, 1)
        self.assertEqual(second["version"], 2)
        old = course_graph_store.get_version(self.user_id, "test", 1)
        restored = course_graph_store.put(self.user_id, "test", old["title"], old, 2)
        self.assertEqual(restored["version"], 3)
        self.assertEqual(len(course_graph_store.versions(self.user_id, "test")), 3)
        self.assertIsNone(course_graph_store.get("different_teacher", "test"))

    def test_video_active_quota_lease_cancel_and_bounded_retry(self):
        payload = {"title": "回归测试", "slides": [{"html": "<html>test</html>", "narration": "测试"}]}
        jobs = [video_job_store.create(self.user_id, payload) for _ in range(3)]
        with self.assertRaises(ValueError): video_job_store.create(self.user_id, payload)
        self.assertTrue(video_job_store.cancel(self.user_id, jobs[1]["job_id"]))
        job_id = jobs[0]["job_id"]
        with course_graph_store._connect() as conn, conn.cursor() as cur:
            cur.execute("UPDATE a12_learning_video_job SET status='running',attempts=1,lease_id='test-lease' WHERE user_id=%s AND job_id=%s", (self.user_id, job_id))
        video_job_store.update(job_id, 50, lease_id="test-lease")
        with self.assertRaises(asyncio.CancelledError): video_job_store.update(job_id, 100, lease_id="wrong-lease")
        video_job_store.update(job_id, 0, error="测试失败", lease_id="test-lease")
        self.assertTrue(video_job_store.retry(self.user_id, job_id))
        with course_graph_store._connect() as conn, conn.cursor() as cur:
            cur.execute("UPDATE a12_learning_video_job SET status='failed',attempts=2 WHERE user_id=%s AND job_id=%s", (self.user_id, job_id))
        self.assertFalse(video_job_store.retry(self.user_id, job_id))
        self.assertIsNone(video_job_store.get("different_teacher", job_id))
