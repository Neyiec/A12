import asyncio
import html
import json
import logging
import uuid
from typing import Any

from ..llm import LLMClient
from ..models import InteractiveModuleGenerateRequest
from ..presentation.html_utils import auto_close_basic_tags, clean_html_response, validate_html

logger = logging.getLogger("a12_ppt.interactive")

# 三处超时必须协同，任何一层先超时都会让前端把请求中断成「已取消」：
# - MODEL_GENERATION_TIMEOUT_SECONDS：服务端等待模型的上限（6 分钟），超时回退本地模板；
# - MODEL_REQUEST_TIMEOUT_SECONDS：模型 HTTP 超时，略小于等待上限，保证先由模型层报错并记录日志；
# - teacher.js 的 INTERACTIVE_MODULE_GENERATION_TIMEOUT：前端 axios 上限（6.5 分钟，留网络余量）。
MODEL_GENERATION_TIMEOUT_SECONDS = 360.0
MODEL_REQUEST_TIMEOUT_SECONDS = 350.0


class InteractiveModuleGenerator:
    def __init__(self) -> None:
        self.llm = LLMClient()

    async def generate(self, request: InteractiveModuleGenerateRequest) -> dict[str, Any]:
        markup = ""
        degraded_reason = ""
        if self.llm.available:
            try:
                markup = await asyncio.wait_for(
                    self._generate_with_model(request), timeout=MODEL_GENERATION_TIMEOUT_SECONDS
                )
            except asyncio.TimeoutError:
                degraded_reason = "model_timeout"
                logger.warning(
                    "H5 模块生成超过 %.0f 秒，回退本地模板：title=%s",
                    MODEL_GENERATION_TIMEOUT_SECONDS,
                    request.title,
                )
            except Exception as exc:  # noqa: BLE001 - 任何模型异常都不应阻塞教师使用降级模板
                degraded_reason = "model_failed"
                logger.warning("H5 模块模型生成失败，回退本地模板：%s", str(exc)[:200])
        model_used = self.llm.available and bool(markup)
        if not markup:
            if self.llm.available and not degraded_reason:
                degraded_reason = "model_empty"
            markup = self._fallback_html(request)
        return {
            "module_id": f"interactive_{uuid.uuid4().hex[:12]}",
            "title": request.title,
            "module_type": request.module_type,
            "topic": request.topic,
            "html": markup,
            "embed_mode": request.embed_mode,
            "usage_suggestions": self._usage_suggestions(request),
            "metadata": {
                "model_used": model_used,
                "theme": request.theme,
                "standalone": request.embed_mode == "standalone",
                "degraded_reason": degraded_reason or None,
            },
        }

    async def _generate_with_model(self, request: InteractiveModuleGenerateRequest) -> str:
        prompt = f"""
请生成一个可嵌入 HTML PPT 的 HTML5 教学互动模块。
只返回完整 HTML，不要 Markdown，不要解释。

要求:
1. 固定 1280x720 画布，body overflow:hidden。
2. 使用纯 HTML/CSS/JavaScript，不依赖外部网络资源。
3. 必须有明确的交互状态、按钮、反馈、计分或动画进度。
4. 适合教师课堂展示，文本不溢出，视觉精致。
5. 如果是小游戏，需要可玩、可重置、能给即时反馈。
6. 如果是动画，需要有播放/暂停/重播控制，并表现知识点过程。

请求:
{json.dumps(request.model_dump(), ensure_ascii=False, indent=2, default=str)}
""".strip()
        # 模型异常向上冒泡，由 generate() 统一标记 model_failed；
        # 只有「模型返回了内容但 HTML 校验不通过」才在这里返回空串（标记 model_empty）。
        raw = await self.llm.complete(
            "你是教学 HTML5 动画和小游戏开发专家，只输出完整 HTML。",
            prompt,
            0.45,
            timeout_seconds=MODEL_REQUEST_TIMEOUT_SECONDS,
        )
        markup = auto_close_basic_tags(clean_html_response(raw))
        return markup if validate_html(markup, strict=False)["valid"] else ""

    def _fallback_html(self, request: InteractiveModuleGenerateRequest) -> str:
        if request.module_type in {"quiz_game", "matching_game", "timeline_game"}:
            return self._fallback_game(request)
        return self._fallback_animation(request)

    def _fallback_animation(self, request: InteractiveModuleGenerateRequest) -> str:
        points = request.knowledge_points or [request.topic, "观察变化", "总结规律"]
        point_cards = "".join(
            f'<div class="step" data-step="{index}"><b>{index}</b><span>{html.escape(str(point))}</span></div>'
            for index, point in enumerate(points[:5], 1)
        )
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{html.escape(request.title)}</title>
<style>
*{{box-sizing:border-box}}html,body{{margin:0;width:100%;height:100%;font-family:"Microsoft YaHei",Arial,sans-serif;background:#f8fafc;overflow:hidden;color:#111827}}
.stage{{width:1280px;height:720px;padding:48px 64px;background:linear-gradient(135deg,#ffffff,#eef6ff);position:relative;overflow:hidden}}
.stage:before{{content:"";position:absolute;right:-120px;top:-140px;width:420px;height:420px;border-radius:50%;background:rgba(59,130,246,.14)}}
header{{position:relative;z-index:2;display:flex;justify-content:space-between;align-items:flex-start;border-bottom:1px solid rgba(15,23,42,.12);padding-bottom:22px}}
h1{{font-size:44px;line-height:1.12;margin:0;max-width:850px}}.tag{{font-size:18px;color:#2563eb;font-weight:700}}
.canvas{{position:relative;z-index:2;height:430px;margin-top:34px;display:grid;grid-template-columns:390px 1fr;gap:34px;align-items:center}}
.process{{height:360px;position:relative;border:1px solid rgba(37,99,235,.22);background:rgba(255,255,255,.72);border-radius:8px;padding:22px;overflow:hidden}}
.orb{{width:86px;height:86px;border-radius:50%;background:#2563eb;position:absolute;left:30px;top:136px;box-shadow:0 16px 32px rgba(37,99,235,.24);transition:transform .55s ease,background .35s ease}}
.path{{position:absolute;left:70px;right:50px;top:178px;height:4px;background:linear-gradient(90deg,#2563eb,#16a34a)}}
.label{{position:absolute;bottom:28px;left:28px;right:28px;font-size:24px;font-weight:700;color:#1e293b}}
.steps{{display:grid;gap:16px}}.step{{display:grid;grid-template-columns:54px 1fr;gap:14px;align-items:center;background:white;border:1px solid rgba(15,23,42,.1);border-radius:8px;padding:16px 18px;font-size:22px;transition:.25s}}
.step b{{width:44px;height:44px;display:grid;place-items:center;background:#e0ecff;color:#2563eb;border-radius:50%}}.step.active{{border-color:#2563eb;box-shadow:0 12px 28px rgba(37,99,235,.14);transform:translateX(8px)}}
.controls{{position:absolute;left:64px;right:64px;bottom:38px;display:flex;gap:12px;align-items:center}}button{{border:0;background:#111827;color:white;border-radius:6px;padding:12px 18px;font-size:18px;cursor:pointer}}.ghost{{background:#e2e8f0;color:#111827}}
.progress{{height:10px;flex:1;background:#e2e8f0;border-radius:999px;overflow:hidden}}.bar{{height:100%;width:0;background:#2563eb;transition:width .45s}}
</style>
</head>
<body>
<section class="stage">
<header><div><div class="tag">{html.escape(request.topic)}</div><h1>{html.escape(request.title)}</h1></div><div class="tag">{html.escape(request.theme or "互动动画")}</div></header>
<main class="canvas"><div class="process"><div class="path"></div><div class="orb" id="orb"></div><div class="label" id="label">点击播放，观察过程变化</div></div><div class="steps">{point_cards}</div></main>
<div class="controls"><button onclick="play()">播放</button><button class="ghost" onclick="pause()">暂停</button><button class="ghost" onclick="resetAnim()">重播</button><div class="progress"><div class="bar" id="bar"></div></div></div>
</section>
<script>
let step=0,timer=null;const steps=[...document.querySelectorAll('.step')],orb=document.getElementById('orb'),bar=document.getElementById('bar'),label=document.getElementById('label');
function render(){{steps.forEach((s,i)=>s.classList.toggle('active',i===step));orb.style.transform='translateX('+(step*74)+'px) scale('+(1+step*.06)+')';orb.style.background=step%2?'#16a34a':'#2563eb';bar.style.width=((step+1)/steps.length*100)+'%';label.textContent=steps[step]?.innerText||'完成';}}
function play(){{clearInterval(timer);timer=setInterval(()=>{{step=(step+1)%steps.length;render();}},1200);render();}}
function pause(){{clearInterval(timer)}}function resetAnim(){{clearInterval(timer);step=0;render();}}render();
</script>
</body></html>"""

    def _fallback_game(self, request: InteractiveModuleGenerateRequest) -> str:
        points = request.knowledge_points or [request.topic, "关键概念", "课堂应用"]
        cards = "".join(
            f'<button class="card" onclick="answer(this,{index == 0})">{html.escape(str(point))}</button>'
            for index, point in enumerate(points[:4])
        )
        return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><title>{html.escape(request.title)}</title>
<style>
*{{box-sizing:border-box}}html,body{{margin:0;width:100%;height:100%;font-family:"Microsoft YaHei",Arial,sans-serif;background:#0f172a;color:white;overflow:hidden}}
.stage{{width:1280px;height:720px;padding:54px 70px;background:linear-gradient(135deg,#0f172a,#1e293b);position:relative}}
h1{{font-size:46px;margin:0 0 12px}}.sub{{color:#93c5fd;font-size:22px;margin-bottom:30px}}.board{{display:grid;grid-template-columns:1fr 360px;gap:32px;height:480px}}
.question{{background:rgba(255,255,255,.08);border:1px solid rgba(147,197,253,.28);border-radius:8px;padding:32px}}
.question h2{{font-size:34px;margin:0 0 22px}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}.card{{min-height:112px;border:1px solid rgba(255,255,255,.18);background:rgba(255,255,255,.1);color:white;border-radius:8px;font-size:22px;padding:18px;text-align:left;cursor:pointer;transition:.2s}}
.card:hover{{transform:translateY(-4px);border-color:#60a5fa}}.card.good{{background:#16a34a}}.card.bad{{background:#dc2626}}.side{{background:white;color:#0f172a;border-radius:8px;padding:28px;display:flex;flex-direction:column;justify-content:space-between}}
.score{{font-size:64px;font-weight:900;color:#2563eb}}.tip{{font-size:22px;line-height:1.5;color:#334155}}button.reset{{border:0;background:#2563eb;color:white;border-radius:6px;padding:14px 18px;font-size:18px;cursor:pointer}}
</style></head><body><section class="stage"><h1>{html.escape(request.title)}</h1><div class="sub">{html.escape(request.topic)} · 课堂互动小游戏</div>
<div class="board"><main class="question"><h2>哪一项最符合本节课的核心概念？</h2><div class="grid">{cards}</div></main><aside class="side"><div><div>得分</div><div class="score" id="score">0</div></div><div class="tip" id="tip">请学生选择答案，系统会即时反馈。</div><button class="reset" onclick="resetGame()">重置</button></aside></div></section>
<script>
let score=0;function answer(el,ok){{if(el.classList.contains('good')||el.classList.contains('bad'))return;el.classList.add(ok?'good':'bad');if(ok)score+=10;document.getElementById('score').textContent=score;document.getElementById('tip').textContent=ok?'回答正确：可以请学生解释原因。':'还可以再想想：请回到知识点重新判断。';}}
function resetGame(){{score=0;document.getElementById('score').textContent=0;document.getElementById('tip').textContent='请学生选择答案，系统会即时反馈。';document.querySelectorAll('.card').forEach(c=>c.className='card');}}
</script></body></html>"""

    def _usage_suggestions(self, request: InteractiveModuleGenerateRequest) -> list[str]:
        if request.module_type == "animation":
            return ["可作为概念导入或过程演示页插入 PPT。", "课堂中先播放动画，再暂停在关键步骤提问。"]
        return ["可作为课堂巩固或小组抢答环节。", "建议教师让学生说明选择理由，而不只看对错。"]
