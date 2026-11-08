import asyncio
from typing import Annotated,Literal
from fastapi import APIRouter, HTTPException, Path, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import psycopg

from .direct_auth import direct_user_id, direct_bearer
from .batch_store import batch_store
from .batch_planner import create_plan, public_plan, propose, validate_item, make_item
from .batch_sources import SOURCE_DIR, flatten_nodes, node_material
from .batch_worker import save_project, request_zip, EXPORT_DIR
from .ai_runtime import use_runtime_options
from .presentation import get_template
from .job_limits import limit_job

router = APIRouter(prefix='/api/v1/python/batch-presentations')
Identifier = Annotated[str, Path(pattern=r'^[0-9a-f]{32}$')]


def owner():
    value = direct_user_id.get()
    if not value: raise HTTPException(401,'请先登录')
    return value


async def action(function,*args,**kwargs):
    try:
        return await asyncio.to_thread(function,*args,**kwargs)
    except ValueError as exc: raise HTTPException(409,str(exc)) from None
    except psycopg.Error: raise HTTPException(503,'批量任务存储暂不可用') from None


async def get_plan(plan_id):
    plan = await action(batch_store.plan,owner(),plan_id)
    if not plan: raise HTTPException(404,'计划不存在')
    return plan


class PlanRequest(BaseModel):
    message: str = Field(min_length=1,max_length=6000)
    resource_ids: list[str] = Field(default_factory=list,max_length=5)
    source_text: str = Field(default='',max_length=60000)
    session_id: str | None = Field(default=None,max_length=80)
    allow_suggested: bool = False
    single: bool = False
    enable_rag: bool = False


@router.post('/plans')
async def plan(request: PlanRequest):
    try:
        with use_runtime_options(owner(),'batch_plan',reasoning_effort='low'):
            async with limit_job('batch_plan',request.model_dump()):
                value = await create_plan(owner(),request)
        return {'code':200,'data':value}
    except ValueError as exc: raise HTTPException(409,str(exc)) from None


@router.get('/plans')
async def plans(session_id: str | None = Query(default=None,max_length=80)):
    return {'code':200,'data':[public_plan(row) for row in await action(batch_store.list_plans,owner(),session_id)]}


@router.get('/plans/{plan_id}')
async def read_plan(plan_id:Identifier):
    return {'code':200,'data':public_plan(await get_plan(plan_id))}


class ReviseRequest(BaseModel):
    revision:int = Field(ge=1)
    message:str = Field(default='',max_length=6000)
    source_text:str = Field(default='',max_length=60000)
    resource_ids:list[str] = Field(default_factory=list,max_length=5)
    allow_suggested:bool = False
    enable_rag: bool | None = None


@router.post('/plans/{plan_id}/revise')
async def revise(plan_id:Identifier,request:ReviseRequest):
    current = await get_plan(plan_id)
    if current['status'] != 'draft' or current['revision'] != request.revision:
        raise HTTPException(409,'计划已变化，请刷新后重试')
    payload = current['payload']
    try:
        if request.resource_ids:
            from .batch_planner import owned_source
            for resource_id in request.resource_ids:
                document,blob,name = await owned_source(resource_id)
                if blob:
                    payload['document'],payload['source_name'] = document,name
                    directory=SOURCE_DIR/plan_id; directory.mkdir(parents=True,exist_ok=True)
                    from hashlib import sha256
                    payload['source_file']='source-'+sha256(blob).hexdigest()[:16]+'.docx'
                    await asyncio.to_thread((directory/payload['source_file']).write_bytes,blob)
                else: payload['source_text'] = document.get('source_text','')
            payload['resource_ids']=list(dict.fromkeys([*payload.get('resource_ids',[]),*request.resource_ids]))
        source_text = request.source_text or payload.get('source_text','')
        if payload.get('needs_input') and not request.allow_suggested and not source_text and not payload.get('document'):
            raise ValueError('请上传教学计划、粘贴目录，或选择使用 AI 建议目录')
        with use_runtime_options(owner(),'batch_plan_revise',reasoning_effort='low'):
            async with limit_job('batch_plan',{'plan':plan_id,**request.model_dump()}):
                proposed = await propose(request.message or payload.get('requirements',''),payload.get('document'),source_text,
                    request.allow_suggested,payload.get('single',False),previous=None if payload.get('needs_input') else payload)
        payload = {**payload,**proposed,'source_text':source_text}
        if request.enable_rag is not None:
            payload['enable_rag'] = request.enable_rag
        saved = await action(batch_store.save_plan,owner(),payload,plan_id=plan_id,revision=request.revision)
        return {'code':200,'data':public_plan(saved)}
    except ValueError as exc: raise HTTPException(409,str(exc)) from None


class ItemEdit(BaseModel):
    id:str
    title:str = Field(min_length=1,max_length=180)
    hours:str = Field(default='',max_length=100)
    objectives:str = Field(default='',max_length=1500)
    min_pages:int = Field(ge=1,le=30)
    max_pages:int = Field(ge=1,le=30)


class PlanEdit(BaseModel):
    revision:int = Field(ge=1)
    title:str = Field(min_length=1,max_length=180)
    subject:str = Field(min_length=1,max_length=80)
    grade:str = Field(min_length=1,max_length=80)
    textbook_version:str = Field(default='',max_length=100)
    reasoning_effort:Literal['low','medium','high']='low'
    items:list[ItemEdit] = Field(min_length=1,max_length=200)


@router.patch('/plans/{plan_id}')
async def edit(plan_id:Identifier,request:PlanEdit):
    current=await get_plan(plan_id);payload=current['payload']
    old={item['id']:item for item in payload.get('items',[])}
    if len({item.id for item in request.items})!=len(request.items) or any(item.id not in old for item in request.items):
        raise HTTPException(409,'章节标识不匹配，请刷新计划')
    items=[]
    try:
        for entry in request.items:
            value={**old[entry.id],**entry.model_dump()};validate_item(value);items.append(value)
    except ValueError as exc: raise HTTPException(409,str(exc)) from None
    payload.update({'title':request.title,'subject':request.subject,'grade':request.grade,
        'textbook_version':request.textbook_version,'reasoning_effort':request.reasoning_effort,'items':items})
    return {'code':200,'data':public_plan(await action(batch_store.save_plan,owner(),payload,plan_id=plan_id,revision=request.revision))}


class SplitRequest(BaseModel):
    revision:int = Field(ge=1)
    item_id:str


@router.post('/plans/{plan_id}/split')
async def split(plan_id:Identifier,request:SplitRequest):
    current=await get_plan(plan_id);payload=current['payload'];nodes=flatten_nodes((payload.get('document') or {}).get('chapters',[]))
    item=next((item for item in payload.get('items',[]) if item['id']==request.item_id),None)
    children=[child for ref in (item or {}).get('source_node_ids',[]) for child in nodes.get(ref,{}).get('children',[])]
    if not children or not item: raise HTTPException(409,'该章没有可直接拆分的小节，请使用 AI 调整方案')
    expanded=[]
    for old in payload['items']:
        if old['id']==item['id']:
            for node in children:
                # Retain the chapter's introductory material and tables in each derived lesson.
                text,images=node_material(node)
                prefix='\n'.join(nodes[ref].get('text','') for ref in item['source_node_ids'])
                expanded.append(make_item(node['title'],prefix+'\n'+text,images,[node['id']]))
        else: expanded.append(old)
    if len(expanded)>24: raise HTTPException(409,'拆分后超过24份，请分批规划')
    payload['items']=expanded
    return {'code':200,'data':public_plan(await action(batch_store.save_plan,owner(),payload,plan_id=plan_id,revision=request.revision))}


class ConfirmRequest(BaseModel):
    revision:int = Field(ge=1)
    item_ids:list[str] = Field(min_length=1,max_length=24)
    theme:str = Field(default='素白风',min_length=1,max_length=80)
    accept_suggested:bool=False
    enable_rag: bool | None = None


@router.post('/plans/{plan_id}/confirm')
async def confirm(plan_id:Identifier,request:ConfirmRequest):
    current=await get_plan(plan_id)
    payload=current['payload']
    if not payload.get('subject') or not payload.get('grade'):
        raise HTTPException(409,'请先填写学科和适用年级并保存计划')
    if get_template(request.theme).get('_missing_template'):
        raise HTTPException(409,'模板不存在或已停用')
    batch_id=await action(batch_store.confirm,owner(),plan_id,request.revision,request.item_ids,request.theme,request.accept_suggested,request.enable_rag)
    return {'code':200,'data':await action(batch_store.get,owner(),batch_id)}


@router.get('/batches')
async def batches():
    return {'code':200,'data':await action(batch_store.list,owner())}


@router.get('/batches/{batch_id}')
async def batch(batch_id:Identifier):
    value=await action(batch_store.get,owner(),batch_id)
    if not value: raise HTTPException(404,'批次不存在')
    return {'code':200,'data':value}


async def owned_item(batch_id,item_id):
    item=await action(batch_store.item,owner(),batch_id,item_id)
    if not item: raise HTTPException(404,'章节任务不存在')
    return item


@router.post('/batches/{batch_id}/items/{item_id}/retry')
async def retry(batch_id:Identifier,item_id:Identifier):
    await action(batch_store.retry,owner(),batch_id,item_id)
    return {'code':200}


@router.post('/batches/{batch_id}/cancel')
async def cancel(batch_id:Identifier):
    await batch(batch_id)
    await action(batch_store.cancel,owner(),batch_id)
    return {'code':200}


@router.post('/batches/{batch_id}/items/{item_id}/save')
async def save(batch_id:Identifier,item_id:Identifier):
    item=await owned_item(batch_id,item_id)
    if item['status'] not in ('ready','completed'): raise HTTPException(409,'本章还没有生成完成')
    parent=await action(batch_store.get,owner(),batch_id);item['course_title']=parent['title']
    try:
        await save_project(item,direct_bearer.get())
    except Exception as exc:
        if isinstance(exc,HTTPException): raise
        raise HTTPException(503,'课件已保留，保存个人项目暂未成功，请重试') from None
    return {'code':200,'data':await action(batch_store.get,owner(),batch_id)}


@router.post('/sync-ready')
async def sync_ready():
    owner_id=owner();saved=0;attempted=0
    for parent in await action(batch_store.list,owner_id):
        for value in parent['items']:
            if value['status']!='ready': continue
            if attempted>=3:return {'code':200,'data':{'saved':saved}}
            attempted+=1
            item=await action(batch_store.item,owner_id,parent['id'],value['id']);item['course_title']=parent['title']
            try:
                if await asyncio.wait_for(save_project(item,direct_bearer.get()),20):saved+=1
            except Exception:
                # Do not scan every pending chapter while the business service is unavailable.
                # The task panel retains explicit synchronization and idempotent retries.
                return {'code':200,'data':{'saved':saved}}
    return {'code':200,'data':{'saved':saved}}


class ZipRequest(BaseModel):
    include_partial:bool=False


@router.post('/batches/{batch_id}/zip')
async def zip_request(batch_id:Identifier,request:ZipRequest):
    await action(request_zip,owner(),batch_id,request.include_partial)
    return {'code':200}


@router.get('/batches/{batch_id}/zip')
async def zip_download(batch_id:Identifier):
    value=await action(batch_store.get,owner(),batch_id)
    path=EXPORT_DIR/(batch_id+'.zip')
    if not value or value['zip_status']!='ready' or not path.exists(): raise HTTPException(404,'ZIP 尚未准备好')
    return FileResponse(path,filename='课程课件批次.zip',media_type='application/zip')


@router.get('/plans/{plan_id}/source')
async def original(plan_id:Identifier):
    value=await get_plan(plan_id)
    path=SOURCE_DIR/plan_id/value['payload'].get('source_file','source.docx')
    if not path.exists(): raise HTTPException(404,'本计划没有保留 Word 原件')
    return FileResponse(path,filename='原始教学计划.docx',media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
