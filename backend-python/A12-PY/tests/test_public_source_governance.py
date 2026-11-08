import asyncio
import json
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import psycopg
from psycopg.conninfo import make_conninfo
import pytest

from test_agent_evolution import isolated_evolution
from a12_ppt import database
from a12_ppt.resources.provenance import assess, trusted_url
from a12_ppt.resources import governance
from a12_ppt.resources.index_store import ResourceIndexStore
from a12_ppt.resources.chunks import chunk_records
from a12_ppt.resources.parsers.document_parser import paged_text
from a12_ppt.resources.parsers.common import ParsedResource
from a12_ppt.models import ResourceIndexSyncRequest, ResourceIndexMetadataRequest


def source(**changes):
    return {'source_kind': 'curriculum', 'source_type': 'official', 'source_url': 'https://www.moe.gov.cn/example.html',
            'source_note': 'test registration', 'version_label': '2022年版', 'version_year': '2022',
            'authority_level': 'official', 'valid_until': '', **changes}


@pytest.mark.parametrize('url', ['http://moe.gov.cn/a', 'https://evilgov.cn/a', 'https://moe.gov.cn.evil.example/a',
                                'https://moe.gov.cn@localhost/a', 'https://127.0.0.1/a', 'https://www.moe.gov.cn:8443/a'])
def test_import_whitelist_cannot_be_bypassed(url):
    assert not trusted_url(url)
    assert not assess({'provenance': source(source_url=url)})['eligible']


def test_temporal_types_keep_versions_and_expire_news_inclusively():
    today = date(2026, 11, 5)
    assert assess({'provenance': source()}, today=today)['eligible']
    assert not assess({}, today=today)['eligible']
    assert assess({'provenance': source(source_kind='current_affairs', valid_until=today.isoformat())}, today=today)['eligible']
    for until in ('', '2026-11-04', 'invalid', '20261105'):
        assert not assess({'provenance': source(source_kind='current_affairs', valid_until=until)}, today=today)['eligible']
    assert not assess({'provenance': source(), 'source_check': {'status': 'broken'}})['eligible']


def test_page_chunks_use_parser_offsets_and_never_cross_page_boundaries():
    text, spans = paged_text([(1, '第一页概念。' * 300), (3, '第三页实例。' * 200)])
    records = chunk_records(text, metadata={'parse': {'page_spans': spans}})
    assert {record['metadata']['page_number'] for record in records} == {1, 3}
    assert all(not ('第一页' in record['content'] and '第三页' in record['content']) for record in records)
    assert all('page_number' not in item['metadata'] for item in chunk_records('Word中无法确定分页的段落'))


def test_model_cannot_claim_grounding_using_invented_citation_ids():
    from a12_ppt.models import OutlineGenerateRequest
    from a12_ppt.presentation import PPTGenerator
    request = OutlineGenerateRequest(title='test', subject='科学', grade='八年级', reference_text='UNTRUSTED_EVIDENCE',
                                    _retrieval_citations={'invented': {}})
    assert not request._retrieval_citations  # Private server state is not accepted from JSON.
    flow = PPTGenerator.__new__(PPTGenerator)
    outline = {'slides': [{'title': 'test', 'citation_ids': ['invented']}]}
    report = flow._outline_quality_report(outline, request, 1)
    assert report['invalid_citation_ids'] == ['invented'] and report['grounding_status'] == 'insufficient_evidence'
    request._retrieval_citations = {'real': {'page_number': 2, 'provenance': source()}}
    outline['slides'][0]['citation_ids'] = ['real']
    report = flow._outline_quality_report(outline, request, 1)
    assert report['checks']['citations_use_retrieved_evidence'] and report['grounding_status'] == 'grounded'


@pytest.fixture
def public_index(isolated_evolution):
    # Actual tables and pgvector live only in a random schema; public is needed for the vector type.
    scoped = make_conninfo(database.get_settings().postgres_dsn)
    from psycopg.conninfo import conninfo_to_dict
    options = conninfo_to_dict(scoped)['options'] + ',public'
    scoped = make_conninfo(scoped, options=options)
    index = ResourceIndexStore.__new__(ResourceIndexStore)
    index.settings = SimpleNamespace(postgres_dsn=scoped, retrieval_min_score=0.0, index_parse_timeout_seconds=2)
    index.embedding_dimensions = 2
    index.embedding_client = SimpleNamespace(embed_query=AsyncMock(return_value=[1.0, 0.0]),
        embed_documents=AsyncMock(side_effect=lambda chunks: [[1.0, 0.0] for _ in chunks]))
    index.available = False
    index._ensure_postgres()
    assert index.available
    return index


def test_real_pgvector_filters_sources_and_emits_page_citations(public_index):
    index = public_index
    async def probe():
        text, spans = paged_text([(1, '光的折射定义和概念。'), (2, '光的折射典型实验。')])
        with patch('a12_ppt.resources.index_store.download_and_parse_resource', new_callable=AsyncMock,
                   return_value=ParsedResource(text=text, metadata={'page_spans': spans, 'content_sha256': 'a' * 64})):
            request = ResourceIndexSyncRequest(source_type='public', resource_id='11', title='test', file_url='https://example.test/test.pdf',
                file_type='pdf', metadata={'provenance': source()})
            assert (await index.sync_resource(request))['status'] == 'indexed'
            result = await index.search_context([], '光的折射', top_k=8)
            assert result['search_mode'] == 'pgvector_hybrid_rerank'
            assert len(result['matches']) == 2
            assert {item['page_number'] for item in result['citations']} == {1, 2}
            assert result['citations'][0]['provenance']['source_url'] == source()['source_url']
            assert '2022年版' in result['context']
            # General registered sources are lower weighted; source label is not grounding confidence.
            old = index._load_resource_meta('public:11')['metadata']
            candidates = [{'resource_id': 'public:11', 'chunk_id': 'a', 'content': '光的折射', 'score': 1, 'metadata': old},
                {'resource_id': 'public:12', 'chunk_id': 'b', 'content': '光的折射', 'score': 1,
                 'metadata': {'provenance': source(source_type='teacher', authority_level='general', source_url='')}}]
            assert index._rerank_matches(candidates, '光的折射', 2)[0]['chunk_id'] == 'a'
            index.update_metadata(ResourceIndexMetadataRequest(source_type='public', resource_id='11',
                metadata={'provenance': source(source_kind='current_affairs', valid_until=(date.today()-timedelta(days=1)).isoformat())}))
            assert not (await index.search_context([], '光的折射'))['matches']
            # Missing registration cannot keep serving the prior successful chunks after a failed refresh.
            request.metadata = {}
            assert (await index.sync_resource(request))['status'] == 'failed'
            assert not (await index.search_context([], '光的折射'))['matches']
    asyncio.run(probe())


def test_patrol_blocks_definite_failure_and_recovers_on_success(public_index):
    index = public_index
    request = ResourceIndexSyncRequest(source_type='public', resource_id='11', title='test', file_url='https://example.test/test.pdf', file_type='pdf', metadata={'provenance': source()})
    metadata = index._build_metadata(request)
    index._replace_index(request, metadata, 'digest', '光的折射', ['光的折射'], [[1.0, 0.0]])
    async def probe():
        with patch.object(governance, 'fetch_source', new_callable=AsyncMock, return_value=(404, {}, b'')):
            assert (await governance.patrol(index, 'test-admin'))['warnings'] == 1
        assert not (await index.search_context([], '光的折射'))['matches']
        with patch.object(governance, 'fetch_source', new_callable=AsyncMock, side_effect=TimeoutError()):
            await governance.patrol(index, 'test-admin')
        assert not (await index.search_context([], '光的折射'))['matches']
        with patch.object(governance, 'fetch_source', new_callable=AsyncMock, return_value=(200, {'etag': 'new'}, b'')):
            await governance.patrol(index, 'test-admin')
        assert (await index.search_context([], '光的折射'))['matches']
        assert not governance.apply_health(index, 'public:11', source(version_label='stale'), {'status': 'broken'})
        assert governance.overview_data(index)['history'][0]['checked_count'] == 1
    asyncio.run(probe())


def test_concurrent_browser_and_event_index_only_embed_once(public_index):
    request = ResourceIndexSyncRequest(source_type='public', resource_id='11', title='test', file_url='https://example.test/file.txt', metadata={'provenance': source()})
    async def probe():
        started, release = asyncio.Event(), asyncio.Event()
        async def parse(*args, **kwargs):
            started.set()
            await release.wait()
            return ParsedResource(text='真实来源的课程内容', metadata={'content_sha256':'digest'})
        with patch('a12_ppt.resources.index_store.download_and_parse_resource', side_effect=parse):
            first = asyncio.create_task(public_index.sync_resource(request))
            try:
                await asyncio.wait_for(started.wait(), 5)
                assert (await public_index.sync_resource(request))['status'] == 'processing'
            finally:
                release.set()
                assert (await first)['status'] == 'indexed'
        assert public_index.embedding_client.embed_documents.await_count == 1
    asyncio.run(probe())


def test_busy_index_event_does_not_report_false_completion(monkeypatch):
    from a12_ppt.resources import index_worker
    monkeypatch.setenv('A12_PYTHON_INTERNAL_KEY', 'test-key')
    real_client = httpx.AsyncClient
    payload = {'source_type':'public','resource_id':'11','title':'test','file_url':'https://example.test/file.txt','metadata':{'provenance':source()}}
    def transport(request):
        assert request.method == 'GET', 'busy resource must not be reported completed'
        return httpx.Response(200, json={'code':200,'data':payload})
    async def probe():
        with patch.object(index_worker.httpx, 'AsyncClient', side_effect=lambda **kwargs:real_client(transport=httpx.MockTransport(transport),**kwargs)), \
             patch.object(index_worker.resource_index_store,'sync_resource',new_callable=AsyncMock,return_value={'status':'processing'}):
            with pytest.raises(RuntimeError,match='保留事件'):
                await index_worker.process_event({'source_type':'public','resource_id':'11','action':'sync'})
    asyncio.run(probe())


def test_fetch_checks_redirects_and_admin_api_permissions(public_index):
    import main
    real_client = httpx.AsyncClient
    def transport(request):
        if request.url.host == 'www.moe.gov.cn':
            return httpx.Response(302, headers={'location': 'http://127.0.0.1/private'})
        raise AssertionError('Unsafe redirect must never be requested')
    async def probe():
        with patch.object(governance.httpx, 'AsyncClient', side_effect=lambda **kwargs: real_client(transport=httpx.MockTransport(transport), **kwargs)):
            with pytest.raises(ValueError):
                await governance.fetch_source(source()['source_url'])
        async with real_client(transport=httpx.ASGITransport(app=main.app), base_url='http://test') as client:
            headers = {'Authorization': 'Bearer test-token'}
            with patch('main.verify_active_token', new_callable=AsyncMock), \
                 patch('main.authenticate_browser', new_callable=AsyncMock, return_value=('7','test-token','teacher')):
                assert (await client.get('/api/v1/python/resources/index/governance', headers=headers)).status_code == 403
            with patch('main.verify_active_token', new_callable=AsyncMock), \
                 patch('main.authenticate_browser', new_callable=AsyncMock, return_value=('7','test-token','admin')), \
                 patch.object(governance, 'store', return_value=public_index), \
                 patch.object(governance, 'fetch_source', new_callable=AsyncMock, return_value=(200, {'content-type': 'text/html; charset=utf-8', 'content-encoding':'gzip'}, ('<html><body><script>EVIL</script><p>' + '真实来源正文。'*20 + '</p></body></html>').encode())):
                response = await client.post('/api/v1/python/resources/index/governance/fetch', headers=headers, json={'source_url':source()['source_url']})
                assert response.status_code == 200 and response.json()['data']['filename'].endswith('.txt')
                import base64
                assert 'EVIL' not in base64.b64decode(response.json()['data']['content_base64']).decode()
                assert (await client.get('/api/v1/python/resources/index/governance', headers=headers)).status_code == 200
    asyncio.run(probe())
