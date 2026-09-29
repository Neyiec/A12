import unittest
from unittest.mock import AsyncMock, patch

from a12_ppt.resources import index_worker


class _Response:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


class _Client:
    def __init__(self, response):
        self.response = response
        self.post = AsyncMock(return_value=_Response({"code": 200}))

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    async def get(self, *_args, **_kwargs):
        return self.response


class ResourceIndexWorkerTests(unittest.IsolatedAsyncioTestCase):
    async def test_deleted_resource_removes_index_without_java_lookup(self):
        with patch.object(index_worker.resource_index_store, "delete_resource") as deleted:
            await index_worker.process_event({"action": "delete", "source_type": "personal", "resource_id": "12"})
        deleted.assert_called_once_with("personal", "12")

    async def test_sync_reads_trusted_business_payload_and_reports_completion(self):
        payload = {
            "source_type": "public", "resource_id": "7", "title": "教材", "file_url": "https://oss.test/file",
            "available": True, "allow_ai": True, "metadata": {},
        }
        client = _Client(_Response({"code": 200, "data": payload}))
        with patch.dict("os.environ", {"A12_PYTHON_INTERNAL_KEY": "test-secret"}), \
             patch.object(index_worker.httpx, "AsyncClient", return_value=client), \
             patch.object(index_worker.resource_index_store, "sync_resource", new_callable=AsyncMock,
                          return_value={"status": "indexed"}) as synced:
            await index_worker.process_event({"action": "sync", "source_type": "public",
                                              "resource_id": "7", "force_reparse": "true"})
        self.assertTrue(synced.call_args.args[0].force_reparse)
        self.assertEqual(client.post.call_args.kwargs["json"]["status"], "completed")


if __name__ == "__main__":
    unittest.main()
