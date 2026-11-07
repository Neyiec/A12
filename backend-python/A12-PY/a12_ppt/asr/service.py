"""Provider-aware speech transcription; audio and credentials never enter logs."""
import base64
import logging
import mimetypes
import time
from pathlib import Path

from openai import AsyncOpenAI, BadRequestError
from ..config import get_settings
from ..direct_auth import require_active_browser_token
logger=logging.getLogger(__name__)

async def transcribe_audio(path: Path, language: str | None = None) -> dict:
    settings=get_settings();started=time.perf_counter();model=settings.asr_model
    def result(status,text='',segments=None,error=None):
        return {'text':text,'language':language,'model':model,'status':status,'segments':segments or [],'error_message':error}
    if not settings.asr_api_key:
        logger.error('ASR unavailable reason=missing_key model=%s',model)
        return result('unavailable',error='语音识别服务尚未配置')
    await require_active_browser_token()
    logger.info('ASR started model=%s bytes=%d',model,path.stat().st_size)
    try:
        async with AsyncOpenAI(api_key=settings.asr_api_key,
            base_url=settings.asr_base_url.rstrip('/') if settings.asr_base_url else None,
            timeout=settings.request_timeout_seconds) as client:
            if model.startswith(('qwen3-asr-','qwen-asr-')):
                # Qwen-ASR uses chat/completions input_audio, not Whisper multipart.
                # Keep the encoded data URI below the provider's 10 MB input cap.
                if path.stat().st_size>7*1024*1024:
                    raise ValueError('语音文件过大，请控制在7MB以内或分段录音')
                mime=mimetypes.guess_type(path.name)[0] or 'audio/wav'
                if path.suffix.lower()=='.webm':mime='audio/webm'
                data='data:'+mime+';base64,'+base64.b64encode(path.read_bytes()).decode()
                extra={'asr_options':{'language':language}} if language else {}
                response=await client.chat.completions.create(model=model,
                    messages=[{'role':'user','content':[{'type':'input_audio','input_audio':{'data':data}}]}],extra_body=extra)
                text=response.choices[0].message.content or ''
                segments=[]  # No invented timestamps for providers returning only text.
            else:
                try:
                    with path.open('rb') as file:
                        kwargs={'model':model,'file':file,'response_format':'verbose_json','timestamp_granularities':['segment']}
                        if language:kwargs['language']=language
                        transcript=await client.audio.transcriptions.create(**kwargs)
                except BadRequestError:
                    # Do not double-call on authentication or network failures.
                    with path.open('rb') as file:
                        kwargs={'model':model,'file':file,'response_format':'json'}
                        if language:kwargs['language']=language
                        transcript=await client.audio.transcriptions.create(**kwargs)
                text=getattr(transcript,'text','') or '';segments=[]
                for item in getattr(transcript,'segments',None) or []:
                    value=item.model_dump() if hasattr(item,'model_dump') else item if isinstance(item,dict) else {}
                    segments.append({k:value.get(k) for k in ('start','end','text','speaker')})
            text=text.strip()
            if not text:raise ValueError('未识别到语音文字，请检查录音音量或重新录制')
        logger.info('ASR completed model=%s chars=%d elapsed_ms=%d',model,len(text),round((time.perf_counter()-started)*1000))
        return result('completed',text,segments)
    except Exception as exc:
        logger.error('ASR failed model=%s elapsed_ms=%d error_type=%s status=%s',
            model,round((time.perf_counter()-started)*1000),type(exc).__name__,getattr(exc,'status_code',None))
        message=str(exc) if isinstance(exc,ValueError) else '语音识别服务调用失败，请检查ASR模型、服务地址与访问权限'
        return result('failed',error=message)
