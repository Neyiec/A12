"""Public source registration, bounded authoritative import and scheduled patrol."""
import asyncio
import base64
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from html.parser import HTMLParser
from email.message import Message
from urllib.parse import urljoin, urlsplit

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import psycopg

from ..direct_auth import direct_user_id, direct_user_role
from .provenance import assess, trusted_url

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/api/v1/python/resources/index/governance')
_task = None


def admin():
    if not direct_user_id.get() or direct_user_role.get() != 'admin':
        raise HTTPException(403, '仅管理员可维护公共来源')


def store():
    from . import resource_index_store
    if not resource_index_store.available:
        raise HTTPException(503, '来源巡检需要 PostgreSQL 可用')
    return resource_index_store


async def fetch_source(url, *, head=False):
    """Whitelist every redirect; never proxy arbitrary user URLs or unlimited responses."""
    # Some legacy government CDNs mislabel compressed responses; request plain bytes.
    async with httpx.AsyncClient(timeout=8, follow_redirects=False, trust_env=False,
                                 headers={'Accept-Encoding': 'identity'}) as client:
        for _ in range(5):
            if not trusted_url(url):
                raise ValueError('仅支持 gov.cn、pep.com.cn、hep.com.cn 白名单 HTTPS 来源，跳转也须合规')
            async with client.stream('HEAD' if head else 'GET', url) as response:
                if response.is_redirect:
                    url = urljoin(url, response.headers.get('location', ''))
                    continue
                if head:
                    return response.status_code, dict(response.headers), b''
                response.raise_for_status()
                content = bytearray()
                async for block in response.aiter_bytes():
                    content.extend(block)
                    if len(content) > 20 * 1024 * 1024:
                        raise ValueError('来源文件超过 20MB，请下载后从文件上传入口导入')
                return response.status_code, dict(response.headers), bytes(content)
        raise ValueError('来源跳转过多')


class ReadableHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style', 'nav', 'header', 'footer'}:
            self.skip += 1
    def handle_endtag(self, tag):
        if tag in {'script', 'style', 'nav', 'header', 'footer'}:
            self.skip = max(0, self.skip - 1)
    def handle_data(self, data):
        if not self.skip and data.strip():
            self.parts.append(data.strip())


class ImportRequest(BaseModel):
    source_url: str = Field(min_length=10, max_length=1800)


@router.post('/fetch')
async def source_import(request: ImportRequest):
    admin()
    try:
        _, headers, content = await asyncio.wait_for(fetch_source(request.source_url), 30)
        digest = hashlib.sha256(content).hexdigest()
        mime = headers.get('content-type', '').lower()
        if content.startswith(b'%PDF'):
            ext, mime = 'pdf', 'application/pdf'
        elif content.startswith(b'PK') and urlsplit(request.source_url).path.lower().endswith('.docx'):
            ext, mime = 'docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        elif 'html' in mime or content.lstrip().lower().startswith((b'<!doctype html', b'<html')):
            parser = ReadableHTML()
            # fetch_source already decoded Content-Encoding; do not feed its gzip header
            # into a second httpx.Response and accidentally decompress plain HTML twice.
            message = Message()
            message['content-type'] = headers.get('content-type', '')
            encoding = message.get_content_charset() or 'utf-8'
            try:
                text = content.decode(encoding, errors='replace')
            except LookupError:
                text = content.decode('utf-8', errors='replace')
            parser.feed(text)
            content = ('来源：' + request.source_url + '\n\n' + '\n\n'.join(parser.parts)).encode('utf-8')
            ext, mime = 'txt', 'text/plain'
        elif mime.startswith('text/plain'):
            ext = 'txt'
        else:
            raise ValueError('该链接不是支持的 PDF、Word 或正文网页')
        if len(content) < 60:
            raise ValueError('来源正文为空或过短，请检查链接')
        return {'code': 200, 'data': {'filename': '权威来源资料.' + ext, 'content_type': mime,
            'content_base64': base64.b64encode(content).decode(), 'source_sha256': digest,
            'source_url': request.source_url}}
    except (ValueError, httpx.HTTPError, TimeoutError) as exc:
        raise HTTPException(400, '来源读取失败：' + str(exc)[:180]) from None


def rows_for_patrol(index, limit, *, recent=False):
    order = "metadata#>>'{source_check,checked_at}' DESC NULLS LAST" if recent else "metadata#>>'{source_check,checked_at}' ASC NULLS FIRST"
    with index._connect() as conn:
        return conn.execute(f"""SELECT resource_key,resource_id,title,metadata,available
            FROM a12_resource_index WHERE source_type='public' ORDER BY {order},resource_key LIMIT %s""", (limit,)).fetchall()


def overview_data(index):
    # All rows are assessed for the warning count; display is bounded independently.
    with index._connect() as conn:
        rows = conn.execute("""SELECT resource_key,resource_id,title,metadata,available
            FROM a12_resource_index WHERE source_type='public' ORDER BY updated_at DESC""").fetchall()
        history = conn.execute("""SELECT id,actor,checked_count,warning_count,created_at
            FROM a12_public_source_patrol ORDER BY id DESC LIMIT 10""").fetchall()
    items = []
    for key, resource_id, title, metadata, available in rows:
        check = assess({**(metadata or {}), 'available': available})
        health = (metadata or {}).get('source_check') or {}
        items.append({'resource_key': key, 'resource_id': resource_id, 'title': title, 'available': available,
                      'assessment': check, 'source_check': health})
    return {'total': len(items), 'blocked': sum(not item['assessment']['eligible'] for item in items),
            'warnings': sum(bool(item['assessment']['reasons'] or item['source_check'].get('warning')) for item in items),
            'items': sorted(items, key=lambda item: item['assessment']['eligible'])[:100],
            'history': [dict(zip(('id','actor','checked_count','warning_count','created_at'), row)) for row in history]}


@router.get('')
async def overview():
    admin()
    return {'code': 200, 'data': await asyncio.to_thread(overview_data, store())}


async def patrol(index, actor, limit=20):
    # One patrol across workers. Source checks update resource+chunk metadata together.
    conn = await asyncio.to_thread(index._connect)
    try:
        locked = (await asyncio.to_thread(conn.execute, 'SELECT pg_try_advisory_lock(120240711)')).fetchone()[0]
        if not locked:
            raise HTTPException(409, '已有来源巡检正在执行')
        rows = await asyncio.to_thread(rows_for_patrol, index, limit)
        semaphore = asyncio.Semaphore(4)
        async def check(row):
            key, resource_id, title, metadata, available = row
            metadata = metadata or {}
            url = (metadata.get('provenance') or {}).get('source_url') or ''
            status, warning = 'registered', ''
            detail = {}
            if trusted_url(url):
                async with semaphore:
                    try:
                        http_status, headers, _ = await asyncio.wait_for(fetch_source(url, head=True), 15)
                        status = 'broken' if http_status in (404, 410) else ('ok' if 200 <= http_status < 300 else 'warning')
                        detail['http_status'] = http_status
                        if status != 'ok':
                            warning = f'来源返回 HTTP {http_status}，请核对'
                        signature = headers.get('etag') or headers.get('last-modified')
                        previous = (metadata.get('source_check') or {}).get('signature')
                        if signature:
                            detail['signature'] = signature
                            if previous and signature != previous:
                                warning = '来源已变化，请核对版本并按需重新导入'
                    except (ValueError, httpx.HTTPError, TimeoutError):
                        status, warning = 'warning', '来源链接暂不可核验；请稍后重试或人工核对'
            elif url:
                warning = '一般来源未自动访问，请人工核对原始出处'
            if (metadata.get('source_check') or {}).get('status') == 'broken' and status not in ('ok', 'registered'):
                status = 'broken'
            health = {'checked_at': datetime.now(timezone.utc).isoformat(), 'status': status, 'warning': warning, **detail}
            await asyncio.to_thread(apply_health, index, key, metadata.get('provenance'), health)
            # Recoverable network failures warn; definite 404/410 blocks citations until rechecked.
            state = assess({**metadata, 'source_check': health})
            return int(bool(warning or state['reasons']))
        results = await asyncio.gather(*(check(row) for row in rows))
        def save():
            with index._connect() as db:
                db.execute('INSERT INTO a12_public_source_patrol(actor,checked_count,warning_count) VALUES (%s,%s,%s)',
                           (actor, len(rows), sum(results)))
        await asyncio.to_thread(save)
        return {'checked': len(rows), 'warnings': sum(results)}
    finally:
        await asyncio.to_thread(conn.close)


def apply_health(index, key, expected, health):
    with index._connect() as conn:
        row = conn.execute('SELECT metadata FROM a12_resource_index WHERE resource_key=%s FOR UPDATE', (key,)).fetchone()
        if not row or (row[0] or {}).get('provenance') != expected:
            return False  # Do not attach an old URL check to a newly edited registration.
        metadata = {**(row[0] or {}), 'source_check': health}
        patch = {'source_check': health, 'provenance_valid': assess(metadata)['eligible']}
        encoded = json.dumps(patch, ensure_ascii=False)
        conn.execute('UPDATE a12_resource_index SET metadata=metadata || %s::jsonb WHERE resource_key=%s', (encoded, key))
        conn.execute('UPDATE a12_resource_index_chunk SET metadata=metadata || %s::jsonb WHERE resource_key=%s', (encoded, key))
        return True


@router.post('/patrol')
async def run_patrol():
    admin()
    return {'code': 200, 'data': await patrol(store(), direct_user_id.get())}


def start_patrol_worker():
    global _task
    if _task and not _task.done():
        return
    async def loop():
        interval = max(300, int(os.getenv('A12_SOURCE_PATROL_INTERVAL_SECONDS', '21600')))
        while True:
            try:
                await patrol(store(), 'scheduled')
            except Exception:
                logger.warning('公共来源巡检未完成，下轮重试', exc_info=True)
            await asyncio.sleep(interval)
    _task = asyncio.create_task(loop())


async def stop_patrol_worker():
    global _task
    if _task:
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
        _task = None
