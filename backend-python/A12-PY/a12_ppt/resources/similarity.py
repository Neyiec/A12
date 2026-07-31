import math
import re


def embedding_to_pgvector(embedding: list[float] | None) -> str | None:
    if not embedding:
        return None
    return "[" + ",".join(f"{float(value):.8f}" for value in embedding) + "]"


def cosine_similarity(left: list[float] | None, right: list[float] | None) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def keyword_score(text: str, query: str) -> float:
    keywords = [word.lower() for word in re.findall(r"[\w\u4e00-\u9fff]+", query or "") if len(word) > 1]
    if not keywords:
        return 0.0
    lower = text.lower()
    return float(sum(1 for keyword in keywords if keyword in lower))
