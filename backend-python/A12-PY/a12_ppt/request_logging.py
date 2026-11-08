"""Console request summaries without bodies, query strings, credentials or model prompts."""
import logging
import time
from uuid import uuid4

logger=logging.getLogger(__name__)


async def log_request(request,call_next):
    request_id=uuid4().hex[:16]
    started=time.perf_counter()
    try:
        response=await call_next(request)
    except Exception as exc:
        logger.error('HTTP failed request_id=%s method=%s path=%s elapsed_ms=%d error_type=%s',
            request_id,request.method,request.url.path,round((time.perf_counter()-started)*1000),type(exc).__name__)
        raise
    log=logger.error if response.status_code>=500 else logger.info
    log('HTTP completed request_id=%s method=%s path=%s status=%d headers_ms=%d streaming=%s',
        request_id,request.method,request.url.path,response.status_code,
        round((time.perf_counter()-started)*1000),'text/event-stream' in response.headers.get('content-type',''))
    response.headers['X-Request-ID']=request_id
    return response
