import hashlib

from ..models import ResourceIndexSyncRequest


def resource_key(source_type: str, resource_id: str) -> str:
    return f"{source_type}:{resource_id}"


def resource_fingerprint(request: ResourceIndexSyncRequest) -> str:
    raw = "|".join([
        request.source_type,
        request.resource_id,
        request.file_url,
        str(request.file_size or ""),
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
