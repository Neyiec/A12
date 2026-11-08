"""Public RAG provenance and temporal eligibility; personal material remains user scoped."""
from datetime import datetime, date
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

PUBLISHERS = ('pep.com.cn', 'hep.com.cn')


def official_host(host):
    return bool(host and (host == 'gov.cn' or host.endswith('.gov.cn')))


def publisher_host(host):
    return bool(host and any(host == root or host.endswith('.' + root) for root in PUBLISHERS))


def trusted_url(url):
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or '').lower()
        return (parsed.scheme == 'https' and not parsed.username and not parsed.password
                and parsed.port in (None, 443) and (official_host(host) or publisher_host(host)))
    except ValueError:
        return False


def assess(metadata, *, today=None):
    today = today or datetime.now(ZoneInfo('Asia/Shanghai')).date()
    source = metadata.get('provenance')
    if not isinstance(source, dict):
        return {'eligible': False, 'reasons': ['缺少来源登记'], 'weight': 0.0}
    text = lambda key: str(source.get(key) or '').strip()
    kind, origin, level = text('source_kind'), text('source_type'), text('authority_level')
    reasons = []
    if metadata.get('available') is False or metadata.get('allow_ai') is False:
        reasons.append('资源已停用或未授权 AI')
    if kind not in {'curriculum', 'textbook', 'current_affairs', 'courseware', 'other'}:
        reasons.append('缺少资料时效类型')
    if origin not in {'official', 'publisher', 'teacher', 'other'} or level not in {'official', 'publisher', 'general'}:
        reasons.append('来源类型或可信等级无效')
    url = text('source_url')
    host = ''
    if not url and not text('source_note'):
        reasons.append('缺少来源链接或说明')
    if url:
        try:
            parsed = urlsplit(url)
            host = (parsed.hostname or '').lower()
            if parsed.scheme != 'https' or not host or parsed.username or parsed.password or parsed.port not in (None, 443):
                raise ValueError()
        except ValueError:
            reasons.append('来源链接必须是 HTTPS 地址')
    if (origin == 'official' or level == 'official') and not (origin == level == 'official' and official_host(host)):
        reasons.append('官方等级与 gov.cn 白名单不符')
    if (origin == 'publisher' or level == 'publisher') and not (origin == level == 'publisher' and publisher_host(host)):
        reasons.append('出版社等级与白名单不符')
    if not text('version_label'):
        reasons.append('缺少版本或版次')
    try:
        year = int(text('version_year'))
        if not 1900 <= year <= today.year + 1:
            raise ValueError()
    except ValueError:
        reasons.append('版本年份无效')
    until = text('valid_until')
    if kind == 'current_affairs' and not until:
        reasons.append('时政资料缺少有效期')
    if until:
        try:
            parsed_date = date.fromisoformat(until)
            if parsed_date.isoformat() != until:
                raise ValueError()
            if parsed_date < today:
                reasons.append('资料已过期')
        except ValueError:
            reasons.append('有效期格式无效')
    if (metadata.get('source_check') or {}).get('status') == 'broken':
        reasons.append('来源链接已失效，需人工核对')
    if metadata.get('superseded') is True:
        reasons.append('资料已标记为被新版替代')
    return {'eligible': not reasons, 'reasons': reasons,
            'weight': {'official': 1.0, 'publisher': 0.9, 'general': 0.75}.get(level, 0.0),
            'source_kind': kind, 'version_label': text('version_label'), 'version_year': text('version_year'),
            'source_note': text('source_note'),
            'source_url': url, 'authority_level': level, 'valid_until': until,
            'ingested_at': metadata.get('ingested_at'), 'citation_host': host}


def public_sql_filter():
    # ISO dates use lexical comparison; malformed/forged metadata is revalidated in Python.
    return """AND (source_type <> 'public' OR (
      metadata->>'provenance_valid' = 'true'
      AND EXISTS (SELECT 1 FROM a12_resource_index registered
          WHERE registered.resource_key=a12_resource_index_chunk.resource_key
          AND registered.parse_status='completed' AND registered.available IS TRUE AND registered.allow_ai IS TRUE)
      AND COALESCE(metadata#>>'{source_check,status}', '') <> 'broken'
      AND COALESCE(metadata->>'superseded', 'false') <> 'true'
      AND (COALESCE(metadata#>>'{provenance,valid_until}', '') = ''
           OR metadata#>>'{provenance,valid_until}' >= to_char(NOW() AT TIME ZONE 'Asia/Shanghai','YYYY-MM-DD'))))"""
