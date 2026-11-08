"""Original local DB follow-up. Creates clearly labelled fixtures via business APIs.

Requires A12_REAL_DB_CONFIRM=3306/a12 and A12_TEST_PASSWORD. Does not inject
simulated strategy metrics or alter the active prompt release in public.
"""
import io
import json
import logging
import os
import time
import zipfile
from contextlib import contextmanager
from pathlib import Path

import httpx
from docx import Document
import redis

assert os.environ.get('A12_REAL_DB_CONFIRM') == '3306/a12'
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/原库恢复后联调20261106'
OUT.mkdir(parents=True,exist_ok=True)
logging.basicConfig(level=logging.INFO,format='[%(levelname)s] %(asctime)s %(message)s',
    handlers=[logging.StreamHandler(),logging.FileHandler(OUT/'integration.log',encoding='utf-8')])
logging.getLogger('httpx').setLevel(logging.WARNING)
log=logging.getLogger('original-integration')
JAVA='http://127.0.0.1:8088/api/v1'
PY='http://127.0.0.1:8001/api/v1/python'
TAG='[MOCK原库复测20261106]'
SOURCE='https://www.moe.gov.cn/srcsite/A26/s8001/202204/t20220420_619921.html'
client=httpx.Client(timeout=180,limits=httpx.Limits(max_keepalive_connections=0))
actors={}
report={'mysql':'3306/a12','postgresql_schema':'public','redis_database':0,'checks':[],
    'fixtures':{},'note':'模拟样例通过真实业务接口写入；不注入模拟策略效果，不修改现有发布版本。'}
if (OUT/'result.json').exists():
    report=json.loads((OUT/'result.json').read_text(encoding='utf-8'))

def persist():
    (OUT/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf-8')

@contextmanager
def stage(name):
    start=time.perf_counter();log.info('START stage=%s',name)
    try:yield
    except Exception as exc:
        report['checks'].append({'stage':name,'status':'failed','error_type':type(exc).__name__})
        log.exception('FAIL stage=%s elapsed_ms=%d',name,round((time.perf_counter()-start)*1000));persist();raise
    else:
        ms=round((time.perf_counter()-start)*1000)
        report['checks'].append({'stage':name,'status':'passed','elapsed_ms':ms});persist()
        log.info('PASS stage=%s elapsed_ms=%d',name,ms)

def headers(actor):
    info=actors[actor]
    with redis.Redis.from_url('redis://127.0.0.1:6379/0',decode_responses=True) as cache:
        token=cache.get('token:user:'+str(info['user_id'])) or info['token']
    return {'Authorization':'Bearer '+token}

def call(base,path,method='GET',data=None,actor='admin'):
    start=time.perf_counter()
    r=client.request(method,base+path,json=data,headers=headers(actor) if actor else {})
    log.info('HTTP method=%s path=%s status=%s elapsed_ms=%d',method,path.split('?')[0],r.status_code,round((time.perf_counter()-start)*1000))
    assert r.status_code==200,f'HTTP {r.status_code} at {path.split("?")[0]}'
    value=r.json();assert value.get('code',200) in (0,200),f'Business code {value.get("code")} at {path.split("?")[0]}: {str(value.get("message"))[:120]}'
    return value.get('data',value)

def rows(value):return value if isinstance(value,list) else value.get('records',value.get('list',[]))

def setup():
    with stage('original_login_permissions_and_fixture_teacher'):
        actors['admin']=call(JAVA,'/auth/login','POST',{'username':'whn','password':os.environ['A12_TEST_PASSWORD']},actor=None)
        assert actors['admin']['user_id']==1
        report['baseline_projects']=call(JAVA,'/projects?size=100')
        # Keep only counts/identifiers in the report, never project bodies.
        projects=report.pop('baseline_projects')
        report['baseline_visible_projects']=len(rows(projects))
        report['strategy_release_before']=call(PY,'/agent-evolution')['release']
        users=rows(call(JAVA,'/admin/users?keyword=mock_targets_20261106&size=20'))
        user=next((u for u in users if u['username']=='mock_targets_20261106'),None)
        if not user:
            user=call(JAVA,'/admin/users','POST',{'username':'mock_targets_20261106','password':os.environ['A12_TEST_PASSWORD'],
                'real_name':'MOCK联调教师','roles':'["teacher"]','email':'mock-targets-20261106@example.invalid'})
        actors['teacher']=call(JAVA,'/auth/login','POST',{'username':user['username'],'password':os.environ['A12_TEST_PASSWORD']},actor=None)
        report['fixtures']['teacher_id']=actors['teacher']['user_id']
        call(PY,'/teacher-style/preferences',actor='teacher')
        call(JAVA,'/admin/moderation/tasks?size=100')
        call(JAVA,'/admin/public-resources?size=100')

def feedback():
    with stage('3.dedicated_mock_teacher_profile'):
        for i in range(3):
            value=call(PY,'/teacher-style/feedback','POST',{'project_id':TAG+str(i),'action':'manual_edit',
                'instruction':'MOCK测试偏好：少文字、多案例、多练习','metadata':{'mock':True}},actor='teacher')
            assert value['stored']
        value=call(PY,'/teacher-style/profile?user_id='+str(actors['teacher']['user_id']),actor='teacher')
        assert value['profile']['evidence_count']>=3
        report['profile']=value
        # Global candidates, cohorts and release history are deliberately unchanged.

def sources():
    with stage('4.original_public_upload_index_and_citation'):
        source={'source_kind':'courseware','source_type':'teacher','authority_level':'general','source_url':SOURCE,
            'source_note':'MOCK 自编课堂样例；不是课程标准原文。','version_label':'MOCK原库20261106','version_year':'2026'}
        body=(TAG+'数学课堂材料\n二次函数y=x²开口向上，顶点是原点。相似三角形对应角相等，对应边成比例。\n学生先独立预测，再解释理由。\n参考：'+SOURCE).encode('utf-8')
        rid=report['fixtures'].get('resource_id')
        if not rid:
            value=call(JAVA,'/admin/public-resources/uploads','POST',{'resource_type':'document','title':TAG+'数学参考资料','subject':'数学','grade':'九年级',
                'file_name':'MOCK原库数学.txt','file_type':'text/plain','file_size':len(body),'source_metadata':json.dumps(source,ensure_ascii=False)})
            rid=value['upload_id'];report['fixtures']['resource_id']=rid;persist()
            assert client.put(value['upload_url'],content=body,headers={'Content-Type':'text/plain'}).status_code in (200,201,204)
            call(JAVA,f'/admin/public-resources/uploads/{rid}/complete','POST',{})
        for _ in range(20):
            synced=call(PY,'/resources/index/sync','POST',{'source_type':'public','resource_id':str(rid),'title':TAG+'数学参考资料','file_type':'txt','file_url':'https://ignored.invalid/resolve-from-business-record'})
            if synced['status']!='processing':break
            time.sleep(2)
        assert synced['status'] in ('indexed','skipped')
        found=call(PY,'/resources/index/search','POST',{'resource_ids':['public:'+str(rid)],'query':'二次函数顶点和相似三角形对应边','top_k':3})
        assert found.get('matches') and any((c.get('provenance') or {}).get('version_label')==source['version_label'] for c in found.get('citations',[]))
        report['citations']=found['citations']

def review():
    with stage('2.three_domain_real_reviews_and_human_return'):
        fixtures=report['fixtures'].get('submissions',[])
        for subject,domain in ([] if fixtures else [('语文','arts'),('数学','science'),('计算机','engineering')]):
            value=call(JAVA,'/community/submissions','POST',{'content_type':'case','title':TAG+subject+'审核样例','subject':subject,'grade':'九年级',
                'description':'MOCK 自编联调内容，仅测试机审和人工复判，不代表已获得质量认可。','license':'CC BY-NC 4.0','keywords':'MOCK,联调',
                'content_data':json.dumps({'objectives':['理解二次函数顶点'],'activities':['独立预测开口方向，再说明理由'],
                    'assessment':'比较y=x²和y=-x²','mock':True},ensure_ascii=False)},actor='teacher')
            cid=value['id'];call(JAVA,f'/community/submissions/{cid}/submit','POST',{'notes':'MOCK原库复测'},actor='teacher')
            task=next(t for t in rows(call(JAVA,'/admin/moderation/tasks?size=100')) if t.get('target_id')==cid)
            fixtures.append({'id':cid,'audit_id':task['id'],'expected_domain':domain})
        report['fixtures']['submissions']=fixtures;persist()
        for _ in range(90):
            complete=True
            for item in fixtures:
                task=call(JAVA,f"/admin/moderation/tasks/{item['audit_id']}")
                if not task.get('ai_verdict'):complete=False;continue
                assert task['ai_domain']==item['expected_domain'] and task['ai_verdict']!='error'
                checks=json.loads(task['ai_report'])['checks'];assert len(checks)==4
                item.update({'verdict':task['ai_verdict'],'score':task['ai_score'],'model':task['ai_model']})
            if complete:break
            time.sleep(3)
        assert complete,'Review consumer did not finish'
        item=fixtures[0]
        call(JAVA,f"/admin/moderation/tasks/{item['audit_id']}/decisions",'POST',{'action':'rework','comment':'MOCK人工复测：请补充学科相关内容和评价依据。'})
        owned=call(JAVA,f"/community/submissions/{item['id']}",actor='teacher')
        assert 'MOCK' in json.dumps(owned,ensure_ascii=False)

def generate(single=False):
    name='6.word_single' if single else '5.two_chapter_batch'
    with stage(name):
        doc=Document();doc.add_heading(TAG+('单份数学讲义' if single else '数学教学计划'),0)
        doc.add_heading('第一章 二次函数',1);doc.add_paragraph('1课时。目标：判断y=x²与y=-x²的开口和顶点。先观察、再解释、最后练习。')
        if not single:
            doc.add_heading('第二章 相似三角形',1);doc.add_paragraph('1课时。目标：识别对应角与对应边成比例。练习计算两组对应边。')
        blob=io.BytesIO();doc.save(blob)
        (OUT/('单份讲义.docx' if single else '教学计划.docx')).write_bytes(blob.getvalue())
        previous_plan=report['fixtures'].get(name,{}).get('plan_id')
        if previous_plan:
            plan=call(PY,f'/batch-presentations/plans/{previous_plan}',actor='teacher')
            items=plan['items']
        else:
            upload=client.post(PY+'/resources/upload?word_conversion=true',headers=headers('teacher'),files={'file':('MOCK数学.docx',blob.getvalue(),'application/vnd.openxmlformats-officedocument.wordprocessingml.document')})
            assert upload.status_code==200;rid=upload.json()['data']['resource_id']
            if not single:
                route=call(PY,'/workspace/chat/route','POST',{'user_id':str(actors['teacher']['user_id']),'messages':[{'role':'user','content':'按这份教学计划批量生成整门数学课的PPT，每章一份'}],'route_preference':'auto'},actor='teacher')
                assert route['route']=='batch'
            plan=call(PY,'/batch-presentations/plans','POST',{'message':TAG+'九年级数学，每章2页','resource_ids':[rid],'single':single},actor='teacher')
            items=[{k:i.get(k,'') for k in ('id','title','hours','objectives')} | {'min_pages':2,'max_pages':2} for i in plan['items']]
            assert len(items)==(1 if single else 2)
            plan=call(PY,f"/batch-presentations/plans/{plan['id']}",'PATCH',{'revision':plan['revision'],'title':plan['title'],'subject':'数学','grade':'九年级',
                'reasoning_effort':'low','textbook_version':'MOCK自编计划','items':items},actor='teacher')
            report['fixtures'][name]={'plan_id':plan['id'],'items':len(items)};persist()
        if plan['status']=='draft':
            call(PY,f"/batch-presentations/plans/{plan['id']}/confirm",'POST',{'revision':plan['revision'],'item_ids':[i['id'] for i in plan['items']]},actor='teacher')
        bid=plan['id'];previous=None
        for _ in range(240):
            batch=call(PY,f'/batch-presentations/batches/{bid}',actor='teacher')
            state=(batch['status'],batch['progress'])
            if state!=previous:log.info('BATCH stage=%s status=%s progress=%s',name,*state);previous=state
            if batch['status'] in ('completed','ready','partial_failed','cancelled'):break
            time.sleep(5)
        assert batch['status'] in ('completed','ready'),'Generation failed; checkpoints retained'
        for i in batch['items']:call(PY,f"/batch-presentations/batches/{bid}/items/{i['id']}/save",'POST',{},actor='teacher')
        batch=call(PY,f'/batch-presentations/batches/{bid}',actor='teacher')
        ids=[i['project_id'] for i in batch['items']];report['fixtures'][name]['project_ids']=ids;persist()
        for pid in ids:
            assert len(call(JAVA,f'/projects/{pid}/pages',actor='teacher'))==2
            assert call(JAVA,f'/projects/{pid}/versions',actor='teacher')
        call(PY,f'/batch-presentations/batches/{bid}/zip','POST',{},actor='teacher')
        for _ in range(120):
            batch=call(PY,f'/batch-presentations/batches/{bid}',actor='teacher')
            if batch['zip_status'] in ('ready','failed'):break
            time.sleep(3)
        assert batch['zip_status']=='ready'
        response=client.get(PY+f'/batch-presentations/batches/{bid}/zip',headers=headers('teacher'))
        assert response.status_code==200
        target=OUT/('单份Word课件.zip' if single else '两章课件.zip');target.write_bytes(response.content)
        with zipfile.ZipFile(target) as archive:
            files=[n for n in archive.namelist() if n.endswith('.pptx')];assert len(files)==len(items)
            for n in files:
                with zipfile.ZipFile(io.BytesIO(archive.read(n))) as ppt:
                    slides=[s for s in ppt.namelist() if s.startswith('ppt/slides/slide') and s.endswith('.xml')]
                    assert len(slides)==2 and any('<a:t>' in ppt.read(s).decode() for s in slides)

if __name__=='__main__':
    persist()
    try:
        setup()
        completed={c['stage'] for c in report['checks'] if c['status']=='passed'}
        if '3.dedicated_mock_teacher_profile' not in completed:feedback()
        if '4.original_public_upload_index_and_citation' not in completed:sources()
        if '2.three_domain_real_reviews_and_human_return' not in completed:review()
        if '5.two_chapter_batch' not in completed:generate()
        if '6.word_single' not in completed:generate(True)
        with stage('preserve_existing_strategy_release'):
            after=call(PY,'/agent-evolution')['release'];assert after==report['strategy_release_before']
            report['strategy_release_after']=after
        report['success']=True;persist();log.info('ALL ORIGINAL DATABASE CHECKS PASSED')
    finally:client.close()
