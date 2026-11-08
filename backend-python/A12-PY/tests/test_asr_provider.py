import asyncio
import json
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
from openai import AsyncOpenAI as RealClient
import pytest
from a12_ppt.asr import service


def settings(model):
    return SimpleNamespace(asr_api_key='private-key',asr_base_url='https://speech.example.invalid/v1',
                           asr_model=model,request_timeout_seconds=9)


@pytest.mark.parametrize('model,endpoint',[('qwen3-asr-flash','/v1/chat/completions'),('whisper-1','/v1/audio/transcriptions')])
def test_provider_protocol_and_connection_cleanup(monkeypatch,tmp_path,model,endpoint,caplog):
    path=tmp_path/'voice.wav';path.write_bytes(b'private-audio-bytes');clients=[]
    def respond(request):
        assert request.url.path==endpoint
        if model.startswith('qwen'):
            body=json.loads(request.content)
            assert body['messages'][0]['content'][0]['input_audio']['data'].startswith('data:audio/')
            assert body['asr_options']['language']=='zh'
            return httpx.Response(200,json={'id':'asr','created':0,'object':'chat.completion','model':model,
                'choices':[{'index':0,'finish_reason':'stop','message':{'role':'assistant','content':'按计划批量生成'}}]})
        return httpx.Response(200,json={'text':'按计划批量生成','segments':[{'start':0,'end':1,'text':'按计划批量生成'}]})
    def client_factory(**kwargs):
        transport=httpx.AsyncClient(transport=httpx.MockTransport(respond))
        clients.append(transport);return RealClient(**kwargs,http_client=transport)
    monkeypatch.setattr(service,'get_settings',lambda:settings(model))
    monkeypatch.setattr(service,'require_active_browser_token',AsyncMock())
    monkeypatch.setattr(service,'AsyncOpenAI',client_factory)
    with caplog.at_level(logging.INFO,logger=service.__name__):value=asyncio.run(service.transcribe_audio(path,'zh'))
    assert value['status']=='completed' and value['text']=='按计划批量生成'
    assert clients[0].is_closed
    if model.startswith('qwen'):assert value['segments']==[]
    assert 'elapsed_ms=' in caplog.text and 'private-key' not in caplog.text and 'private-audio' not in caplog.text


def test_auth_failure_is_logged_once_without_provider_payload(monkeypatch,tmp_path,caplog):
    path=tmp_path/'voice.wav';path.write_bytes(b'voice');calls=[]
    def respond(request):
        calls.append(request)
        return httpx.Response(401,json={'error':{'message':'secret-provider-diagnostic','type':'authentication_error'}})
    monkeypatch.setattr(service,'get_settings',lambda:settings('whisper-1'))
    monkeypatch.setattr(service,'require_active_browser_token',AsyncMock())
    monkeypatch.setattr(service,'AsyncOpenAI',lambda **kwargs:RealClient(**kwargs,http_client=httpx.AsyncClient(transport=httpx.MockTransport(respond))))
    with caplog.at_level(logging.INFO,logger=service.__name__):value=asyncio.run(service.transcribe_audio(path))
    assert value['status']=='failed' and len(calls)==1
    assert 'ASR failed' in caplog.text and 'secret-provider-diagnostic' not in caplog.text
    assert 'secret' not in value['error_message']
