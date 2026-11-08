import asyncio
import logging
import httpx
import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse,StreamingResponse
from a12_ppt.request_logging import log_request


def make_app():
    app=FastAPI();app.middleware('http')(log_request)
    @app.post('/success')
    async def success():return {'ok':True}
    @app.get('/unavailable')
    async def unavailable():return JSONResponse({'code':503},status_code=503)
    @app.get('/stream')
    async def stream():
        async def tokens():yield 'data: private model output\n\n'
        return StreamingResponse(tokens(),media_type='text/event-stream')
    @app.get('/crash')
    async def crash():raise RuntimeError('sensitive exception detail')
    return app


def test_console_summaries_include_status_and_elapsed_without_sensitive_data(caplog):
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=make_app()),base_url='http://local') as client:
            good=await client.post('/success?api_key=private-key',json={'password':'private-password'},headers={'Authorization':'Bearer private-token'})
            bad=await client.get('/unavailable')
            assert good.headers['x-request-id']!=bad.headers['x-request-id']
    with caplog.at_level(logging.INFO,logger='a12_ppt.request_logging'):asyncio.run(run())
    records=[r for r in caplog.records if r.name=='a12_ppt.request_logging']
    assert records[0].levelname=='INFO' and 'status=200' in records[0].message
    assert records[1].levelname=='ERROR' and 'status=503' in records[1].message
    assert 'headers_ms=' in records[0].message
    assert 'private' not in '\n'.join(r.message for r in records)


def test_stream_logging_distinguishes_headers_latency_from_full_generation(caplog):
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=make_app()),base_url='http://local') as client:
            response=await client.get('/stream');assert 'private model output' in response.text
    with caplog.at_level(logging.INFO,logger='a12_ppt.request_logging'):asyncio.run(run())
    assert 'streaming=True' in caplog.text and 'private model output' not in caplog.text


def test_exception_logs_type_and_path_without_exception_payload(caplog):
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=make_app()),base_url='http://local') as client:
            with pytest.raises(RuntimeError):await client.get('/crash')
    with caplog.at_level(logging.INFO,logger='a12_ppt.request_logging'):asyncio.run(run())
    assert 'error_type=RuntimeError' in caplog.text and 'path=/crash' in caplog.text
    assert 'sensitive exception detail' not in caplog.text
