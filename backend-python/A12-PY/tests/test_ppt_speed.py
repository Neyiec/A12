import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from a12_ppt.direct_auth import direct_user_id
from a12_ppt.models import PresentationGenerateRequest
from a12_ppt.presentation import PPTGenerator
from a12_ppt.presentation.generation_cache import GenerationCache
from a12_ppt.presentation.image_generator import GeneratedImage
from a12_ppt.presentation.prompts import slide_html_prompt


HTML = '<!doctype html><html><head><style>body{margin:0;width:1280px;height:720px;overflow:hidden}</style></head><body><section>教学内容</section></body></html>'


def test_cache_expires_is_bounded_and_returns_independent_copies():
    now = [0]
    cache = GenerationCache(max_bytes=80, ttl=10, clock=lambda: now[0])
    cache.put('a', {'body': ['a']})
    cached = cache.get('a'); cached['body'].append('changed')
    assert cache.get('a')['body'] == ['a']
    cache.put('big', 'x' * 200)
    assert cache.get('big') is None
    now[0] = 11
    assert cache.get('a') is None and cache.size == 0


def test_page_cache_is_user_scoped_and_invalidates_changed_page_material_or_theme():
    async def run():
        flow = PPTGenerator.__new__(PPTGenerator)
        flow.settings = SimpleNamespace(enable_quality_pipeline=True, quality_preset='fast', max_html_retries=1)
        flow.llm = SimpleNamespace(available=True)
        flow.generation_cache = GenerationCache()
        flow._complete_html_with_retry = AsyncMock(return_value=HTML)
        args = dict(title='函数', slide={'title':'函数定义','content_points':['定义域']},slide_no=1,total=4,
            theme='素白风',template_name='素白风',template_html='',request_context={'requirements':'多案例'},
            all_slides=[{'title':f'第{i}页'} for i in range(4)],quality_assets={})
        with patch('a12_ppt.direct_auth.require_active_browser_token',new=AsyncMock()) as auth:
            identity = direct_user_id.set('1')
            try:
                await flow._generate_slide_html(**args)
                await flow._generate_slide_html(**args)
                assert flow._complete_html_with_retry.await_count == 1
                args['all_slides'][3]['content_points'] = ['另一页的局部修改']
                await flow._generate_slide_html(**args)
                assert flow._complete_html_with_retry.await_count == 1
                await flow._generate_slide_html(**{**args,'theme':'深色风'})
                await flow._generate_slide_html(**{**args,'request_context':{'rag_context':'新教材版本'}})
                direct_user_id.set('2')
                await flow._generate_slide_html(**args)
                assert flow._complete_html_with_retry.await_count == 4
                assert auth.await_count == 6
            finally:
                direct_user_id.reset(identity)
    asyncio.run(run())


def test_images_and_html_overlap_and_image_wait_does_not_occupy_html_slot():
    async def run():
        flow = PPTGenerator.__new__(PPTGenerator)
        flow.settings=SimpleNamespace(max_slide_concurrency=1,enable_quality_pipeline=False,quality_preset='fast',max_html_retries=1,max_generated_images=1)
        flow.llm=SimpleNamespace(available=False)
        image_started, second_html = asyncio.Event(), asyncio.Event()
        async def image(*args):
            image_started.set()
            await second_html.wait()
            return GeneratedImage('', 'data:image/png;base64,aGVsbG8=', '', 'unchanged-model', 'testimage')
        async def html(**kwargs):
            if kwargs['slide_no'] == 1:
                await image_started.wait()
                return HTML.replace('教学内容', '<img src="a12-generated-image://slot-1" data-ppt-element="image">')
            second_html.set()
            return HTML
        flow.image_generator=SimpleNamespace(available=True,generate=image)
        flow._generate_slide_html=html
        flow._select_generated_image_slides=lambda *args: {1}
        req=PresentationGenerateRequest(title='函数',asset_policy='generate',stream_compact=True,
            outline={'slides':[{'title':'封面'},{'title':'函数定义'}]})
        async def collect():
            return [e async for e in flow.stream_presentation(req)]
        result=await asyncio.wait_for(collect(),2)
        final=result[-1]['response']
        assert final['metadata']['generated_image_count'] == 1
        assert final['html'] == ''
        assert 'a12-generated-image://' not in final['slides'][0]['html']
        assert 'data:image/png;base64,aGVsbG8=' in final['slides'][0]['html']
        assert final['slides'][0]['metadata']['html_validation']['sha256']
    asyncio.run(run())


def test_prompt_stays_full_html_and_preserves_teacher_constraints():
    args=dict(title='函数',theme='素白风',request_context={'requirements':'必须以校园案例引入','teacher_style_summary':'少文字、多实践'},
        template_name='素白风',template_html='x'*20000,style_genes='',global_constitution='',page_brief='',
        slide={'title':'函数定义','content_points':['定义域']},slide_no=1,total=20,all_slides=[{'title':'函数'}]*20)
    prompt=slide_html_prompt(**args)
    assert '只输出完整 HTML' in prompt
    assert '必须以校园案例引入' in prompt and '少文字、多实践' in prompt
    assert len(prompt) < 10000


def test_batch_resume_reuses_only_matching_valid_pages_and_generates_remaining_html():
    async def run():
        flow=PPTGenerator.__new__(PPTGenerator)
        flow.settings=SimpleNamespace(max_slide_concurrency=2,enable_quality_pipeline=False,quality_preset='fast',max_html_retries=1,max_generated_images=0)
        flow.llm=SimpleNamespace(available=False)
        flow._generate_slide_html=AsyncMock(return_value=HTML)
        req=PresentationGenerateRequest(title='函数',asset_policy='none',outline={'slides':[{'title':'封面'},{'title':'新知'},{'title':'练习'}]})
        saved={'1':{'slide_no':1,'title':'封面','html':HTML,'metadata':{'previous':True}},
               '2':{'slide_no':2,'title':'旧标题','html':HTML},
               '3':{'slide_no':3,'title':'练习','html':'invalid HTML'}}
        result=[event async for event in flow.stream_presentation(req,resume_slides=saved)]
        pages=result[-1]['response']['slides']
        assert flow._generate_slide_html.await_count==2
        assert pages[0]['metadata']['resumed'] and pages[0]['metadata']['previous']
        assert [call.kwargs['slide_no'] for call in flow._generate_slide_html.await_args_list]==[2,3]
    asyncio.run(run())


def test_template_and_asset_planning_cache_reuses_success_but_not_failure():
    async def run():
        flow=PPTGenerator.__new__(PPTGenerator)
        flow.settings=SimpleNamespace(max_generated_images=0)
        flow.generation_cache=GenerationCache()
        flow.llm=SimpleNamespace(available=True,complete=AsyncMock(return_value='模板风格：蓝白'))
        with patch('a12_ppt.direct_auth.require_active_browser_token',new=AsyncMock()):
            await flow._cached_style_genes('蓝白','<html>模板</html>')
            await flow._cached_style_genes('蓝白','<html>模板</html>')
            assert flow.llm.complete.await_count == 1
            flow.llm.complete=AsyncMock(return_value='{"policy":"none","slides":{}}')
            req=PresentationGenerateRequest(title='函数',outline={})
            slides=[{'title':'定义域'}]
            await flow._resolve_asset_plan(req,slides)
            await flow._resolve_asset_plan(req,slides)
            assert flow.llm.complete.await_count == 1
            flow.llm.complete=AsyncMock(side_effect=RuntimeError('provider unavailable'))
            req=req.model_copy(update={'title':'新的课程'})
            await flow._resolve_asset_plan(req,slides)
            await flow._resolve_asset_plan(req,slides)
            assert flow.llm.complete.await_count == 2
    asyncio.run(run())
