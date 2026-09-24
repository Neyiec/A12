"""不调用外部模型的教学 PPT 回归评测。

用法：在 backend-python/A12-PY 目录执行
    .venv/Scripts/python.exe evals/run_offline_evals.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from a12_ppt.models import OutlineGenerateRequest  # noqa: E402
from a12_ppt.presentation.generator import PPTGenerator  # noqa: E402


async def main() -> int:
    cases_path = Path(__file__).with_name("golden_teaching_cases.jsonl")
    cases = [json.loads(line) for line in cases_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    generator = PPTGenerator()
    results: list[dict] = []
    for case in cases:
        request = OutlineGenerateRequest(
            title=case["title"],
            subject=case["subject"],
            grade=case["grade"],
            requirements=case["requirements"],
            slide_count=8,
            enable_rag=False,
        )
        outline = generator._fallback_outline(request, 8)
        outline["generation_status"] = "fallback"
        response = generator._decorate_outline(outline, request)
        outline = response.get("outline", response)
        slides = outline.get("slides", [])
        report = outline.get("quality_report", {})
        teaching_chain = outline.get("teaching_design_chain", {})
        checks = {
            "有完整页数": len(slides) == 8,
            "有教学目标": bool(teaching_chain.get("teaching_goals")),
            "有互动设计": bool(outline.get("interactive_assets")) or any(
                slide.get("interaction") or slide.get("student_task") or slide.get("learner_question")
                for slide in slides
            ),
            "有质量评分": isinstance(report.get("quality_score"), (int, float)),
            "降级状态透明": response.get("generation_status") == "fallback",
        }
        results.append({"id": case["id"], "passed": all(checks.values()), "checks": checks})

    summary = {"total": len(results), "passed": sum(item["passed"] for item in results), "results": results}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["passed"] == summary["total"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
