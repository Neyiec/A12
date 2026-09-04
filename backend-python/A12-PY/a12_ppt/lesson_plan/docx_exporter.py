import re
import uuid
from pathlib import Path
from typing import Any

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt


OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "exports"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def export_lesson_plan_to_docx(title: str, lesson_plan: dict[str, Any], filename: str | None = None) -> Path:
    document = Document()
    _setup_document(document)

    heading = document.add_heading(title or str(lesson_plan.get("title") or _zh("A12 \u6559\u6848")), level=0)
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER

    _add_basic_info(document, lesson_plan)
    _add_list_section(document, _zh("\u4e00\u3001\u6559\u5b66\u76ee\u6807"), lesson_plan.get("teaching_goals"))
    _add_list_section(document, _zh("\u4e8c\u3001\u6559\u5b66\u91cd\u70b9"), lesson_plan.get("key_points"))
    _add_list_section(document, _zh("\u4e09\u3001\u6559\u5b66\u96be\u70b9"), lesson_plan.get("difficult_points"))
    _add_list_section(document, _zh("\u56db\u3001\u6559\u5b66\u65b9\u6cd5"), lesson_plan.get("teaching_methods"))
    _add_list_section(document, _zh("\u4e94\u3001\u6559\u5b66\u8d44\u6e90"), lesson_plan.get("teaching_resources"))
    _add_boppps_table(document, lesson_plan.get("boppps") or {})
    _add_process_table(document, lesson_plan.get("lesson_process") or [])
    _add_list_section(document, _zh("\u4e03\u3001\u8bfe\u5802\u6d3b\u52a8\u8bbe\u8ba1"), lesson_plan.get("classroom_activities"))
    _add_text_section(document, _zh("\u516b\u3001\u677f\u4e66\u8bbe\u8ba1"), lesson_plan.get("blackboard_design"))
    _add_list_section(document, _zh("\u4e5d\u3001\u8bfe\u540e\u4f5c\u4e1a"), lesson_plan.get("homework"))
    _add_list_section(document, _zh("\u5341\u3001\u8bc4\u4ef7\u65b9\u5f0f"), lesson_plan.get("assessment"))
    _add_text_section(document, _zh("\u5341\u4e00\u3001\u6559\u5b66\u53cd\u601d"), lesson_plan.get("reflection"))

    output_name = _safe_filename(filename or f"{title or lesson_plan.get('title') or 'lesson_plan'}_{uuid.uuid4().hex[:8]}.docx")
    if not output_name.lower().endswith(".docx"):
        output_name += ".docx"
    output_path = OUTPUT_DIR / output_name
    document.save(str(output_path))
    return output_path


def _setup_document(document: Document) -> None:
    section = document.sections[0]
    section.top_margin = Pt(72)
    section.bottom_margin = Pt(72)
    section.left_margin = Pt(72)
    section.right_margin = Pt(72)
    _setup_styles(document)
    _add_page_footer(document)


def _setup_styles(document: Document) -> None:
    for style_name in ["Normal", "Heading 1", "Heading 2"]:
        style = document.styles[style_name]
        style.font.name = "Microsoft YaHei"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    document.styles["Normal"].font.size = Pt(10.5)
    document.styles["Heading 1"].font.size = Pt(15)
    document.styles["Heading 2"].font.size = Pt(13)


def _add_page_footer(document: Document) -> None:
    paragraph = document.sections[0].footer.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    fld_char_begin = OxmlElement("w:fldChar")
    fld_char_begin.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = "PAGE"
    fld_char_end = OxmlElement("w:fldChar")
    fld_char_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_char_begin)
    run._r.append(instr_text)
    run._r.append(fld_char_end)


def _add_basic_info(document: Document, plan: dict[str, Any]) -> None:
    document.add_heading(_zh("\u57fa\u672c\u4fe1\u606f"), level=1)
    table = document.add_table(rows=4, cols=2)
    table.style = "Table Grid"
    minute_label = _zh("\u5206\u949f")
    fields = [
        (_zh("\u8bfe\u9898"), plan.get("title", "")),
        (_zh("\u5b66\u79d1"), plan.get("subject", "")),
        (_zh("\u5e74\u7ea7"), plan.get("grade", "")),
        (_zh("\u8bfe\u65f6"), f"{plan.get('duration_minutes', '')} {minute_label}" if plan.get("duration_minutes") else ""),
    ]
    for row, (label, value) in zip(table.rows, fields):
        row.cells[0].text = label
        row.cells[1].text = str(value or "")


def _add_list_section(document: Document, heading: str, value: Any) -> None:
    document.add_heading(heading, level=1)
    items = _as_list(value)
    if not items:
        document.add_paragraph(_zh("\u65e0"))
        return
    for item in items:
        document.add_paragraph(str(item), style="List Bullet")


def _add_text_section(document: Document, heading: str, value: Any) -> None:
    document.add_heading(heading, level=1)
    document.add_paragraph(str(value or _zh("\u65e0")))


def _add_boppps_table(document: Document, boppps: dict[str, Any]) -> None:
    document.add_heading("BOPPPS Teaching Model", level=1)
    table = document.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    table.rows[0].cells[0].text = "Stage"
    table.rows[0].cells[1].text = "Design"
    stages = [
        ("Bridge-in", "bridge_in"),
        ("Objective", "objective"),
        ("Pre-assessment", "pre_assessment"),
        ("Participatory Learning", "participatory_learning"),
        ("Post-assessment", "post_assessment"),
        ("Summary", "summary"),
    ]
    for label, key in stages:
        row = table.add_row().cells
        row[0].text = label
        row[1].text = "\n".join(str(item) for item in _as_list(boppps.get(key))) or _zh("\u65e0")


def _add_process_table(document: Document, process: list[dict[str, Any]]) -> None:
    document.add_heading(_zh("\u516d\u3001\u6559\u5b66\u8fc7\u7a0b"), level=1)
    table = document.add_table(rows=1, cols=6)
    table.style = "Table Grid"
    minute_label = _zh("\u5206\u949f")
    headers = [
        _zh("\u73af\u8282"),
        _zh("\u65f6\u95f4"),
        _zh("\u6559\u5e08\u6d3b\u52a8"),
        _zh("\u5b66\u751f\u6d3b\u52a8"),
        _zh("\u8bbe\u8ba1\u610f\u56fe"),
        _zh("PPT\u5bf9\u5e94"),
    ]
    for cell, header in zip(table.rows[0].cells, headers):
        cell.text = header
    if not process:
        row = table.add_row().cells
        row[0].text = _zh("\u672a\u586b\u5199")
        return
    for item in process:
        row = table.add_row().cells
        row[0].text = str(item.get("stage", ""))
        row[1].text = f"{item.get('duration_minutes', '')} {minute_label}" if item.get("duration_minutes") else ""
        row[2].text = str(item.get("teacher_activity", ""))
        row[3].text = str(item.get("student_activity", ""))
        row[4].text = str(item.get("design_intent", ""))
        row[5].text = str(item.get("ppt_reference", ""))


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [item.strip() for item in re.split(r"[\n;；]", value) if item.strip()]
    return [value]


def _safe_filename(filename: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._\-\u4e00-\u9fff]", "_", filename.strip() or "lesson_plan.docx")


def _zh(value: str) -> str:
    try:
        return value.encode("ascii").decode("unicode_escape")
    except UnicodeEncodeError:
        return value
