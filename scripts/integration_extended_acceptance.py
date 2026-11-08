"""Explicit local, Mock-labelled course/concurrency/complex DOCX/ASR acceptance.

Requires A12_REAL_DB_CONFIRM=3306/a12 and A12_TEST_PASSWORD. OSS is deferred by
the user; active upload storage stays local. No simulated strategy metrics.
"""
import importlib.util
import io
import json
import logging
import os
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from docx import Document

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('original_acceptance',ROOT/'scripts/integration_original_database.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
sys.path.insert(0,str(ROOT/'backend-python/A12-PY'))
from a12_ppt.config import get_settings
from a12_ppt.batch_sources import parse_docx

OUT=ROOT/'artifacts/赛前补充验收20261106'
OUT.mkdir(parents=True,exist_ok=True)
log_file=logging.FileHandler(OUT/'integration.log',encoding='utf-8')
log_file.setFormatter(logging.Formatter('[%(levelname)s] %(asctime)s %(message)s'))
m.log.addHandler(log_file)
old_teacher=m.report['fixtures']['teacher_id']
m.OUT=OUT
m.report={'mock':True,'mysql':'3306/a12','storage':'local','oss':'deferred_by_user',
          'checks':[],'fixtures':{},'source':'https://docs.python.org/3.12/tutorial/index.html'}
if (OUT/'result.json').exists():m.report=json.loads((OUT/'result.json').read_text(encoding='utf-8'))
m.actors.update({'admin':{'user_id':1,'token':''}})


def setup():
    for _ in range(30):
        try:
            m.call(m.JAVA,'/users/me');break
        except Exception:time.sleep(1)
    for actor,username in [('teacher','mock_targets_20261106'),('second','mock_parallel_20261106')]:
        users=m.rows(m.call(m.JAVA,'/admin/users?keyword='+username+'&size=20'))
        user=next((u for u in users if u['username']==username),None)
        if not user:
            user=m.call(m.JAVA,'/admin/users','POST',{'username':username,'password':os.environ['A12_TEST_PASSWORD'],
                'real_name':'MOCK并发教师','roles':'["teacher"]','email':username+'@example.invalid'})
        m.actors[actor]=m.call(m.JAVA,'/auth/login','POST',{'username':username,'password':os.environ['A12_TEST_PASSWORD']},actor=None)
    m.report['fixtures']['teachers']={a:m.actors[a]['user_id'] for a in ('teacher','second')}
    m.report.setdefault('strategy_before',m.call(m.PY,'/agent-evolution')['release']);m.persist()


def upload(content,name,actor):
    response=m.client.post(m.PY+'/resources/upload?word_conversion=true',headers=m.headers(actor),
        files={'file':(name,content,'application/vnd.openxmlformats-officedocument.wordprocessingml.document')})
    assert response.status_code==200
    return response.json()['data']['resource_id']


def audio():
    with m.stage('real_asr_and_batch_intent_plan'):
        blob=(OUT/'教学计划语音.wav').read_bytes()
        started=time.perf_counter()
        response=m.client.post(m.PY+'/audio/asr',headers=m.headers('second'),files={'file':('lesson.wav',blob,'audio/wav')},data={'language':'zh'})
        assert response.status_code==200,f'ASR HTTP {response.status_code}'
        result=response.json()['data'];assert result['status']=='completed' and result['text']
        (OUT/'语音真实转写.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        m.log.info('ASR verified model=%s elapsed_ms=%d chars=%d',result['model'],round((time.perf_counter()-started)*1000),len(result['text']))
        route=m.call(m.PY,'/workspace/chat/route','POST',{'user_id':str(m.actors['second']['user_id']),
            'messages':[{'role':'user','content':result['text']}],'route_preference':'auto'},actor='second')
        assert route['route']=='batch'
        plan=m.call(m.PY,'/batch-presentations/plans','POST',{'message':result['text']},actor='second')
        assert len(plan['items'])==2 and not plan.get('needs_input')
        assert all((i['min_pages'],i['max_pages'])==(2,2) for i in plan['items'])
        m.report['fixtures']['audio_plan']=plan['id'];m.persist()
        empty=m.client.post(m.PY+'/audio/asr',headers=m.headers('second'),files={'file':('empty.wav',b'','audio/wav')})
        assert empty.status_code==400


def prepare(actor,count,pages):
    prior=m.report['fixtures'].get(actor)
    if prior:return m.call(m.PY,f"/batch-presentations/plans/{prior['plan_id']}",actor=actor)
    blob=(OUT/'Python完整短课程_含表格与插图.docx').read_bytes()
    rid=upload(blob,'MOCK完整课程.docx',actor)
    plan=m.call(m.PY,'/batch-presentations/plans','POST',{'message':'[MOCK补充验收] 大学一年级计算机，按这份自编Python课程逐章生成，每章'+str(pages)+'页','resource_ids':[rid]},actor=actor)
    assert len(plan['items'])==6 and sum(i['image_count'] for i in plan['items'])==12
    original=m.client.get(m.PY+f"/batch-presentations/plans/{plan['id']}/source",headers=m.headers(actor))
    assert original.status_code==200 and original.content==blob
    selected=plan['items'][:count]
    items=[{k:i.get(k,'') for k in ('id','title','hours','objectives')}|{'min_pages':pages,'max_pages':pages} for i in selected]
    plan=m.call(m.PY,f"/batch-presentations/plans/{plan['id']}",'PATCH',{'revision':plan['revision'],'title':plan['title'],'subject':'计算机',
        'grade':'大一','textbook_version':'MOCK自编六章短课程','reasoning_effort':'low','items':items},actor=actor)
    stale=m.client.patch(m.PY+f"/batch-presentations/plans/{plan['id']}",headers=m.headers(actor),json={'revision':plan['revision']-1,
        'title':plan['title'],'subject':'计算机','grade':'大一','items':items})
    assert stale.status_code==409
    m.report['fixtures'][actor]={'plan_id':plan['id'],'items':count,'pages':pages};m.persist()
    return plan


def boundaries():
    with m.stage('batch_budget_and_ownership_boundaries'):
        d=Document()
        for i in range(25):d.add_heading(f'第{i+1}章 测试主题',1);d.add_paragraph('本章为配额验证样例，不执行生成。')
        data=io.BytesIO();d.save(data)
        rid=upload(data.getvalue(),'MOCK配额边界.docx','second')
        plan=m.call(m.PY,'/batch-presentations/plans','POST',{'message':'大一计算机，测试规划边界','resource_ids':[rid]},actor='second')
        assert len(plan['items'])==25
        response=m.client.post(m.PY+f"/batch-presentations/plans/{plan['id']}/confirm",headers=m.headers('second'),
            json={'revision':plan['revision'],'item_ids':[i['id'] for i in plan['items']]})
        assert response.status_code==422
        items=[{k:i.get(k,'') for k in ('id','title','hours','objectives')}|{'min_pages':30,'max_pages':30} for i in plan['items'][:9]]
        plan=m.call(m.PY,f"/batch-presentations/plans/{plan['id']}",'PATCH',{'revision':plan['revision'],'title':plan['title'],'subject':'计算机','grade':'大一','items':items},actor='second')
        response=m.client.post(m.PY+f"/batch-presentations/plans/{plan['id']}/confirm",headers=m.headers('second'),
            json={'revision':plan['revision'],'item_ids':[i['id'] for i in plan['items']]})
        assert response.status_code==409
        assert m.call(m.PY,f"/batch-presentations/plans/{plan['id']}",actor='second')['status']=='draft'
        m.report['fixtures']['boundary_plan']=plan['id']


def concurrent_batches():
    with m.stage('complex_word_six_chapters_and_two_teachers'):
        parsed=parse_docx((OUT/'Python完整短课程_含表格与插图.docx').read_bytes(),'course.docx')
        assert parsed['image_count']==12
        assert all('嵌套表格' in c['children'][0]['text'] for c in parsed['chapters'])
        plans={'teacher':prepare('teacher',6,2),'second':prepare('second',2,1)}
        for actor,plan in plans.items():
            if plan['status']=='draft':
                m.call(m.PY,f"/batch-presentations/plans/{plan['id']}/confirm",'POST',{'revision':plan['revision'],'item_ids':[i['id'] for i in plan['items']]},actor=actor)
            other='second' if actor=='teacher' else 'teacher'
            denied=m.client.get(m.PY+f"/batch-presentations/batches/{plan['id']}",headers=m.headers(other))
            assert denied.status_code==404
        bids=[p['id'] for p in plans.values()];maximum=m.report.get('max_simultaneous',0);latest={}
        for _ in range(300):
            with ThreadPoolExecutor(max_workers=2) as pool:
                states=dict(zip(plans,pool.map(lambda a:m.call(m.PY,f"/batch-presentations/batches/{plans[a]['id']}",actor=a),plans)))
            with psycopg.connect(get_settings().postgres_dsn,row_factory=dict_row) as conn:
                running=conn.execute("SELECT user_id,count(*) AS n FROM a12_batch_item WHERE batch_id=ANY(%s) AND status='running' GROUP BY user_id",(bids,)).fetchall()
            assert all(row['n']<=1 for row in running)
            maximum=max(maximum,sum(r['n'] for r in running));assert maximum<=2
            for actor,state in states.items():
                key=(state['status'],state['progress'])
                if latest.get(actor)!=key:m.log.info('BATCH actor=%s status=%s progress=%s concurrent=%d',actor,*key,sum(r['n'] for r in running));latest[actor]=key
            m.report['max_simultaneous']=maximum;m.persist()
            if all(s['status'] in ('completed','ready','partial_failed','cancelled') for s in states.values()):break
            time.sleep(8)
        assert maximum==2,'Two-teacher concurrency was not observed'
        for actor,batch in states.items():
            assert batch['status'] in ('completed','ready'),f'{actor}: generation failed; checkpoints retained'
            for item in batch['items']:m.call(m.PY,f"/batch-presentations/batches/{batch['id']}/items/{item['id']}/save",'POST',{},actor=actor)
            batch=m.call(m.PY,f"/batch-presentations/batches/{batch['id']}",actor=actor)
            ids=[i['project_id'] for i in batch['items']];m.report['fixtures'][actor]['project_ids']=ids;m.persist()
            for pid in ids:
                assert len(m.call(m.JAVA,f'/projects/{pid}/pages',actor=actor))==m.report['fixtures'][actor]['pages']
                assert m.call(m.JAVA,f'/projects/{pid}/versions',actor=actor)
            m.call(m.PY,f"/batch-presentations/batches/{batch['id']}/zip",'POST',{},actor=actor)
        for _ in range(120):
            states={a:m.call(m.PY,f"/batch-presentations/batches/{plans[a]['id']}",actor=a) for a in plans}
            if all(s['zip_status'] in ('ready','failed') for s in states.values()):break
            time.sleep(4)
        for actor,batch in states.items():
            assert batch['zip_status']=='ready'
            response=m.client.get(m.PY+f"/batch-presentations/batches/{batch['id']}/zip",headers=m.headers(actor));assert response.status_code==200
            name='六章完整短课程.zip' if actor=='teacher' else '第二教师并发课件.zip'
            (OUT/name).write_bytes(response.content)
            with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                ppt=[n for n in archive.namelist() if n.endswith('.pptx')];assert len(ppt)==m.report['fixtures'][actor]['items']
                for n in ppt:
                    with zipfile.ZipFile(io.BytesIO(archive.read(n))) as deck:
                        slides=[s for s in deck.namelist() if s.startswith('ppt/slides/slide') and s.endswith('.xml')]
                        assert len(slides)==m.report['fixtures'][actor]['pages'] and any('<a:t>' in deck.read(s).decode() for s in slides)


if __name__=='__main__':
    m.persist()
    try:
        setup()
        done={c['stage'] for c in m.report['checks'] if c['status']=='passed'}
        if 'real_asr_and_batch_intent_plan' not in done:audio()
        if 'batch_budget_and_ownership_boundaries' not in done:boundaries()
        if 'complex_word_six_chapters_and_two_teachers' not in done:concurrent_batches()
        assert m.call(m.PY,'/agent-evolution')['release']==m.report['strategy_before']
        m.report['success']=True;m.persist();m.log.info('ALL EXTENDED LOCAL ACCEPTANCE CHECKS PASSED; OSS DEFERRED BY USER')
    finally:m.client.close()
