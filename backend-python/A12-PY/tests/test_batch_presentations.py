import asyncio
import io
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from contextlib import asynccontextmanager
from uuid import uuid4

import httpx
import pytest
from docx import Document
from docx.shared import Pt, Inches
from PIL import Image

from test_agent_evolution import isolated_evolution
from a12_ppt import agent_evolution
from a12_ppt.batch_sources import parse_docx, node_material
from a12_ppt.batch_planner import items_from_document, propose,teacher_page_bounds
from a12_ppt.batch_store import batch_store
from a12_ppt import batch_worker


def word_sample():
    document = Document(); document.add_heading('九年级数学联调教学计划',0)
    document.add_heading('第一章 二次函数',1); document.add_paragraph('学习二次函数定义与图像。\n课时：2课时\n教学目标：理解二次函数图像')
    document.add_heading('1.1 顶点与开口',2); document.add_paragraph('根据顶点式观察开口。')
    document.add_table(rows=1,cols=2).rows[0].cells[0].text='x 的取值'
    image=io.BytesIO();Image.new('RGB',(60,30),'blue').save(image,format='PNG');image.seek(0)
    document.add_picture(image,width=Inches(1))
    document.add_heading('第二章 相似三角形',1);document.add_paragraph('探究对应角与对应边。')
    output=io.BytesIO();document.save(output);return output.getvalue()


@pytest.mark.parametrize('text,bounds',[('每章两页',(2,2)),('每份2至3页',(2,3)),('各章十二到十五页',(12,15)),
    ('每个PPT 3–5页',(3,5)),('只要前两章，大学一年级',None),('每章两页，但第二章三页',None)])
def test_only_explicit_per_item_page_instructions_set_global_bounds(text,bounds):
    assert teacher_page_bounds(text)==bounds


def test_asr_source_page_limit_overrides_model_expansion():
    model=SimpleNamespace(available=True,complete=AsyncMock(return_value=json.dumps({'title':'入门课','items':[
        {'title':'第一章 变量','min_pages':2,'max_pages':30,'objectives':['理解变量']},
        {'title':'第二章 分支','min_pages':6,'max_pages':10}]})))
    with patch('a12_ppt.batch_planner.LLMClient',return_value=model):
        value=asyncio.run(propose('按录音生成课件',source_text='第一章变量，第二章分支，每章两页。'))
    assert [(i['min_pages'],i['max_pages']) for i in value['items']]==[(2,2),(2,2)]
    assert value['items'][0]['objectives']=='理解变量'


def test_chapter_exception_is_not_erased_by_original_global_source_limit():
    model=SimpleNamespace(available=True,complete=AsyncMock(return_value=json.dumps({'title':'入门课','items':[
        {'title':'第一章 变量','min_pages':2,'max_pages':2},
        {'title':'第二章 分支','min_pages':3,'max_pages':3}]})))
    with patch('a12_ppt.batch_planner.LLMClient',return_value=model):
        value=asyncio.run(propose('第二章改为三页',source_text='第一章变量，第二章分支，每章两页。',previous={'items':[]}))
    assert [(i['min_pages'],i['max_pages']) for i in value['items']]==[(2,2),(3,3)]


def test_chapter_revision_retains_confirmed_course_metadata():
    original={'title':'大学计算机入门','subject':'计算机科学','grade':'大学一年级','items':[]}
    model=SimpleNamespace(available=True,complete=AsyncMock(return_value=json.dumps({'title':'模型新标题','subject':'信息技术','grade':'通用',
        'items':[{'title':'第一章 变量','min_pages':2,'max_pages':2}]})))
    with patch('a12_ppt.batch_planner.LLMClient',return_value=model):
        value=asyncio.run(propose('每章两页，整理教学目标',previous=original))
    assert all(value[k]==original[k] for k in ('title','subject','grade'))


def test_docx_fast_plan_respects_teacher_range_without_extra_model_call():
    with patch('a12_ppt.batch_planner.LLMClient') as model:
        value=asyncio.run(propose('大学数学，每份2至3页',document=parse_docx(word_sample(),'plan.docx')))
    model.assert_not_called()
    assert all((i['min_pages'],i['max_pages'])==(2,3) for i in value['items'])


def test_word_hierarchy_tables_images_and_single_conversion():
    doc=parse_docx(word_sample(),'lesson.docx')
    assert len(doc['chapters'])==2 and len(doc['chapters'][0]['children'])==1
    text,images=node_material(doc['chapters'][0])
    assert text.index('顶点式')<text.index('x 的取值')
    assert len(images)==1 and images[0]['data_url'].startswith('data:image/jpeg;base64,')
    assert not node_material(doc['chapters'][1])[1]
    assert len(items_from_document(doc,single=True))==1
    assert len(items_from_document(doc))==2
    assert items_from_document(doc)[0]['hours']=='2课时'
    assert items_from_document(doc)[0]['objectives']=='理解二次函数图像'


def test_number_and_font_heuristics_and_plain_fallback():
    document=Document()
    for text in ['1. 第一章','1.1 第一节','第二章 新章','第一节 小节']:document.add_paragraph(text)
    output=io.BytesIO();document.save(output)
    doc=parse_docx(output.getvalue(),'numbered.docx')
    assert len(doc['chapters'])==2
    assert doc['chapters'][0]['children'][0]['title'].startswith('1.1')
    assert doc['chapters'][1]['children'][0]['title'].startswith('第一节')
    document=Document();document.add_paragraph('普通正文，不带章节格式。')
    output=io.BytesIO();document.save(output)
    doc=parse_docx(output.getvalue(),'plain.docx')
    assert len(doc['chapters'])==1 and doc['warnings']
    document=Document();p=document.add_paragraph('实验准备');p.runs[0].font.size=Pt(18)
    document.add_paragraph('准备量筒和清水。')
    output=io.BytesIO();document.save(output)
    assert parse_docx(output.getvalue(),'font.docx')['chapters'][0]['title']=='实验准备'


def test_missing_textbook_directory_requires_explicit_suggested_choice():
    result=asyncio.run(propose('整本九年级数学的PPT'))
    assert result['needs_input'] and not result['items']
    with patch('a12_ppt.batch_planner.LLMClient') as llm:
        llm.return_value.available=True
        llm.return_value.complete=AsyncMock(return_value=json.dumps({'title':'建议课程','subject':'数学','grade':'九年级',
            'items':[{'title':'二次函数','min_pages':2,'max_pages':3}]}))
        result=asyncio.run(propose('整本九年级数学的PPT',allow_suggested=True))
        assert result['basis']=='suggested' and not result['needs_input']


def test_inline_pasted_or_spoken_plan_is_used_as_material_without_requiring_second_paste():
    message='按这个计划生成九年级数学课件：第一章 二次函数，2课时；第二章 相似三角形，2课时。'
    with patch('a12_ppt.batch_planner.LLMClient') as llm:
        llm.return_value.available=True
        llm.return_value.complete=AsyncMock(return_value=json.dumps({'title':'九年级数学','subject':'数学','grade':'九年级',
            'items':[{'title':'二次函数','min_pages':3,'max_pages':5},{'title':'相似三角形','min_pages':3,'max_pages':5}]},ensure_ascii=False))
        value=asyncio.run(propose(message))
        assert value['basis']=='provided_text' and len(value['items'])==2
        context=json.loads(llm.return_value.complete.await_args.args[1])
        assert context['source_text']==message
        assert value['items'][0]['source_text']==message


@pytest.fixture
def batches(isolated_evolution,monkeypatch):
    import importlib
    module=importlib.import_module('a12_ppt.batch_store')
    monkeypatch.setattr(module,'connect',agent_evolution.connect)
    monkeypatch.setattr(batch_worker,'connect',agent_evolution.connect)
    return batch_store


def draft(batches,owner='7',count=2):
    items=[{'id':uuid4().hex,'title':f'第{index+1}章','source_text':'已核验的课堂资料', 'images':[],
            'min_pages':2,'max_pages':3,'objectives':'理解课程内容'} for index in range(count)]
    return batches.save_plan(owner,{'title':'测试课程','subject':'数学','grade':'九年级','basis':'document','items':items})


def confirm(batches,row):
    return batches.confirm(row['user_id'],row['id'],row['revision'],[item['id'] for item in row['payload']['items']],'素白风',False)


def test_confirmation_is_owned_versioned_bounded_and_idempotent(batches):
    row=draft(batches)
    with pytest.raises(ValueError):batches.confirm('other',row['id'],1,[row['payload']['items'][0]['id']],'素白风',False)
    with pytest.raises(ValueError,match='变化'):batches.confirm('7',row['id'],999,[row['payload']['items'][0]['id']],'素白风',False)
    batch_id=confirm(batches,row)
    assert confirm(batches,row)==batch_id
    state=batches.get('7',batch_id)
    assert len(state['items'])==2 and batches.get('8',batch_id) is None
    item=batches.item('7',batch_id,state['items'][0]['id'])
    assert item['payload']['subject']=='数学'
    another=draft(batches)
    with pytest.raises(ValueError,match='还有批量'):confirm(batches,another)
    batches.cancel('7',batch_id)
    confirm(batches,another)


def test_suggested_plan_gate_and_stale_draft_update(batches):
    row=draft(batches)
    payload=row['payload'];payload['basis']='suggested'
    saved=batches.save_plan('7',payload,plan_id=row['id'],revision=1)
    with pytest.raises(ValueError):batches.save_plan('7',payload,plan_id=row['id'],revision=1)
    with pytest.raises(ValueError,match='AI 建议'):confirm(batches,saved)
    batches.confirm('7',row['id'],saved['revision'],[item['id'] for item in payload['items']],'素白风',True)


@asynccontextmanager
async def admission(*args,**kwargs):yield SimpleNamespace()


HTML='<!doctype html><html><head><style>html,body{margin:0;width:1280px;height:720px;overflow:hidden}.slide{width:1280px;height:720px}</style></head><body><section class="slide"><h1>真实 HTML 页面</h1></section></body></html>'


def test_worker_checkpoints_recovers_failures_and_keeps_pending_project_state(batches):
    row=draft(batches,count=1);batch_id=confirm(batches,row)
    item=batches.claim()
    outline=AsyncMock(return_value={'title':'test','slides':[{'title':'第一张'},{'title':'第二张'}],'generation_status':'model'})
    async def broken(request,**kwargs):
        yield {'type':'slide','slide':{'slide_no':1,'title':'第一张','html':HTML},'completed':1,'total':2}
        raise RuntimeError('upstream disconnected')
    fake=SimpleNamespace(llm=SimpleNamespace(available=True),generate_outline=outline,stream_presentation=broken)
    async def probe():
        with patch.object(batch_worker,'limit_job',admission),patch.object(batch_worker,'prompt_session',admission):
            await batch_worker.process_item(item,fake)
            failed=batches.item('7',batch_id,item['id'])
            assert failed['status']=='failed' and failed['output']['slides']['1']['html']==HTML
            batches.retry('7',batch_id,item['id']);recovered=batches.claim()
            async def successful(request,**kwargs):
                assert kwargs['resume_slides']['1']['html']==HTML
                yield {'type':'final','response':{'slides':[{'slide_no':1,'title':'第一张','html':HTML},{'slide_no':2,'title':'第二张','html':HTML}]}}
            fake.stream_presentation=successful
            with patch.object(batch_worker,'save_project',new_callable=AsyncMock,return_value=False):
                await batch_worker.process_item(recovered,fake)
            final=batches.get('7',batch_id)
            assert final['status']=='ready' and final['items'][0]['project_id'] is None
            assert outline.await_count==1
            batches.saved('7',batch_id,item['id'],123)
            batches.saved('7',batch_id,item['id'],123)
            assert batches.get('7',batch_id)['status']=='completed'
            with pytest.raises(ValueError):batches.saved('8',batch_id,item['id'],999)
    asyncio.run(probe())


def test_leases_concurrency_cancel_and_retry_limits(batches):
    row=draft(batches);confirm(batches,row)
    item=batches.claim();assert item
    assert batches.claim() is None  # One chapter per teacher, even with two workers.
    with agent_evolution.connect() as conn:
        conn.execute("UPDATE a12_batch_item SET updated_at=NOW()-INTERVAL '3 minutes' WHERE id=%s",(item['id'],))
    recovered=batches.claim();assert recovered['id']==item['id'] and recovered['lease_id']!=item['lease_id']
    with pytest.raises(asyncio.CancelledError):batches.update(item,progress=50)
    batches.update(recovered,status='failed')
    with agent_evolution.connect() as conn:conn.execute('UPDATE a12_batch_item SET attempts=3 WHERE id=%s',(item['id'],))
    with pytest.raises(ValueError,match='3 次'):batches.retry('7',row['id'],item['id'])
    batches.cancel('7',row['id'])
    assert batches.claim() is None


def test_cancel_interrupts_inflight_model_and_releases_job(batches,monkeypatch):
    row=draft(batches,count=1);confirm(batches,row)
    item=batches.claim()
    monkeypatch.setattr(batch_worker,'HEARTBEAT_SECONDS',.02)
    started=asyncio.Event();interrupted=asyncio.Event()
    async def slow_outline(request):
        started.set()
        try: await asyncio.sleep(60)
        finally: interrupted.set()
    fake=SimpleNamespace(llm=SimpleNamespace(available=True),generate_outline=slow_outline)
    async def probe():
        with patch.object(batch_worker,'limit_job',admission),patch.object(batch_worker,'prompt_session',admission):
            task=asyncio.create_task(batch_worker.process_item(item,fake))
            await asyncio.wait_for(started.wait(),3)
            batches.cancel('7',row['id'])
            with pytest.raises(asyncio.CancelledError):await asyncio.wait_for(task,3)
            assert interrupted.is_set()
            assert batches.get('7',row['id'])['items'][0]['status']=='cancelled'
    asyncio.run(probe())


def test_home_sync_stops_on_business_failure_without_scanning_every_chapter(batches):
    from a12_ppt import batch_router
    from a12_ppt.direct_auth import direct_user_id,direct_bearer
    row=draft(batches);confirm(batches,row)
    for _ in range(2):
        item=batches.claim();batches.update(item,status='ready',output={'presentation':{'slides':[{'html':HTML}]}})
    async def probe():
        identity=direct_user_id.set('7');bearer=direct_bearer.set('test')
        try:
            with patch.object(batch_router,'save_project',new_callable=AsyncMock,side_effect=RuntimeError('Java unavailable')) as save:
                result=await batch_router.sync_ready()
                assert result['data']['saved']==0 and save.await_count==1
        finally:direct_user_id.reset(identity);direct_bearer.reset(bearer)
    asyncio.run(probe())


def test_zip_partial_gate_and_failed_export_retry_preserves_item(batches,tmp_path,monkeypatch):
    row=draft(batches);confirm(batches,row)
    item=batches.claim();batches.update(item,status='ready',output={'presentation':{'slides':[{'html':HTML}]}},progress=100)
    other=batches.claim();batches.update(other,status='failed')
    with pytest.raises(ValueError,match='所有章节'):batch_worker.request_zip('7',row['id'],False)
    batch_worker.request_zip('7',row['id'],True)
    job=batch_worker.claim_zip()
    monkeypatch.setattr(batch_worker,'EXPORT_DIR',tmp_path)
    async def probe():
        with patch.object(batch_worker,'limit_job',admission),patch.object(batch_worker,'export_html_slides_to_pptx',new_callable=AsyncMock,side_effect=RuntimeError('exporter unavailable')):
            await batch_worker.process_zip(job)
        assert batches.get('7',row['id'])['zip_status']=='failed'
        batch_worker.request_zip('7',row['id'],True);retried=batch_worker.claim_zip()
        exported=tmp_path/'source.pptx'
        with zipfile.ZipFile(exported,'w') as archive:archive.writestr('ppt/slides/slide1.xml','<a:t>可编辑</a:t>')
        with patch.object(batch_worker,'limit_job',admission),patch.object(batch_worker,'export_html_slides_to_pptx',new_callable=AsyncMock,return_value=exported):
            await batch_worker.process_zip(retried)
        assert batches.get('7',row['id'])['zip_status']=='ready'
        with zipfile.ZipFile(tmp_path/(row['id']+'.zip')) as archive:
            assert len([name for name in archive.namelist() if name.endswith('.pptx')])==1
            assert 'failed' in archive.read('批次清单.json').decode()
    asyncio.run(probe())


def test_batch_api_ownership_confirmation_and_graph_routing(batches):
    from main import app
    from a12_ppt.chat_router import ChatRouteRequest,ChatRouteWorkflow
    row=draft(batches)
    async def probe():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            headers={'Authorization':'Bearer test'}
            with patch('main.verify_active_token',new_callable=AsyncMock),patch('main.authenticate_browser',new_callable=AsyncMock,return_value=('8','test','teacher')):
                assert (await client.get('/api/v1/python/batch-presentations/plans/'+row['id'],headers=headers)).status_code==404
            with patch('main.verify_active_token',new_callable=AsyncMock),patch('main.authenticate_browser',new_callable=AsyncMock,return_value=('7','test','teacher')):
                response=await client.get('/api/v1/python/batch-presentations/plans/'+row['id'],headers=headers)
                assert response.status_code==200 and 'source_text' not in response.text
                response=await client.post('/api/v1/python/batch-presentations/plans/'+row['id']+'/confirm',headers=headers,json={
                    'revision':1,'item_ids':[item['id'] for item in row['payload']['items']]})
                assert response.status_code==200
        routed=await ChatRouteWorkflow().route(ChatRouteRequest(user_id='7',messages=[{'role':'user','content':'按章生成PPT'}],route_preference='batch'))
        assert routed['next_stage']=='batch_plan'
    asyncio.run(probe())
