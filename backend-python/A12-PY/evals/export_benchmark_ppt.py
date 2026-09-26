"""生成并保存基准测试使用的8页可编辑PPT、HTML预览和原始JSON。"""

from __future__ import annotations

import asyncio
import json
import re
import shutil
import sys
import time
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
sys.path.insert(0, str(ROOT))

from a12_ppt.ai_runtime import use_runtime_options  # noqa: E402
from a12_ppt.models import OutlineGenerateRequest, PresentationGenerateRequest  # noqa: E402
from a12_ppt.presentation.generator import PPTGenerator  # noqa: E402
from a12_ppt.presentation.pptx_exporter import export_html_slides_to_pptx  # noqa: E402


def repair_editable_export_layout(response: dict) -> dict:
    """修正浏览器 HTML 转可编辑 PPT 时与 CSS 盒模型不一致的少数布局。"""
    slide_overrides = {
        5: """
        .slide-content-container { padding: 38px 80px !important; }
        header { margin-bottom: 22px !important; }
        main { gap: 28px !important; min-height: 0 !important; }
        .left-col { gap: 16px !important; min-height: 0 !important; }
        .right-col { gap: 12px !important; min-height: 0 !important; }
        .card { padding: 18px !important; }
        .card-header { margin-bottom: 10px !important; }
        .path-steps { font-size: 14px !important; line-height: 1.45 !important; color: var(--text-secondary); margin-bottom: 10px !important; }
        .path-steps > div { margin-bottom: 4px !important; }
        .left-col .card:nth-child(2) > div:last-child { padding: 10px !important; }
        .process-step { margin-bottom: 7px !important; }
        .step-text { font-size: 14px !important; line-height: 1.45 !important; }
        .task-area { padding: 22px !important; }
        .question-box { padding: 15px !important; margin-bottom: 12px !important; }
        .question-text { font-size: 15px !important; line-height: 1.5 !important; }
        .options-grid { gap: 10px !important; }
        .option-item { padding: 9px !important; font-size: 13px !important; }
        .feedback-section { padding-top: 10px !important; }
        footer { padding-top: 10px !important; }
        """,
        6: """
        .learner-question { border-left: 0 !important; padding-left: 0 !important; }
        """,
        7: """
        .page-title { border-left: 0 !important; padding-left: 0 !important; }
        .subtitle { padding-left: 0 !important; }
        .challenge-section { border-left: 0 !important; }
        """,
    }
    for slide in response.get("slides", []):
        slide_no = int(slide.get("slide_no") or 0)
        if slide_no == 5:
            slide["html"] = re.sub(
                r'<p style="font-size: 16px; color: var\(--text-secondary\); line-height: 1\.8; margin-bottom: 20px;">.*?</p>',
                """<div class="path-steps">
                    <div>请按照以下步骤完成今天的课堂闭环：</div>
                    <div>1. 观察示例中的<strong>实验变量</strong>。</div>
                    <div>2. 预测可能的<strong>实验结果</strong>。</div>
                    <div>3. 结合光合作用公式解释原因。</div>
                </div>""",
                slide["html"],
                count=1,
                flags=re.S,
            )
        override = slide_overrides.get(slide_no)
        if override:
            slide["html"] = slide["html"].replace("</style>", f"{override}\n</style>", 1)
    return response


async def main() -> None:
    output_dir = REPO_ROOT / "artifacts" / "ppt-benchmark"
    output_dir.mkdir(parents=True, exist_ok=True)

    generator = PPTGenerator()
    settings = replace(generator.settings, max_slide_concurrency=8, max_html_retries=0,
                       request_timeout_seconds=75)
    generator.settings = settings
    generator.llm.settings = settings

    outline_request = OutlineGenerateRequest(
        title="光合作用",
        subject="生物",
        grade="七年级",
        slide_count=8,
        requirements="包含实验、课堂互动、分层练习和出口检测",
        model_profile="fast",
        reasoning_effort="low",
    )
    outline = generator._decorate_outline(generator._fallback_outline(outline_request, 8), outline_request)["outline"]
    request = PresentationGenerateRequest(
        title="光合作用",
        outline=outline,
        asset_policy="none",
        model_profile="fast",
        reasoning_effort="low",
    )

    started = time.perf_counter()
    with use_runtime_options(operation="export_benchmark_ppt", model_profile="fast", reasoning_effort="low"):
        response = await generator.generate_presentation(request)
    response = repair_editable_export_layout(response)
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    response.setdefault("metadata", {})["generation_elapsed_ms"] = elapsed_ms

    json_path = output_dir / "光合作用-生成结果-v2.json"
    html_path = output_dir / "光合作用-HTML预览-v2.html"
    json_path.write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8")
    html_path.write_text(response["html"], encoding="utf-8")

    exported = await export_html_slides_to_pptx(
        response["title"], response["slides"], "光合作用-qwen3.7-flash-可编辑-v2.pptx",
        fidelity="dom_editable", package_static_assets=False,
    )
    final_path = output_dir / "光合作用-qwen3.7-flash-可编辑-v2.pptx"
    if exported.resolve() != final_path.resolve():
        shutil.copy2(exported, final_path)

    print(json.dumps({
        "pptx": str(final_path),
        "html": str(html_path),
        "json": str(json_path),
        "slide_count": response.get("slide_count"),
        "model_page_count": sum(
            1 for slide in response.get("slides", []) if (slide.get("metadata") or {}).get("model_used") is True
        ),
        "generation_elapsed_ms": elapsed_ms,
        "quality_report": response.get("quality_report"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
