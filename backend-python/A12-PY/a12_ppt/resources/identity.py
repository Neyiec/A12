import hashlib

from ..models import ResourceIndexSyncRequest


def resource_key(source_type: str, resource_id: str) -> str:
    return f"{source_type}:{resource_id}"


def resource_fingerprint(request: ResourceIndexSyncRequest) -> str:
    # Java 传入的是带签名的临时下载 URL，查询参数（签名/过期时间）每次都不同，
    # 指纹必须基于不含查询参数的稳定地址，否则每次同步都会被误判为文件已变更而强制重解析
    stable_url = (request.file_url or "").split("?", 1)[0]
    raw = "|".join([
        request.source_type,
        request.resource_id,
        stable_url,
        str(request.file_size or ""),
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
