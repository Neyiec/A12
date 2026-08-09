import base64
import json
import mimetypes
import re
import shutil
import tempfile
import uuid
import zipfile
from pathlib import Path
from typing import Any

EXPORT_DIR = Path(__file__).resolve().parents[2] / "data" / "exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


async def export_html_slides_to_pptx(
    title: str,
    slides: list[dict[str, Any]],
    filename: str | None = None,
    fidelity: str = "high_fidelity",
    package_static_assets: bool = True,
) -> Path:
    static_assets = _collect_static_assets(slides) if package_static_assets else []
    if fidelity == "high_fidelity":
        rendered = await _export_high_fidelity(title, slides, filename)
        if rendered:
            return _package_if_needed(title, rendered, static_assets, filename)
    output = _export_editable_text(title, slides, filename)
    return _package_if_needed(title, output, static_assets, filename)


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


def _package_if_needed(title: str, pptx_path: Path, static_assets: list[dict[str, Any]], filename: str | None = None) -> Path:
    if not static_assets:
        return pptx_path

    package_id = uuid.uuid4().hex[:8]
    package_dir = EXPORT_DIR / f"package_{package_id}"
    static_dir = package_dir / "static"
    static_dir.mkdir(parents=True, exist_ok=True)

    packaged_assets = _write_static_assets(static_assets, static_dir)
    _append_asset_reference_slides(pptx_path, packaged_assets, static_dir)

    manifest = {
        "title": title,
        "pptx": pptx_path.name,
        "static_dir": "static",
        "assets": packaged_assets,
    }
    (static_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    safe_name = _safe_filename(filename or f"{title}_{package_id}.zip")
    safe_name = re.sub(r"\.pptx$", ".zip", safe_name, flags=re.I)
    if not safe_name.lower().endswith(".zip"):
        safe_name += ".zip"
    zip_path = EXPORT_DIR / safe_name
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(pptx_path, pptx_path.name)
        for path in static_dir.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(package_dir).as_posix())
    shutil.rmtree(package_dir, ignore_errors=True)
    return zip_path


def _collect_static_assets(slides: list[dict[str, Any]]) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for slide_index, slide in enumerate(slides or [], 1):
        candidates: list[Any] = []
        for key in ["interactive_assets", "interactive_modules", "static_assets", "assets"]:
            value = slide.get(key)
            if isinstance(value, list):
                candidates.extend(value)
            elif isinstance(value, dict):
                candidates.append(value)
        metadata = slide.get("metadata") or {}
        for key in ["interactive_assets", "interactive_modules", "static_assets", "assets"]:
            value = metadata.get(key) if isinstance(metadata, dict) else None
            if isinstance(value, list):
                candidates.extend(value)
            elif isinstance(value, dict):
                candidates.append(value)
        if isinstance(slide.get("interactive_module"), dict):
            candidates.append(slide["interactive_module"])

        for index, raw in enumerate(candidates, 1):
            if not isinstance(raw, dict):
                continue
            asset = _normalize_static_asset(raw, slide_index, index)
            dedupe_key = asset.get("asset_id") or asset.get("filename") or f"{slide_index}_{index}"
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            collected.append(asset)
    return collected


def _normalize_static_asset(raw: dict[str, Any], slide_no: int, index: int) -> dict[str, Any]:
    asset_id = str(raw.get("asset_id") or raw.get("module_id") or f"asset_{slide_no}_{index}")
    asset_id = re.sub(r"[^a-zA-Z0-9_-]", "_", asset_id).strip("_") or f"asset_{slide_no}_{index}"
    fmt = str(raw.get("preferred_format") or raw.get("format") or raw.get("type") or "html5").lower()
    if fmt in {"animation", "game", "simulation", "quiz_game", "matching_game", "timeline_game"}:
        fmt = "html5"
    if fmt not in {"html5", "html", "gif", "mp4"}:
        fmt = "html5"
    extension = "html" if fmt in {"html5", "html"} else fmt
    filename = _safe_filename(str(raw.get("filename") or f"{asset_id}.{extension}"))
    if "." not in filename:
        filename = f"{filename}.{extension}"
    return {
        **raw,
        "asset_id": asset_id,
        "title": str(raw.get("title") or raw.get("name") or f"Interactive asset {slide_no}-{index}"),
        "description": str(raw.get("description") or raw.get("usage") or raw.get("notes") or "Supplementary classroom interactive resource."),
        "format": "html5" if extension == "html" else extension,
        "filename": filename,
        "target_slide_no": int(raw.get("target_slide_no") or raw.get("slide_no") or slide_no),
        "integration": str(raw.get("integration") or ("ppt_video" if extension == "mp4" else "static_link")),
    }


def _write_static_assets(assets: list[dict[str, Any]], static_dir: Path) -> list[dict[str, Any]]:
    packaged: list[dict[str, Any]] = []
    used_names: set[str] = set()
    for asset in assets:
        source_path = Path(str(asset.get("path") or asset.get("file_path") or ""))
        has_binary_source = source_path.is_file() or bool(asset.get("bytes_base64") or asset.get("content_base64"))
        filename = _safe_filename(str(asset.get("filename") or f"{asset.get('asset_id')}.html"))
        if Path(filename).suffix.lower() in {".mp4", ".gif"} and not has_binary_source:
            filename = f"{Path(filename).stem}.html"
            asset = {**asset, "format": "html5", "integration": "static_link"}
        filename = _unique_filename(filename, used_names)
        output = static_dir / filename
        if source_path.is_file():
            shutil.copy2(source_path, output)
        elif asset.get("bytes_base64"):
            output.write_bytes(base64.b64decode(str(asset["bytes_base64"])))
        elif asset.get("content_base64"):
            output.write_bytes(base64.b64decode(str(asset["content_base64"])))
        elif asset.get("html") or asset.get("content"):
            output.write_text(str(asset.get("html") or asset.get("content") or ""), encoding="utf-8")
        elif asset.get("url"):
            output.write_text(_external_link_html(asset), encoding="utf-8")
        else:
            output.write_text(_asset_description_html(asset), encoding="utf-8")
        packaged_asset = {key: value for key, value in asset.items() if key not in {"html", "content", "bytes_base64", "content_base64"}}
        packaged_asset.update({
            "filename": filename,
            "relative_path": f"static/{filename}",
            "mime_type": mimetypes.guess_type(filename)[0] or "application/octet-stream",
        })
        packaged.append(packaged_asset)
    return packaged


def _append_asset_reference_slides(pptx_path: Path, assets: list[dict[str, Any]], static_dir: Path) -> None:
    from pptx import Presentation
    from pptx.util import Inches, Pt

    prs = Presentation(str(pptx_path))
    for asset in assets:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        title_box = slide.shapes.add_textbox(Inches(0.6), Inches(0.4), Inches(12.0), Inches(0.7))
        title_tf = title_box.text_frame
        title_tf.text = str(asset.get("title") or "Interactive resource")
        title_tf.paragraphs[0].font.size = Pt(26)
        title_tf.paragraphs[0].font.bold = True

        desc_box = slide.shapes.add_textbox(Inches(0.75), Inches(1.35), Inches(11.8), Inches(2.2))
        desc_tf = desc_box.text_frame
        desc_tf.word_wrap = True
        desc_tf.text = str(asset.get("description") or "")
        desc_tf.paragraphs[0].font.size = Pt(18)

        path_text = str(asset.get("relative_path") or "")
        link_box = slide.shapes.add_textbox(Inches(0.75), Inches(3.75), Inches(11.8), Inches(0.8))
        link_tf = link_box.text_frame
        link_tf.text = "Resource: "
        run = link_tf.paragraphs[0].add_run()
        run.text = path_text
        run.font.size = Pt(18)
        if path_text:
            run.hyperlink.address = path_text

        if asset.get("format") == "mp4":
            video_path = static_dir / str(asset.get("filename") or "")
            if video_path.is_file():
                try:
                    slide.shapes.add_movie(str(video_path), Inches(0.9), Inches(4.6), Inches(6.4), Inches(1.8), mime_type=asset.get("mime_type") or "video/mp4")
                except Exception:
                    pass
    prs.save(str(pptx_path))


def _unique_filename(filename: str, used_names: set[str]) -> str:
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    candidate = filename
    index = 2
    while candidate in used_names:
        candidate = f"{stem}_{index}{suffix}"
        index += 1
    used_names.add(candidate)
    return candidate


def _external_link_html(asset: dict[str, Any]) -> str:
    title = _escape(asset.get("title") or "External resource")
    url = _escape(asset.get("url") or "#")
    description = _escape(asset.get("description") or "")
    return f'<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta http-equiv="refresh" content="0; url={url}"><title>{title}</title></head><body><h1>{title}</h1><p>{description}</p><p><a href="{url}">{url}</a></p></body></html>'


def _asset_description_html(asset: dict[str, Any]) -> str:
    title = _escape(asset.get("title") or "Interactive resource")
    description = _escape(asset.get("description") or "")
    return f'<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>{title}</title></head><body><h1>{title}</h1><p>{description}</p></body></html>'


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
