from pathlib import Path

from a12_ppt.models import OutlineGenerateRequest, PresentationGenerateRequest
from a12_ppt.presentation.generator import PPTGenerator


def test_requests_accept_real_model_controls():
    outline = OutlineGenerateRequest(
        title="光合作用",
        subject="生物",
        grade="七年级",
        model_profile="deep",
        reasoning_effort="high",
    )
    presentation = PresentationGenerateRequest(
        title="光合作用",
        outline={"title": "光合作用", "slides": []},
        model_profile="fast",
        reasoning_effort="low",
    )
    assert outline.model_profile == "deep"
    assert outline.reasoning_effort == "high"
    assert presentation.model_profile == "fast"


def test_fallback_outline_exposes_generation_status():
    generator = PPTGenerator()
    request = OutlineGenerateRequest(title="光合作用", subject="生物", grade="七年级", slide_count=6)
    outline = generator._fallback_outline(request, 6)
    outline["generation_status"] = "fallback"
    response = generator._decorate_outline(outline, request)
    assert response["generation_status"] == "fallback"
    assert len(response["outline"]["slides"]) == 6


def test_database_schema_is_non_destructive():
    schema = (Path(__file__).parents[1] / "postgresql_schema.sql").read_text(encoding="utf-8").upper()
    assert "DROP TABLE" not in schema
    assert "A12_AI_FEEDBACK" in schema
    assert "A12_AI_RUN_LOG" in schema
    assert "A12_CLASSROOM_EVENT" in schema
