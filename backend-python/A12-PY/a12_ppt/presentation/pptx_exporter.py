import re
import tempfile
import uuid
from pathlib import Path
from typing import Any

EXPORT_DIR = Path(__file__).resolve().parents[2] / "data" / "exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


async def export_html_slides_to_pptx(
    title: str,
    slides: list[dict[str, Any]],
    filename: str | None = None,
    fidelity: str = "high_fidelity",
) -> Path:
    if fidelity == "high_fidelity":
        rendered = await _export_high_fidelity(title, slides, filename)
        if rendered:
            return rendered
    return _export_editable_text(title, slides, filename)


def export_html_slides_to_pptx_sync(title: str, slides: list[dict[str, Any]], filename: str | None = None) -> Path:
    return _export_editable_text(title, slides, filename)


def _export_editable_text(title: str, slides: list[dict[str, Any]], filename: str | None = None) -> Path:
    from pptx import Presentation
    from pptx.util import Inches, Pt

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    for index, slide_data in enumerate(slides, 1):
        html = str(slide_data.get("html") or slide_data.get("html_content") or "")
        slide_title, bullets = extract_slide_text(html, slide_data, index)
        slide = prs.slides.add_slide(prs.slide_layouts[6])

        title_box = slide.shapes.add_textbox(Inches(0.6), Inches(0.35), Inches(12.1), Inches(0.8))
        title_tf = title_box.text_frame
        title_tf.text = slide_title
        title_tf.paragraphs[0].font.size = Pt(28)
        title_tf.paragraphs[0].font.bold = True

        body_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.35), Inches(11.8), Inches(5.4))
        body_tf = body_box.text_frame
        body_tf.word_wrap = True
        body_tf.clear()
        for i, bullet in enumerate(bullets[:12]):
            p = body_tf.paragraphs[0] if i == 0 else body_tf.add_paragraph()
            p.text = bullet
            p.level = 0
            p.font.size = Pt(18)

        footer = slide.shapes.add_textbox(Inches(11.7), Inches(6.95), Inches(1.0), Inches(0.3))
        footer.text_frame.text = str(index)
        footer.text_frame.paragraphs[0].font.size = Pt(10)

    safe_name = _safe_filename(filename or f"{title}_{uuid.uuid4().hex[:8]}.pptx")
    if not safe_name.lower().endswith(".pptx"):
        safe_name += ".pptx"
    output = EXPORT_DIR / safe_name
    prs.save(output)
    return output


async def _export_high_fidelity(title: str, slides: list[dict[str, Any]], filename: str | None = None) -> Path | None:
    image_paths: list[Path] = []
    try:
        image_paths = await _render_slides_to_images(slides)
        if not image_paths:
            return None
        from pptx import Presentation
        from pptx.util import Inches

        prs = Presentation()
        prs.slide_width = Inches(13.333333)
        prs.slide_height = Inches(7.5)
        for image_path in image_paths:
            slide = prs.slides.add_slide(prs.slide_layouts[6])
            slide.shapes.add_picture(str(image_path), 0, 0, width=prs.slide_width, height=prs.slide_height)
        safe_name = _safe_filename(filename or f"{title}_{uuid.uuid4().hex[:8]}_high_fidelity.pptx")
        if not safe_name.lower().endswith(".pptx"):
            safe_name += ".pptx"
        output = EXPORT_DIR / safe_name
        prs.save(output)
        return output
    except Exception:
        return None
    finally:
        for path in image_paths:
            path.unlink(missing_ok=True)


async def _render_slides_to_images(slides: list[dict[str, Any]]) -> list[Path]:
    from playwright.async_api import async_playwright

    paths: list[Path] = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=2)
        for index, slide_data in enumerate(slides, 1):
            markup = str(slide_data.get("html") or slide_data.get("html_content") or "")
            if not markup.strip():
                slide_title, bullets = extract_slide_text("", slide_data, index)
                markup = _fallback_render_html(slide_title, bullets, index, len(slides))
            await page.set_content(markup, wait_until="networkidle")
            await page.evaluate("document.body.style.margin='0'; document.documentElement.style.margin='0';")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp:
                image_path = Path(temp.name)
            await page.screenshot(path=str(image_path), full_page=False, type="png")
            paths.append(image_path)
        await browser.close()
    return paths


def extract_slide_text(html: str, slide_data: dict[str, Any], index: int) -> tuple[str, list[str]]:
    title = str(slide_data.get("title") or f"第 {index} 页").strip()
    bullets: list[str] = []
    if html:
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            heading = soup.find(["h1", "h2", "title"])
            if heading and heading.get_text(strip=True):
                title = heading.get_text(" ", strip=True)
            for tag in soup.find_all(["li", "p", "article", "div"]):
                text = tag.get_text(" ", strip=True)
                if text and len(text) > 2 and text not in bullets and text != title:
                    bullets.append(text)
                if len(bullets) >= 12:
                    break
        except Exception:
            plain = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.I | re.S)
            plain = re.sub(r"<[^>]+>", "\n", plain)
            lines = [line.strip() for line in plain.splitlines() if len(line.strip()) > 2]
            if lines:
                title = lines[0]
                bullets.extend(line for line in lines[1:13] if line != title)
    for point in slide_data.get("content_points") or []:
        text = str(point).strip()
        if text and text not in bullets:
            bullets.append(text)
    return title, bullets or ["本页内容由 HTML PPT 生成，前端可继续在线编辑后导出。"]


def _safe_filename(filename: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._\-\u4e00-\u9fff]", "_", filename.strip() or "export.pptx")


def _fallback_render_html(title: str, bullets: list[str], index: int, total: int) -> str:
    items = "".join(f"<li>{_escape(item)}</li>" for item in bullets[:8])
    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><style>
html,body{{margin:0;width:100%;height:100%;overflow:hidden;font-family:"Microsoft YaHei",Arial,sans-serif;background:#f8fafc;color:#111827}}
.slide{{width:1280px;height:720px;padding:64px;background:linear-gradient(135deg,#fff,#eef2f7);position:relative}}
h1{{font-size:48px;margin:0 0 36px}}li{{font-size:26px;line-height:1.5;margin:16px 0}}.foot{{position:absolute;right:54px;bottom:34px;color:#64748b}}
</style></head><body><section class="slide"><h1>{_escape(title)}</h1><ul>{items}</ul><div class="foot">{index}/{total}</div></section></body></html>"""


def _escape(value: Any) -> str:
    import html

    return html.escape(str(value or ""))
