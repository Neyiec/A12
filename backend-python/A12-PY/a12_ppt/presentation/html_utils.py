import re


STRUCTURAL_TAGS = ("html", "body", "div", "section", "main", "header", "article", "table")
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


def looks_like_markup(text: str) -> bool:
    lowered = (text or "").lower()
    if not lowered:
        return False
    if "<!doctype html" in lowered or "<html" in lowered:
        return True
    return any(f"<{tag}" in lowered and f"</{tag}>" in lowered for tag in STRUCTURAL_TAGS)


def pick_best_document(candidates: list[str]) -> str:
    documents: list[str] = []
    fragments: list[str] = []
    for candidate in candidates:
        candidate = (candidate or "").strip()
        lowered = candidate.lower()
        if not candidate:
            continue
        if "<!doctype html" in lowered or "<html" in lowered:
            documents.append(candidate)
        elif looks_like_markup(candidate):
            fragments.append(candidate)
    pool = [doc for doc in documents if "</html>" in doc.lower()] or documents
    if not pool:
        return fragments[-1] if fragments else ""
    maximal = [doc for doc in pool if not any(doc != other and doc in other for other in pool)]
    return (maximal or pool)[-1]


def strip_think_tags(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL | re.IGNORECASE)


def clean_html_response(raw_content: str) -> str:
    content = strip_think_tags(raw_content).strip()
    candidates = [
        match.group(1)
        for match in re.finditer(r"```(?:html|HTML)?[ \t]*\r?\n(.*?)```", content, re.DOTALL)
    ]
    candidates += [
        match.group(0)
        for match in re.finditer(r"<!DOCTYPE html.*?</html>", content, re.DOTALL | re.IGNORECASE)
    ]
    candidates += [
        match.group(0)
        for match in re.finditer(r"<html.*?</html>", content, re.DOTALL | re.IGNORECASE)
    ]
    best = pick_best_document(candidates)
    if best:
        return best.strip()
    return content if looks_like_markup(content) else ""


def auto_close_basic_tags(html: str) -> str:
    if not html:
        return html
    open_tags = [m.group(1).lower() for m in re.finditer(r"<([a-zA-Z][\w:-]*)\b(?![^>]*\/>)", html)]
    close_tags = [m.group(1).lower() for m in re.finditer(r"</([a-zA-Z][\w:-]*)>", html)]
    for tag in ("body", "html"):
        if tag in open_tags and tag not in close_tags:
            html += f"</{tag}>"
    return html


def validate_html(html: str, strict: bool = False) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    lowered = (html or "").lower()
    if not looks_like_markup(html):
        errors.append("HTML 缺少可识别的结构化标签")
        return {"valid": False, "errors": errors, "warnings": warnings}

    if "<!doctype html" not in lowered:
        warnings.append("建议以 <!DOCTYPE html> 开头")
    for tag in ("html", "head", "body"):
        if f"<{tag}" not in lowered:
            errors.append(f"缺少 <{tag}> 标签")
        if f"</{tag}>" not in lowered:
            errors.append(f"缺少 </{tag}> 标签")

    if lowered.find("<head") > lowered.find("<body") and "<body" in lowered:
        warnings.append("<head> 应出现在 <body> 之前")

    if "1280" not in lowered and "aspect-ratio" not in lowered and "16 / 9" not in lowered and "16/9" not in lowered:
        errors.append("缺少 1280x720 或 16:9 固定画布约束")
    if "overflow:hidden" not in lowered.replace(" ", "") and "overflow: hidden" not in lowered:
        warnings.append("建议给 body 或主 slide 容器设置 overflow:hidden")
    if "height: 100vh" in lowered and "1280" not in lowered:
        warnings.append("仅使用 100vh 可能导致不同设备比例漂移，建议固定 1280x720 或 aspect-ratio")

    malformed_tags = re.findall(r"<[^>]*<[^>]*>", html or "")
    if malformed_tags:
        errors.append("发现格式错误的 HTML 标签")

    if strict:
        if "http://" in lowered:
            warnings.append("严格模式建议避免非 HTTPS 资源")
        if len(html) < 1800:
            warnings.append("HTML 较短，可能视觉完成度不足")
        if "<style" not in lowered:
            warnings.append("缺少 <style>，可能无法形成完整 PPT 版式")

    return {"valid": not errors, "errors": errors, "warnings": warnings}

