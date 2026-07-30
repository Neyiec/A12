from dataclasses import dataclass
from typing import Any


@dataclass
class IndexedChunk:
    chunk_id: str
    source_type: str
    resource_id: str
    chunk_index: int
    content: str
    metadata: dict[str, Any]
