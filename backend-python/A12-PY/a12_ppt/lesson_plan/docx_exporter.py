import re
import uuid
from pathlib import Path
from typing import Any

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt


OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "exports"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def export_lesson_plan_to_docx(title: str, lesson_plan: dict[str, Any], filename: str | None = None) -> Path:
    document = Document()
    _setup_styles(document)
    heading = document.add_heading(title or str(lesson_plan.get("title") or "A12 教案"), level=0)
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER

    _add_basic_info(document, lesson_plan)
    _add_list_section(document, "一、教学目标", lesson_plan.get("teaching_goals"))
    _add_list_section(document, "二、教学重点", lesson_plan.get("key_points"))
    _add_list_section(document, "三、教学难点", lesson_plan.get("difficult_points"))
    _add_list_section(document, "四、教学方法", lesson_plan.get("teaching_methods"))
    _add_list_section(document, "五、教学资源", lesson_plan.get("teaching_resources"))
    _add_process_table(document, lesson_plan.get("lesson_process") or [])
    _add_list_section(document, "七、课堂活动设计", lesson_plan.get("classroom_activities"))
    _add_text_section(document, "八、板书设计", lesson_plan.get("blackboard_design"))
    _add_list_section(document, "九、课后作业", lesson_plan.get("homework"))
    _add_list_section(document, "十、评价方式", lesson_plan.get("assessment"))
    _add_text_section(document, "十一、教学反思", lesson_plan.get("reflection"))

    output_name = _safe_filename(filename or f"{title or lesson_plan.get('title') or 'lesson_plan'}_{uuid.uuid4().hex[:8]}.docx")
    if not output_name.lower().endswith(".docx"):
        output_name += ".docx"
    output_path = OUTPUT_DIR / output_name
    document.save(str(output_path))
    return output_path


def _setup_styles(document: Document) -> None:
    normal = document.styles["Normal"]
    normal.font.name = "Microsoft YaHei"
    normal.font.size = Pt(10.5)


def _add_basic_info(document: Document, plan: dict[str, Any]) -> None:
    document.add_heading("基本信息", level=1)
    table = document.add_table(rows=4, cols=2)
    table.style = "Table Grid"
    fields = [
        ("课题", plan.get("title", "")),
        ("学科", plan.get("subject", "")),
        ("年级", plan.get("grade", "")),
        ("课时", f"{plan.get('duration_minutes', '')} 分钟" if plan.get("duration_minutes") else ""),
    ]
    for row, (label, value) in zip(table.rows, fields):
        row.cells[0].text = label
        row.cells[1].text = str(value or "")


def _add_list_section(document: Document, heading: str, value: Any) -> None:
    document.add_heading(heading, level=1)
    items = _as_list(value)
    if not items:
        document.add_paragraph("无")
        return
    for item in items:
        document.add_paragraph(str(item), style="List Bullet")


def _add_text_section(document: Document, heading: str, value: Any) -> None:
    document.add_heading(heading, level=1)
    document.add_paragraph(str(value or "无"))


def _add_process_table(document: Document, process: list[dict[str, Any]]) -> None:
    document.add_heading("六、教学过程", level=1)
    table = document.add_table(rows=1, cols=6)
    table.style = "Table Grid"
    headers = ["环节", "时间", "教师活动", "学生活动", "设计意图", "PPT对应"]
    for cell, header in zip(table.rows[0].cells, headers):
        cell.text = header
    for item in process:
        row = table.add_row().cells
        row[0].text = str(item.get("stage", ""))
        row[1].text = f"{item.get('duration_minutes', '')} 分钟" if item.get("duration_minutes") else ""
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
        return [item.strip() for item in re.split(r"[\n；;]", value) if item.strip()]
    return [value]


def _safe_filename(filename: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._\-\u4e00-\u9fff]", "_", filename)
