import asyncio
import contextlib
import hashlib
import json
import logging
import os
import re
import zipfile
from pathlib import Path
from uuid import uuid4

import httpx
from fastapi import HTTPException
from .agent_evolution import connect, prompt_session, current_policy
from .ai_runtime import use_runtime_options
from .batch_store import batch_store
from .job_limits import limit_job
from .models import OutlineGenerateRequest, PresentationGenerateRequest
from .presentation import PPTGenerator, export_html_slides_to_pptx

logger = logging.getLogger(__name__)
EXPORT_DIR = Path(__file__).resolve().parents[1] / 'data' / 'batch-exports'
EXPORT_DIR.mkdir(parents=True, exist_ok=True)
_workers = []
HEARTBEAT_SECONDS = 15


def import_payload(item):
    output = item['output'].get('presentation') or {}
    return {'batch_id': item['batch_id'], 'item_id': item['id'],
        'title': f"{item.get('course_title') or item.get('course_name') or '课程'} · {item['item_order']:02d} {item['title']}"[:180],
        'slides': output.get('slides', []), 'metadata': output.get('metadata') or {}}


async def save_project(item, bearer=None):
    base = os.getenv('JAVA_AUTH_BASE_URL', 'http://127.0.0.1:8088').rstrip('/')
    key = os.getenv('A12_PYTHON_INTERNAL_KEY')
    if bearer:
        url, headers = base + '/api/v1/projects/batch-import', {'Authorization': 'Bearer ' + bearer}
    elif key:
        url, headers = base + '/api/v1/internal/batch-projects/' + item['user_id'], {'X-A12-Internal-Key': key}
    else:
        return False
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(url, headers=headers, json=import_payload(item))
    if response.status_code in (401,403):
        raise ValueError('登录或归档权限已失效，请重新登录后同步')
    response.raise_for_status()
    envelope = response.json()
    data = envelope.get('data') or {}
    if envelope.get('code') not in (0,200) or not data.get('id') or str(data.get('user_id')) != item['user_id']:
        raise ValueError('个人项目保存未成功，生成内容已保留，可重新同步')
    await asyncio.to_thread(batch_store.saved,item['user_id'],item['batch_id'],item['id'],int(data['id']))
    return True


async def process_item(item, generator=None):
    generator = generator or PPTGenerator()
    output = dict(item['output'] or {})
    payload = item['payload']
    parent = asyncio.current_task()
    async def heartbeat():
        while True:
            await asyncio.sleep(HEARTBEAT_SECONDS)
            try:
                await asyncio.to_thread(batch_store.update,item)
            except asyncio.CancelledError:
                if not asyncio.current_task().cancelling(): parent.cancel('任务已取消或租约失效')
                return
            except Exception:
                logger.warning('批量任务心跳失败，停止本次执行 item=%s',item['id'],exc_info=True)
                parent.cancel('无法续租，停止生成以避免重复执行')
                return
    pulse = asyncio.create_task(heartbeat())
    try:
        async with limit_job('presentation', {'batch':item['batch_id'],'item':item['id']}, user_id=item['user_id']):
            with use_runtime_options(item['user_id'],'batch_presentation',reasoning_effort=payload.get('reasoning_effort','low')):
                async with prompt_session(item['user_id'],item['theme']):
                    if not generator.llm.available:
                        raise ValueError('模型未配置，不能把兜底页面视为批量生成成功')
                    if not output.get('outline'):
                        await asyncio.to_thread(batch_store.update,item,stage='规划本章大纲',progress=5)
                        outline = await generator.generate_outline(OutlineGenerateRequest(title=item['title'],
                            subject=payload.get('subject') or '通用', grade=payload.get('grade') or '教师指定对象',
                            requirements=(payload.get('requirements') or '')+'\n本章课时安排：'+(payload.get('hours') or '由教师确认'), teaching_goals=payload.get('objectives'),
                            reference_text=payload.get('source_text'), slide_count=None,
                            enable_rag=bool(payload.get('enable_rag')),
                            reasoning_effort=payload.get('reasoning_effort','low'),
                            slide_count_range={'min_pages':payload['min_pages'],'max_pages':payload['max_pages']}))
                        if outline.get('generation_status') == 'fallback' or outline.get('_fallback'):
                            raise ValueError('大纲未由模型成功生成，请重试')
                        output['outline'] = outline
                        await asyncio.to_thread(batch_store.update,item,stage='大纲已规划',progress=15,output=output)
                    if not output.get('presentation'):
                        outline = {**output['outline'], 'source_material': payload.get('source_text','')[:16000],
                            'reference_images': [{'id':image['id'],'label':image['label'],'source':'a12-batch-image://' + image['id']} for image in payload.get('images',[])]}
                        request = PresentationGenerateRequest(
                            title=item['title'], outline=outline, theme=item['theme'],
                            enable_rag=bool(payload.get('enable_rag')),
                            reasoning_effort=payload.get('reasoning_effort','low'))
                        resume = output.get('slides', {}) if output.get('prompt_version') == current_policy().get('prompt_version') else {}
                        output['prompt_version'] = current_policy().get('prompt_version')
                        async for event in generator.stream_presentation(request, resume_slides=resume):
                            if event.get('type') == 'slide':
                                slide = event['slide']
                                output.setdefault('slides', {})[str(slide['slide_no'])] = slide
                                await asyncio.to_thread(batch_store.update,item,stage=f"生成页面 {event['completed']}/{event['total']}",
                                    progress=15+round(75*event['completed']/event['total']),output=output)
                            elif event.get('type') == 'final':
                                output['presentation'] = event['response']
                        if not output.get('presentation',{}).get('slides'):
                            raise ValueError('模型未返回可用课件页面')
                        for slide in output['presentation']['slides']:
                            for image in payload.get('images',[]):
                                slide['html'] = slide['html'].replace('a12-batch-image://' + image['id'],image['data_url'])
                        output.pop('slides',None)
                        await asyncio.to_thread(batch_store.update,item,stage='已生成，等待保存到个人项目',progress=100,output=output,status='ready')
                    else:
                        await asyncio.to_thread(batch_store.update,item,stage='已生成，等待保存到个人项目',progress=100,status='ready')
        item['output'] = output
    except HTTPException as exc:
        if exc.status_code in (409,429,503):
            await asyncio.to_thread(batch_store.defer,item)
        else:
            await asyncio.to_thread(batch_store.update,item,status='failed',stage='生成失败',error='生成服务暂不可用，请重试')
        return
    except asyncio.CancelledError:
        with contextlib.suppress(Exception):
            await asyncio.to_thread(batch_store.defer,item)
        raise
    except Exception:
        logger.exception('批量章节生成失败 batch=%s item=%s',item['batch_id'],item['id'])
        await asyncio.to_thread(batch_store.update,item,status='failed',stage='生成失败',error='本章生成未完成，已保留检查点，可单独重试')
        return
    finally:
        pulse.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await pulse
    try:
        await save_project(item)
    except Exception:
        logger.warning('章节已生成，项目待同步 batch=%s item=%s',item['batch_id'],item['id'])


def request_zip(owner,batch_id,include_partial):
    with connect() as conn:
        batch = conn.execute('SELECT * FROM a12_batch_job WHERE id=%s AND user_id=%s FOR UPDATE',(batch_id,owner)).fetchone()
        if not batch:
            raise ValueError('批次不存在')
        if batch['zip_status'] in ('queued','running'):
            return
        counts = conn.execute("""SELECT COUNT(*) AS total,COUNT(*) FILTER(WHERE status IN ('ready','completed')) AS ready
            FROM a12_batch_item WHERE batch_id=%s""",(batch_id,)).fetchone()
        if not counts['ready'] or (not include_partial and counts['total'] != counts['ready']):
            raise ValueError('请等待所有章节生成成功，或明确选择只打包已完成项')
        conn.execute("UPDATE a12_batch_job SET zip_status='queued',zip_error='',include_partial=%s,zip_updated_at=NOW() WHERE id=%s",(include_partial,batch_id))


def claim_zip():
    with connect() as conn:
        conn.execute("""UPDATE a12_batch_job SET zip_status='failed',zip_error='打包中断，请重试'
            WHERE zip_status='running' AND zip_updated_at<NOW()-INTERVAL '2 minutes'""")
        batch = conn.execute("SELECT * FROM a12_batch_job WHERE zip_status='queued' ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1").fetchone()
        if not batch:
            return None
        batch['zip_lease'] = uuid4().hex
        conn.execute("UPDATE a12_batch_job SET zip_status='running',zip_lease=%s,zip_updated_at=NOW() WHERE id=%s",(batch['zip_lease'],batch['id']))
        batch['items'] = conn.execute('SELECT * FROM a12_batch_item WHERE batch_id=%s ORDER BY item_order',(batch['id'],)).fetchall()
        return batch


def zip_touch(batch, status='running', error=''):
    with connect() as conn:
        if not conn.execute("""UPDATE a12_batch_job SET zip_status=%s,zip_error=%s,zip_updated_at=NOW()
            WHERE id=%s AND zip_status='running' AND zip_lease=%s""",(status,error,batch['id'],batch['zip_lease'])).rowcount:
            raise asyncio.CancelledError('打包任务已取消')


async def process_zip(batch):
    temp = EXPORT_DIR / (batch['id'] + '-' + batch['zip_lease'] + '.tmp')
    parent=asyncio.current_task()
    async def heartbeat():
        while True:
            await asyncio.sleep(HEARTBEAT_SECONDS)
            try: await asyncio.to_thread(zip_touch,batch)
            except asyncio.CancelledError:
                if not asyncio.current_task().cancelling():parent.cancel('打包任务已取消')
                return
            except Exception:
                logger.warning('批量打包心跳失败 batch=%s',batch['id'],exc_info=True)
                parent.cancel('无法续租，停止打包')
                return
    pulse = asyncio.create_task(heartbeat())
    try:
        async with limit_job('export',{'batch_zip':batch['id']},user_id=batch['user_id']):
            manifest = {'title':batch['title'],'items':[]}
            with zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_DEFLATED) as archive:
                for item in batch['items']:
                    state = {'title':item['title'],'status':item['status'],'project_id':item['project_id']}
                    manifest['items'].append(state)
                    if item['status'] not in ('ready','completed'):
                        continue
                    presentation = item['output'].get('presentation') or {}
                    digest = hashlib.sha256(json.dumps(presentation.get('slides'),ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:16]
                    filename = item['id'] + '-' + digest + '.pptx'
                    target = EXPORT_DIR / filename
                    if not target.exists() or not zipfile.is_zipfile(target):
                        output = await export_html_slides_to_pptx(item['title'],presentation['slides'],filename,'dom_editable',False)
                        if output.resolve() != target.resolve():
                            partial=target.with_suffix('.partial')
                            await asyncio.to_thread(partial.write_bytes,output.read_bytes())
                            partial.replace(target)
                    safe = re.sub(r'[^\w\u4e00-\u9fff.\- ]','_',item['title'])[:70]
                    archive.write(target,f"{item['item_order']:02d}_{safe}.pptx")
                    await asyncio.to_thread(zip_touch,batch)
                archive.writestr('批次清单.json',json.dumps(manifest,ensure_ascii=False,indent=2))
            await asyncio.to_thread(zip_touch,batch)
            temp.replace(EXPORT_DIR / (batch['id'] + '.zip'))
            await asyncio.to_thread(zip_touch,batch,'ready')
    except asyncio.CancelledError:
        raise
    except HTTPException:
        with contextlib.suppress(asyncio.CancelledError):
            await asyncio.to_thread(zip_touch,batch,'failed','导出配额暂满，请稍后重试打包')
    except Exception:
        logger.exception('批量打包失败 batch=%s',batch['id'])
        with contextlib.suppress(asyncio.CancelledError):
            await asyncio.to_thread(zip_touch,batch,'failed','打包未完成，章节产物已保留，可重试')
    finally:
        pulse.cancel()
        with contextlib.suppress(asyncio.CancelledError): await pulse
        temp.unlink(missing_ok=True)


def start_batch_workers():
    if _workers:
        return
    async def run_child(work):
        task=asyncio.create_task(work)
        try: await task
        except asyncio.CancelledError:
            if asyncio.current_task().cancelling(): raise
    async def loop():
        while True:
            try:
                item = await asyncio.to_thread(batch_store.claim)
                if item:
                    await run_child(process_item(item))
                else:
                    batch = await asyncio.to_thread(claim_zip)
                    if batch: await run_child(process_zip(batch))
                    else: await asyncio.sleep(2)
            except asyncio.CancelledError: raise
            except Exception:
                logger.exception('批量任务调度异常，将稍后重试')
                await asyncio.sleep(5)
    _workers.extend(asyncio.create_task(loop()) for _ in range(2))


async def stop_batch_workers():
    for task in _workers: task.cancel()
    await asyncio.gather(*_workers,return_exceptions=True)
    _workers.clear()
