"""社区 PPT 的文科、理科、工科 AI 初审；输出供 Java 业务规则裁决。"""

import json
import logging
import re
from typing import Any

from bs4 import BeautifulSoup
from langchain_core.messages import HumanMessage, SystemMessage

from .config import get_settings
from .llm.model_factory import create_chat_model


logger = logging.getLogger(__name__)
DOMAIN_SUBJECTS = {
    "arts": ("语文", "英语", "历史", "地理", "政治", "思政", "美术", "音乐", "文学", "语言"),
    "science": ("数学", "物理", "化学", "生物", "科学", "统计"),
    "engineering": ("计算机", "信息技术", "编程", "软件", "机械", "电子", "电气", "工程", "机器人", "人工智能"),
}
DOMAIN_GUIDANCE = {
    "arts": "核对史实、作品和引文语境；区分事实与观点，检查文化表达、语言准确性和讨论活动。",
    "science": "核对公式、单位、推导前提、实验安全、数据与结论的一致性；无法验证的结论标记待人工复核。",
    "engineering": "核对代码/流程可执行性、工程约束、安全操作、版本与适用环境；不可运行验证的示例标记待人工复核。",
}
CHECK_NAMES = ("学科准确性", "教学目标与年级适配", "课堂结构与互动", "安全隐私与授权")


def classify_domain(subject: str) -> str:
    normalized = str(subject or "").strip().lower()
    matched = [domain for domain, names in DOMAIN_SUBJECTS.items()
               if any(name.lower() in normalized for name in names)]
    return matched[0] if len(matched) == 1 else "unknown"


def _review_result(payload: dict[str, Any], domain: str, verdict: str, summary: str,
                   *, score: int = 0, checks: list | None = None, findings: list | None = None,
                   model: str = "") -> dict[str, Any]:
    return {"content_version": int(payload["content_version"]), "domain": domain,
            "verdict": verdict, "score": score, "summary": summary[:1000], "model": model,
            "checks": checks or [], "findings": findings or []}


def _extract_review_material(payload: dict[str, Any]) -> tuple[str, list[str]]:
    content = payload.get("content_data") or {}
    if isinstance(content, str):
        content = json.loads(content)
    if not isinstance(content, dict) or not isinstance(content.get("slides"), list) or not content["slides"]:
        raise ValueError("课件缺少可审核页面")
    slides = content["slides"]
    limitations = []
    if not str(payload.get("grade") or "").strip():
        limitations.append("未标注适用年级，需人工核验难度")
    if len(slides) > 20:
        limitations.append("课件超过 20 页，AI 只检查了前 20 页")
    chunks = []
    for index, slide in enumerate(slides[:20], 1):
        if not isinstance(slide, dict):
            limitations.append(f"第 {index} 页结构无效")
            continue
        html = str(slide.get("html") or "")
        soup = BeautifulSoup(html, "html.parser")
        if soup.find(["script", "iframe", "video", "audio", "canvas"]):
            limitations.append(f"第 {index} 页包含脚本、嵌入框或音视频，需人工核验")
        if soup.find("img"):
            limitations.append(f"第 {index} 页包含图片，AI 未核验图片实际内容与版权")
        if re.search(r"(?:background-image\s*:|url\s*\()", html, re.IGNORECASE):
            limitations.append(f"第 {index} 页可能包含背景图片，需人工核验")
        if re.search(r"(?:javascript:|\bon\w+\s*=)", html, re.IGNORECASE):
            limitations.append(f"第 {index} 页包含可执行脚本或事件属性")
        for node in soup(["script", "style"]):
            node.decompose()
        element_text = " ".join(str(element.get("content") or element.get("text") or "")
                                for element in slide.get("elements", []) if isinstance(element, dict))
        if any(str(element.get("type") or "").lower() in {"image", "video", "audio", "h5"}
               for element in slide.get("elements", []) if isinstance(element, dict)):
            limitations.append(f"第 {index} 页存在多媒体元素，需人工核验")
        text = " ".join(filter(None, [str(slide.get("title") or ""), soup.get_text(" ", strip=True),
                                      element_text, str(slide.get("notes") or "")]))
        if len(text) > 1200:
            limitations.append(f"第 {index} 页文本超过单页审核上限")
        chunks.append(f"第 {index} 页：{text[:1200]}")
    material = "\n".join(chunks)
    if re.search(r"(?:忽略.{0,10}(?:审核|上述|之前).{0,10}(?:要求|规则|指令)|ignore.{0,12}(?:previous|above).{0,12}instructions)",
                 material, re.IGNORECASE):
        limitations.append("课件文本包含疑似提示注入指令，需人工核验")
    if len(material) > 16000:
        limitations.append("课件文本超过总审核上限")
    return material[:16000], limitations


def _parse_model_json(raw: str) -> dict[str, Any]:
    cleaned = str(raw or "").strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    result = json.loads(cleaned)
    if not isinstance(result, dict):
        raise ValueError("AI 审核输出不是 JSON 对象")
    return result


async def review_content(payload: dict[str, Any]) -> dict[str, Any]:
    domain = classify_domain(payload.get("subject", ""))
    if domain == "unknown":
        return _review_result(payload, domain, "review", "学科不明确或跨学科，交由人工审核",
                              findings=[{"severity": "review", "evidence": "学科路由不唯一"}])
    try:
        material, limitations = _extract_review_material(payload)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        return _review_result(payload, domain, "fail", str(exc),
                              findings=[{"severity": "fail", "evidence": str(exc)}])
    if not material.strip():
        return _review_result(payload, domain, "review", "课件缺少可读取的文本，需人工检查")
    settings = get_settings()
    model_name = settings.openai_model_standard or settings.openai_model
    if not settings.openai_api_key:
        return _review_result(payload, domain, "error", "未配置审核模型，转人工审核")
    system = (
        "你是教学社区的课件初审 Agent。只基于给定文字做证据化检查，不能臆测图片、音视频或外部链接的内容。"
        f"你负责的学科是 {domain}。{DOMAIN_GUIDANCE[domain]}"
        "必须检查四项：学科准确性、教学目标与年级适配、课堂结构与互动、安全隐私与授权。"
        "若无法确认、资料不足或疑似版权/隐私风险，标记 review；确有严重问题标记 fail。"
        "只返回 JSON 对象：score(0-100整数), summary(简体中文), "
        "checks(数组，恰好四项，每项 name/status/evidence，status 为 pass/review/fail), "
        "findings(数组，每项 severity/evidence/suggestion)。不要输出 Markdown。"
    )
    user = json.dumps({"title": payload.get("title"), "subject": payload.get("subject"),
                       "grade": payload.get("grade"), "lesson_type": payload.get("lesson_type"),
                       "description": payload.get("description"), "license": payload.get("license"),
                       "slides_text": material}, ensure_ascii=False)
    try:
        model = create_chat_model(model_name, settings.openai_api_key, settings.openai_base_url,
                                  settings.request_timeout_seconds, 0, "low")
        response = await model.ainvoke([SystemMessage(content=system), HumanMessage(content=user)])
        parsed = _parse_model_json(response.content)
        checks = parsed.get("checks")
        if not isinstance(checks, list) or len(checks) != len(CHECK_NAMES):
            raise ValueError("AI 审核维度不完整")
        checks = [{"name": str(check.get("name") or "")[:60],
                   "status": str(check.get("status") or "review"),
                   "evidence": str(check.get("evidence") or "")[:500]}
                  for check in checks if isinstance(check, dict)]
        if len(checks) != len(CHECK_NAMES) or {check["name"] for check in checks} != set(CHECK_NAMES):
            raise ValueError("AI 审核维度名称不完整")
        findings = parsed.get("findings") if isinstance(parsed.get("findings"), list) else []
        findings = [{"severity": str(item.get("severity") or "review")[:20],
                     "evidence": str(item.get("evidence") or "")[:500],
                     "suggestion": str(item.get("suggestion") or "")[:300]}
                    for item in findings[:20] if isinstance(item, dict)]
        findings.extend({"severity": "review", "evidence": note, "suggestion": "请审核员核验原页"}
                        for note in limitations[:20])
        score = max(0, min(100, int(parsed.get("score") or 0)))
        statuses = {check["status"] for check in checks}
        if "fail" in statuses or any(item["severity"] == "fail" for item in findings):
            verdict = "fail"
        elif statuses == {"pass"} and not findings and score >= 90:
            verdict = "pass"
        else:
            verdict = "review"
        return _review_result(payload, domain, verdict, str(parsed.get("summary") or "AI 初审完成"),
                              score=score, checks=checks, findings=findings, model=model_name)
    except Exception as exc:
        logger.exception("课件 AI 初审失败，保留人工审核任务")
        return _review_result(payload, domain, "error", f"模型初审失败，转人工审核：{type(exc).__name__}",
                              model=model_name)
