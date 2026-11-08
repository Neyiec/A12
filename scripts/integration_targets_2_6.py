"""Local, explicitly labelled fixture integration for competition targets 2–6.

Run with the project's Python venv from backend-python/A12-PY. Requires real
Java/Python/frontends and A12_TEST_PASSWORD. Strategy metrics are simulated in
the dedicated mock_targets_* schema, never the production release tables.
No bearer tokens, passwords, internal keys or request bodies are logged.
"""
import hashlib
import io
import json
import logging
import os
import sys
import time
import zipfile
from contextlib import contextmanager
from datetime import date,timedelta
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend-python/A12-PY'))
import httpx
import psycopg
import redis
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row
from docx import Document
from a12_ppt.config import get_settings

OUT=ROOT/'artifacts/目标2-6完整联调'
OUT.mkdir(parents=True,exist_ok=True)
logging.basicConfig(level=logging.INFO,format='[%(levelname)s] %(asctime)s %(message)s',
    handlers=[logging.StreamHandler(),logging.FileHandler(OUT/'integration.log',encoding='utf-8')])
logging.getLogger('httpx').setLevel(logging.WARNING)
log=logging.getLogger('integration')
JAVA=os.getenv('A12_TEST_JAVA','http://127.0.0.1:8088')+'/api/v1'
PY=os.getenv('A12_TEST_PYTHON','http://127.0.0.1:8001')+'/api/v1/python'
assert all(urlsplit(base).hostname in ('localhost','127.0.0.1','::1') for base in (JAVA,PY)), 'This fixture script is local-only'
TAG='[MOCK联调20261106]'
SCHEMA=os.environ['A12_TEST_SCHEMA']
assert SCHEMA.startswith('mock_targets_') and SCHEMA.replace('_','').isalnum()
DSN=make_conninfo(get_settings().postgres_dsn,options='-c search_path='+SCHEMA+',public')
client=httpx.Client(timeout=180,limits=httpx.Limits(max_keepalive_connections=0))
auth={}
report={'mock':True,'schema':SCHEMA,'sources':[
 {'url':'https://www.moe.gov.cn/srcsite/A26/s8001/202204/t20220420_619921.html','title':'义务教育课程方案和课程标准（2022年版）印发通知','usage':'自编测试材料的来源参考，不冒充标准全文'},
 {'url':'https://www.moe.gov.cn/srcsite/A16/s3342/202604/t20260410_1433240.html','title':'人工智能+教育行动计划（2026）','usage':'时效元数据示例参考，不据此捏造实施成效'}], 'checks':[], 'fixtures':{}}

def persist():
    (OUT/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf-8')

@contextmanager
def stage(name):
    started=time.perf_counter();log.info('START stage=%s',name)
    try:yield
    except Exception as exc:
        report['checks'].append({'stage':name,'status':'failed','error_type':type(exc).__name__})
        log.exception('FAIL stage=%s elapsed_ms=%d',name,round((time.perf_counter()-started)*1000))
        persist();raise
    else:
        elapsed=round((time.perf_counter()-started)*1000)
        report['checks'].append({'stage':name,'status':'passed','elapsed_ms':elapsed})
        log.info('PASS stage=%s elapsed_ms=%d',name,elapsed);persist()

def call(base,path,method='GET',data=None,*,headers=None,expected=(200,),**kwargs):
    if headers is None and auth:
        # Browser and CLI share only the current whn session in the isolated Redis DB.
        # Logging into the teacher UI rotates the token; never persist or print it.
        with redis.Redis.from_url(os.getenv('A12_AUTH_REDIS_URL','redis://127.0.0.1:6379/4'),decode_responses=True) as cache:
            current=cache.get('token:user:1')
        if current:auth['Authorization']='Bearer '+current
    started=time.perf_counter()
    response=client.request(method,base+path,headers=auth if headers is None else headers,json=data,**kwargs)
    log.info('HTTP method=%s path=%s status=%s elapsed_ms=%d',method,path.split('?')[0],response.status_code,round((time.perf_counter()-started)*1000))
    assert response.status_code in expected,f'{method} {path}: HTTP {response.status_code}'
    value=response.json()
    code=value.get('code',response.status_code)
    assert code in expected or code==0,f'{method} {path}: code={code}, message={str(value.get("message") or value.get("detail"))[:160]}'
    return value.get('data') if 'data' in value else value

def rows(path,value):
    return value if isinstance(value,list) else value.get('records',value.get('list',value.get('rows',[])))

def wait_services():
    for _ in range(60):
        try:
            if client.get(JAVA+'/community/items',timeout=3).status_code in (200,401,403) and client.get(PY.removesuffix('/api/v1/python')+'/docs',timeout=3).status_code==200:return
        except httpx.HTTPError:pass
        time.sleep(1)
    raise RuntimeError('Java/Python did not become ready')

def login():
    with redis.Redis.from_url(os.getenv('A12_AUTH_REDIS_URL','redis://127.0.0.1:6379/4'),decode_responses=True) as cache:
        token=cache.get('token:user:1')
    if token:auth['Authorization']='Bearer '+token
    else:
        user=call(JAVA,'/auth/login','POST',{'username':os.getenv('A12_TEST_USERNAME','whn'),'password':os.environ['A12_TEST_PASSWORD']},headers={})
        auth['Authorization']='Bearer '+user['token']
    me=call(JAVA,'/users/me');assert str(me.get('user_id',me.get('id')))=='1'
    # Verify that HTTP and direct fixture writes address the same isolated DB.
    # A production API must never receive simulated release mutations.
    marker='[MOCK] scope:'+SCHEMA
    with psycopg.connect(DSN) as conn:
        conn.execute("UPDATE a12_prompt_version SET name=%s WHERE fingerprint='builtin-v1'",(marker,))
    overview=call(PY,'/agent-evolution')
    assert any(version['name']==marker for version in overview['versions']), 'API is not connected to this isolated fixture schema'
    report['actor']='whn (local authorised test administrator)'

def submission(name,subject='数学'):
    value=call(JAVA,'/community/submissions','POST',{'content_type':'case','title':TAG+name,'subject':subject,'grade':'九年级',
        'description':'公开资料启发的自编联调样例；评分与效果数据标明模拟，不用于真实质量结论。',
        'keywords':'MOCK,联调,课程标准','license':'CC BY-NC 4.0',
        'content_data':json.dumps({'objectives':['让学生说明二次函数图像的开口与顶点'],
            'activities':['观察 y=x² 与 y=-x²，独立预测后同伴解释'],
            'assessment':'用一个例子说明对应关系，教师核对理由',
            'source_note':report['sources'][0]['url'],'mock':True},ensure_ascii=False)})
    cid=value['id'];call(JAVA,f'/community/submissions/{cid}/submit','POST',{'notes':'MOCK 本地联调'})
    tasks=rows('',call(JAVA,'/admin/moderation/tasks?size=100'))
    task=next(item for item in tasks if item.get('target_id')==cid)
    report['fixtures'].setdefault('community',[]).append({'id':cid,'audit_id':task['id'],'title':TAG+name})
    persist();return cid,task['id']

def controlled_review(aid,score,verdict='pass'):
    key={'X-A12-Internal-Key':os.environ['A12_PYTHON_INTERNAL_KEY']}
    payload=call(JAVA,f'/internal/community-review/{aid}',headers=key)
    call(JAVA,f'/internal/community-review/{aid}/result','POST',{'content_version':payload['content_version'],'domain':'science',
        'verdict':verdict,'score':score,'summary':'MOCK 边界规则测试，评分为人工构造，并非真实模型评价。','model':'MOCK-boundary-fixture',
        'checks':[{'name':n,'status':'pass','evidence':'MOCK 自编短例，用于验证业务分支'} for n in ['政治敏感','广告导流','侵权嫌疑','内容质量']], 'findings':[]},headers=key)
    return call(JAVA,f'/admin/moderation/tasks/{aid}')

def moderation():
    with stage('2.low_score_reject_and_manual_override'):
        cid,aid=submission('59分自动驳回');task=controlled_review(aid,59)
        assert task['action']=='ai_reject' and task['status']=='processed'
        call(JAVA,f'/admin/moderation/tasks/{aid}/decisions','POST',{'action':'approve','comment':'MOCK 人工复判演练，非质量认可'})
        assert call(JAVA,f'/community/items/{cid}')['status']=='public'
    with stage('2.random_sampling_and_human_review'):
        sampled=None;automatic=None;count=0
        for index in range(40):
            cid,aid=submission(f'60分抽检样例{index+1:02d}');task=controlled_review(aid,60);count+=1
            details=json.loads(task.get('ai_report') or '{}')
            if details.get('spot_check'):sampled=(cid,aid)
            if task.get('action')=='ai_approve':automatic=(cid,aid)
            if sampled and automatic:break
        assert sampled and automatic,'random branch not reached within bounded fixtures'
        call(JAVA,f'/admin/moderation/tasks/{sampled[1]}/decisions','POST',{'action':'approve','comment':'MOCK 抽检通过演练'})
        call(JAVA,f'/admin/moderation/tasks/{automatic[1]}/decisions','POST',{'action':'reject','comment':'MOCK 发布后人工抽查推翻演练'})
        metrics=call(JAVA,'/admin/moderation/metrics');report['moderation_metrics']=metrics
        report['sample_fixture_count']=count
    with stage('2.actual_model_three_domains'):
        cases=[submission('真实模型文科审核','语文'),submission('真实模型理科审核','数学'),submission('真实模型工科审核','计算机')]
        pending={aid:domain for (_,aid),domain in zip(cases,['arts','science','engineering'])}
        for _ in range(90):
            for aid,domain in list(pending.items()):
                task=call(JAVA,f'/admin/moderation/tasks/{aid}')
                if task.get('ai_verdict'):
                    assert task['ai_domain']==domain and task['ai_model']!='MOCK-boundary-fixture'
                    assert task['ai_verdict']!='error','actual model review failed'
                    assert len(json.loads(task['ai_report'])['checks'])==4
                    pending.pop(aid)
            if not pending:break
            time.sleep(3)
        assert not pending,'AI review worker did not return all three domains'

def seed_evolution_effects(release):
    with psycopg.connect(DSN,row_factory=dict_row) as conn:
        index=0;counts={'control':0,'canary':0}
        while min(counts.values())<5:
            uid='MOCK-cohort-'+str(index);index+=1
            cohort='canary' if int(hashlib.sha256(f"{uid}:{release['revision']}".encode()).hexdigest()[:8],16)%100<10 else 'control'
            if counts[cohort]>=5:continue
            run=hashlib.md5((uid+str(release['revision'])).encode()).hexdigest()
            vid=release['canary_version'] if cohort=='canary' else release['active_version']
            conn.execute("INSERT INTO a12_prompt_run(id,user_id,version_id,release_revision,cohort,status) VALUES(%s,%s,%s,%s,%s,'success')",(run,uid,vid,release['revision'],cohort))
            for action in (['revision','export_failed','export_success'] if cohort=='control' else ['export_success']):
                conn.execute('INSERT INTO a12_prompt_outcome(run_id,action,event_key) VALUES(%s,%s,%s)',(run,action,'MOCK-'+action))
            counts[cohort]+=1
    log.info('MOCK strategy outcomes inserted scope=%s counts=%s; not real efficacy evidence',SCHEMA,counts)

def evolution():
    with stage('3.feedback_profile_candidate_and_approval_gate'):
        for index in range(3):
            result=call(PY,'/teacher-style/feedback','POST',{'project_id':'MOCK-evidence-'+str(index),'action':'manual_edit',
                'instruction':'MOCK 偏好：少文字，多案例，多练习','metadata':{'mock':True}})
            assert result['stored']
        profile=call(PY,'/teacher-style/profile?user_id=1');report['profile_summary']=profile
        with psycopg.connect(DSN) as conn:
            for index in range(3):
                conn.execute("INSERT INTO a12_ai_feedback(user_id,project_id,action,instruction,metadata) VALUES(%s,%s,'manual_edit','MOCK 第二位教师风格反馈',%s::jsonb)",
                    ('MOCK-second-teacher','MOCK-extra-'+str(index),json.dumps({'mock':True,'style_signals':['less_slide_text','more_cases','more_practice']})))
        before=call(PY,'/agent-evolution')['release']
        candidate=call(PY,'/agent-evolution/candidates','POST',{})
        with psycopg.connect(DSN) as conn:conn.execute("UPDATE a12_prompt_version SET name='[MOCK] 反馈聚类候选' WHERE id=%s",(candidate['id'],))
        rejected=client.post(PY+'/agent-evolution/release',headers=auth,json={'action':'canary','version_id':candidate['id'],'expected_revision':before['revision'],'reason':'MOCK 检验人工确认闸门'})
        assert rejected.status_code==409
        call(PY,f"/agent-evolution/versions/{candidate['id']}/approve",'POST',{})
        release=call(PY,'/agent-evolution/release','POST',{'action':'canary','version_id':candidate['id'],'expected_revision':before['revision'],'reason':'MOCK 隔离库10%灰度演练'})
        rejected=client.post(PY+'/agent-evolution/release',headers=auth,json={'action':'promote','expected_revision':release['revision'],'reason':'MOCK 检验样本不足闸门'})
        assert rejected.status_code==409
        seed_evolution_effects(release)
        overview=call(PY,'/agent-evolution');assert len(overview['effects'])==2
        report['evolution']={'baseline':before['active_version'],'candidate':candidate['id'],'release':release,'metrics_simulated':True}
        persist()

def public_resources():
    with stage('4.source_registration_upload_vector_search_and_expiry'):
        source={'source_kind':'courseware','source_type':'teacher','authority_level':'general','source_url':report['sources'][0]['url'],
            'source_note':'MOCK 自编课堂材料；仅参考公开通知关于重视实践与评价的方向，不是课标原文。','version_label':'MOCK-2026-11','version_year':'2026','valid_until':''}
        text=(TAG+'二次函数与相似三角形课堂资料\n自编样例：函数 y=x² 的图像开口向上，顶点为原点。相似三角形对应角相等，对应边成比例。\n'
            '教学安排：先独立预测，再同伴解释，最后用一道迁移题检查理由。\n参考：'+report['sources'][0]['url'])
        content=text.encode('utf-8')
        request={'resource_type':'document','title':TAG+'公共数学参考资料','subject':'数学','grade':'九年级','file_name':'MOCK数学参考.txt',
            'file_type':'text/plain','file_size':len(content),'source_metadata':json.dumps(source,ensure_ascii=False)}
        invalid=client.post(JAVA+'/admin/public-resources/uploads',headers=auth,json={**request,'source_metadata':'{}'})
        value=invalid.json();assert invalid.status_code>=400 or value['code']>=400
        forged={**source,'source_type':'official','authority_level':'official','source_url':'https://untrusted.invalid/fake-notice'}
        invalid=client.post(JAVA+'/admin/public-resources/uploads',headers=auth,json={**request,'source_metadata':json.dumps(forged)})
        assert invalid.status_code>=400 or invalid.json()['code']>=400
        record=call(JAVA,'/admin/public-resources/uploads','POST',request)
        rid=record['upload_id'];report['fixtures']['public_resource']=rid;persist()
        uploaded=client.put(record['upload_url'],content=content,headers={'Content-Type':'text/plain'});assert uploaded.status_code in (200,201,204)
        call(JAVA,f'/admin/public-resources/uploads/{rid}/complete','POST',{})
        sync_request={'source_type':'public','resource_id':str(rid),'title':TAG+'公共数学参考资料','file_url':'https://ignored.invalid/forged','file_type':'txt'}
        for _ in range(15):
            synced=call(PY,'/resources/index/sync','POST',sync_request)
            if synced['status']!='processing':break
            log.info('public resource indexing already in progress; waiting for business event consumer resource=%s',rid)
            time.sleep(2)
        assert synced['status'] in ('indexed','skipped')
        query={'resource_ids':['public:'+str(rid)],'query':'二次函数图像和相似三角形对应边的关系','top_k':3}
        found=call(PY,'/resources/index/search','POST',query);assert found.get('matches')
        assert any((c.get('provenance') or {}).get('source_url')==source['source_url'] for c in found.get('citations',[]))
        report['rag_citations']=found.get('citations')
        expired={**source,'source_kind':'current_affairs','valid_until':str(date.today()-timedelta(days=1))}
        invalid=client.patch(JAVA+f'/admin/public-resources/{rid}',headers=auth,json={'source_metadata':json.dumps(expired)})
        assert invalid.status_code>=400 or invalid.json()['code']>=400,'Expired news was incorrectly accepted for publication'
        log.info('EXPECTED VALIDATION source registration, fake authority and expired publication all rejected')
        call(PY,'/resources/index/governance/patrol','POST',{})
        report['source_overview']=call(PY,'/resources/index/governance')
        # Source expiry exclusion is also exercised by the isolated DB/API regression suite.

def batch_generate(single=False):
    label='6.word_single' if single else '5.curriculum_batch'
    with stage(label):
        doc=Document();doc.add_heading(TAG+('单份Word讲义' if single else '数学教学计划'),0)
        doc.add_heading('第一章 二次函数',1);doc.add_paragraph('课时：1课时\n教学目标：理解y=x²的顶点与开口方向\n自编练习：比较y=x²与y=-x²。')
        if not single:
            doc.add_heading('第二章 相似三角形',1);doc.add_paragraph('课时：1课时\n教学目标：识别对应角与对应边比例。\n自编练习：比例为2，求对应边。')
        doc.add_paragraph('来源参考（非原文）：'+report['sources'][0]['url'])
        blob=io.BytesIO();doc.save(blob);(OUT/('单份讲义.docx' if single else '教学计划.docx')).write_bytes(blob.getvalue())
        uploaded=client.post(PY+'/resources/upload?word_conversion=true',headers=auth,files={'file':('MOCK-plan.docx',blob.getvalue(),'application/vnd.openxmlformats-officedocument.wordprocessingml.document')})
        assert uploaded.status_code==200
        rid=uploaded.json()['data']['resource_id']
        if not single:
            routed=call(PY,'/workspace/chat/route','POST',{'user_id':'1','messages':[{'role':'user','content':'按这份教学计划批量生成整门数学课的PPT，每章一份'}],'route_preference':'auto'})
            assert routed['route']=='batch'
        plan=call(PY,'/batch-presentations/plans','POST',{'message':TAG+'九年级数学，按上传的计划生成课件，每份2页','resource_ids':[rid],'single':single})
        for item in plan['items']:item['min_pages']=2;item['max_pages']=2
        plan=call(PY,f"/batch-presentations/plans/{plan['id']}",'PATCH',{'revision':plan['revision'],'title':plan['title'],'subject':'数学','grade':'九年级',
            'reasoning_effort':'low','textbook_version':'MOCK 自编，非教材目录',
            'items':[{k:item.get(k,'') for k in ('id','title','hours','objectives','min_pages','max_pages')} for item in plan['items']]})
        report['fixtures'][label]={'plan_id':plan['id'],'items':len(plan['items']),'awaiting_confirmation':True};persist()
        log.info('PLAN READY stage=%s plan_id=%s; open teacher batch task page to confirm',label,plan['id'])
        if not single and os.getenv('A12_TEST_UI_CONFIRM')=='1':
            for _ in range(100):
                current=call(PY,f"/batch-presentations/plans/{plan['id']}")
                if current['status']=='confirmed':break
                time.sleep(3)
            else:raise RuntimeError('Teacher plan was not confirmed in the UI within 5 minutes')
        else:call(PY,f"/batch-presentations/plans/{plan['id']}/confirm",'POST',{'revision':plan['revision'],'item_ids':[i['id'] for i in plan['items']]})
        bid=plan['id'];report['fixtures'][label]['awaiting_confirmation']=False;persist()
        last=None
        for _ in range(240):
            batch=call(PY,'/batch-presentations/batches/'+bid)
            state=(batch['status'],batch['progress'])
            if state!=last:log.info('BATCH stage=%s state=%s progress=%s',label,*state);last=state
            if batch['status'] in ('completed','ready','partial_failed','cancelled'):break
            time.sleep(5)
        assert batch['status'] in ('completed','ready'),'Batch generation failed; retained checkpoint for investigation'
        for item in batch['items']:call(PY,f"/batch-presentations/batches/{bid}/items/{item['id']}/save",'POST',{})
        batch=call(PY,'/batch-presentations/batches/'+bid)
        for item in batch['items']:
            pages=call(JAVA,f"/projects/{item['project_id']}/pages");assert len(pages)==2
            assert call(JAVA,f"/projects/{item['project_id']}/versions")
        report['fixtures'][label]['project_ids']=[item['project_id'] for item in batch['items']];persist()
        call(PY,f'/batch-presentations/batches/{bid}/zip','POST',{})
        for _ in range(120):
            batch=call(PY,'/batch-presentations/batches/'+bid)
            if batch['zip_status'] in ('ready','failed'):break
            time.sleep(3)
        assert batch['zip_status']=='ready'
        output=client.get(PY+f'/batch-presentations/batches/{bid}/zip',headers=auth);assert output.status_code==200
        target=OUT/('单份Word课件.zip' if single else '按章批量课件.zip');target.write_bytes(output.content)
        with zipfile.ZipFile(target) as archive:
            ppts=[name for name in archive.namelist() if name.endswith('.pptx')]
            assert len(ppts)==(1 if single else 2)
            for name in ppts:
                with zipfile.ZipFile(io.BytesIO(archive.read(name))) as ppt:
                    xml=[n for n in ppt.namelist() if n.startswith('ppt/slides/slide') and n.endswith('.xml')]
                    assert len(xml)==2 and any('<a:t>' in ppt.read(n).decode() for n in xml)

def final_release():
    with stage('3.promote_and_rollback_isolated_strategy'):
        current=call(PY,'/agent-evolution')['release']
        promoted=call(PY,'/agent-evolution/release','POST',{'action':'promote','expected_revision':current['revision'],'reason':'MOCK 隔离库，模拟指标满足发布条件'})
        assert promoted['active_version']==report['evolution']['candidate']
        restored=call(PY,'/agent-evolution/release','POST',{'action':'rollback','version_id':report['evolution']['baseline'],'expected_revision':promoted['revision'],'reason':'MOCK 演练结束恢复隔离库基线'})
        assert restored['active_version']==report['evolution']['baseline']

if __name__=='__main__':
    persist()
    try:
        with stage('environment_and_authorized_login'):wait_services();login()
        evolution();public_resources();moderation();batch_generate();batch_generate(True);final_release()
        report['success']=True;persist();log.info('ALL API INTEGRATION CHECKS PASSED; browser observations recorded separately')
    finally:client.close()
