import asyncio
import base64
import json
import logging
import mimetypes
import re
import shutil
import sys
import tempfile
import uuid
import zipfile
from pathlib import Path
from typing import Any

EXPORT_DIR = Path(__file__).resolve().parents[2] / "data" / "exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)
LANDPPT_DOM_TO_PPTX_BUNDLE = Path(__file__).resolve().parent / "vendor" / "dom-to-pptx.bundle.js"
logger = logging.getLogger(__name__)


async def export_html_slides_to_pptx(
    title: str,
    slides: list[dict[str, Any]],
    filename: str | None = None,
    fidelity: str = "dom_editable",
    package_static_assets: bool = True,
) -> Path:
    static_assets = _collect_static_assets(slides) if package_static_assets else []
    if fidelity == "high_fidelity":
        rendered = await _export_high_fidelity_safe(title, slides, filename)
        if rendered:
            return _package_if_needed(title, rendered, static_assets, filename)
    output = await _export_dom_to_pptx_safe(title, slides, filename)
    if not output:
        output = await _export_editable_elements_safe(title, slides, filename)
    if not output:
        output = _export_editable_text(title, slides, filename)
    return _package_if_needed(title, output, static_assets, filename)


def export_html_slides_to_pptx_sync(title: str, slides: list[dict[str, Any]], filename: str | None = None) -> Path:
    return _export_editable_text(title, slides, filename)


async def _export_dom_to_pptx_safe(
    title: str,
    slides: list[dict[str, Any]],
    filename: str | None = None,
) -> Path | None:
    """使用 LandPPT 的 dom-to-pptx/PptxGenJS 管线生成原生、可编辑的 PPT 对象。"""
    try:
        if _loop_supports_subprocess():
            return await _export_dom_to_pptx(title, slides, filename)
        return await asyncio.to_thread(_run_dom_to_pptx_isolated, title, slides, filename)
    except Exception as exc:
        # 浏览器运行时或单页 HTML 异常时继续使用项目原有的元素级导出兜底。
        logger.warning("LandPPT DOM-to-PPTX export failed; using A12 fallback: %s", exc)
        return None


def _run_dom_to_pptx_isolated(
    title: str,
    slides: list[dict[str, Any]],
    filename: str | None = None,
) -> Path:
    loop = asyncio.ProactorEventLoop() if sys.platform == "win32" else asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_export_dom_to_pptx(title, slides, filename))
    finally:
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        finally:
            loop.close()


async def _export_dom_to_pptx(
    title: str,
    slides: list[dict[str, Any]],
    filename: str | None = None,
) -> Path:
    """在 Chromium 中测量真实 DOM，并由 LandPPT/PptxGenJS 输出 OOXML PPTX。"""
    if not LANDPPT_DOM_TO_PPTX_BUNDLE.is_file():
        raise FileNotFoundError(f"LandPPT dom-to-pptx bundle not found: {LANDPPT_DOM_TO_PPTX_BUNDLE}")

    from playwright.async_api import async_playwright

    prepared_slides: list[str] = []
    slide_notes: list[str] = []
    for index, slide_data in enumerate(slides, 1):
        markup = str(slide_data.get("html") or slide_data.get("html_content") or "")
        if not markup.strip():
            slide_title, bullets = extract_slide_text("", slide_data, index)
            markup = _fallback_render_html(slide_title, bullets, index, len(slides))
        prepared_slides.append(markup)
        slide_notes.append(str(slide_data.get("speaker_notes") or slide_data.get("notes") or ""))

    if not prepared_slides:
        raise ValueError("No slides provided for PPTX export")

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
        try:
            await page.set_content(
                "<!doctype html><html><head><meta charset='utf-8'></head>"
                "<body style='margin:0;background:transparent'></body></html>",
                wait_until="load",
            )
            await page.add_script_tag(path=str(LANDPPT_DOM_TO_PPTX_BUNDLE))
            pptx_base64 = await page.evaluate(
                _LANDPPT_EXPORT_SCRIPT,
                {"slides": prepared_slides, "slideNotes": slide_notes},
            )
        finally:
            await browser.close()

    pptx_bytes = base64.b64decode(pptx_base64, validate=True)
    if not pptx_bytes.startswith(b"PK"):
        raise ValueError("dom-to-pptx returned an invalid PPTX payload")

    safe_name = _safe_filename(filename or f"{title}_{uuid.uuid4().hex[:8]}_editable.pptx")
    if not safe_name.lower().endswith(".pptx"):
        safe_name += ".pptx"
    output = EXPORT_DIR / safe_name
    output.write_bytes(pptx_bytes)
    return output


_LANDPPT_EXPORT_SCRIPT = r"""async ({slides, slideNotes}) => {
  if (!window.domToPptx || typeof window.domToPptx.exportToPptx !== 'function') {
    throw new Error('LandPPT dom-to-pptx bundle failed to initialize');
  }

  const renderHost = document.createElement('div');
  renderHost.style.cssText = 'position:fixed;left:-9999px;top:-9999px;width:1280px;height:720px;opacity:0;pointer-events:none;overflow:hidden';
  const frame = document.createElement('iframe');
  frame.style.cssText = 'width:1280px;height:720px;border:0;display:block';
  renderHost.appendChild(frame);
  document.body.appendChild(renderHost);

  const waitForFrame = (markup) => new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Slide iframe load timed out')), 15000);
    frame.onload = () => { clearTimeout(timer); resolve(); };
    frame.onerror = () => { clearTimeout(timer); reject(new Error('Slide iframe failed to load')); };
    frame.srcdoc = markup;
  });

  const settleDocument = async (doc) => {
    try { if (doc.fonts && doc.fonts.ready) await Promise.race([doc.fonts.ready, new Promise(r => setTimeout(r, 3000))]); } catch (_) {}
    const images = Array.from(doc.images || []);
    await Promise.all(images.map(img => img.complete ? null : new Promise(resolve => {
      const done = () => resolve();
      img.addEventListener('load', done, {once:true});
      img.addEventListener('error', done, {once:true});
      setTimeout(done, 5000);
    })));
    await new Promise(resolve => (doc.defaultView || window).requestAnimationFrame(() =>
      (doc.defaultView || window).requestAnimationFrame(resolve)));
  };

  async function* slideStream() {
    for (const markup of slides) {
      await waitForFrame(markup);
      const doc = frame.contentDocument || frame.contentWindow.document;
      await settleDocument(doc);
      const root = doc.querySelector('.slide') || doc.querySelector('[data-ppt-slide]') || doc.body;
      if (!root) throw new Error('Slide root not found');
      yield root;
    }
  }

  try {
    const blob = await window.domToPptx.exportToPptx(slideStream(), {
      skipDownload: true,
      autoEmbedFonts: false,
      svgAsVector: false,
      renderMode: 'dom',
      slideNotes: Array.isArray(slideNotes) ? slideNotes : []
    });
    return await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || '').split(',', 2)[1] || '');
      reader.onerror = () => reject(reader.error || new Error('Unable to read generated PPTX'));
      reader.readAsDataURL(blob);
    });
  } finally {
    renderHost.remove();
  }
}"""


async def _export_editable_elements_safe(title: str, slides: list[dict[str, Any]], filename: str | None = None) -> Path | None:
    """将 HTML 前景文字和媒体转换为独立 PPT 对象，装饰层保留为无文字背景。"""
    try:
        if _loop_supports_subprocess():
            return await _export_editable_elements(title, slides, filename)
        return await asyncio.to_thread(_run_editable_elements_isolated, title, slides, filename)
    except Exception:
        return None


def _run_editable_elements_isolated(title: str, slides: list[dict[str, Any]], filename: str | None = None):
    loop = asyncio.ProactorEventLoop() if sys.platform == "win32" else asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_export_editable_elements(title, slides, filename))
    finally:
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        finally:
            loop.close()


async def _export_editable_elements(title: str, slides: list[dict[str, Any]], filename: str | None = None) -> Path:
    from playwright.async_api import async_playwright
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
    from pptx.util import Inches, Pt

    prs = Presentation()
    prs.slide_width = Inches(13.333333)
    prs.slide_height = Inches(7.5)
    temp_paths: list[Path] = []

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=2)
        try:
            for index, slide_data in enumerate(slides, 1):
                markup = str(slide_data.get("html") or slide_data.get("html_content") or "")
                if not markup.strip():
                    slide_title, bullets = extract_slide_text("", slide_data, index)
                    markup = _fallback_render_html(slide_title, bullets, index, len(slides))
                await page.set_content(markup, wait_until="load", timeout=60000)
                await page.evaluate("document.body.style.margin='0';document.documentElement.style.margin='0';")
                manifest = await page.evaluate(_DOM_EXPORT_SCRIPT)

                ppt_slide = _add_blank_slide(prs)

                # 先把所有文字和媒体透明化，截图只保留渐变、阴影、卡片、伪元素等装饰。
                await page.add_style_tag(content="""
                    [data-a12-ppt-text]{color:transparent!important;-webkit-text-fill-color:transparent!important;text-shadow:none!important}
                    [data-a12-ppt-text] *{color:transparent!important;-webkit-text-fill-color:transparent!important;text-shadow:none!important}
                    [data-a12-ppt-media]{visibility:hidden!important}
                """)
                background = _temp_png()
                temp_paths.append(background)
                await page.screenshot(path=str(background), full_page=False, type="png")
                ppt_slide.shapes.add_picture(str(background), 0, 0, width=prs.slide_width, height=prs.slide_height)

                # 恢复媒体可见性并逐个截图，图片/SVG/Canvas/Table 在 PPT 中是独立、可替换对象。
                await page.evaluate("document.querySelectorAll('[data-a12-ppt-media]').forEach(e=>e.style.setProperty('visibility','visible','important'))")
                for media in manifest.get("media", []):
                    media_path = _temp_png()
                    temp_paths.append(media_path)
                    try:
                        await page.locator(f'[data-a12-ppt-media="{media["id"]}"]').screenshot(path=str(media_path), type="png")
                        x, y, width, height = _ppt_bounds(media)
                        picture = ppt_slide.shapes.add_picture(str(media_path), x, y, width=width, height=height)
                        picture.name = str(media.get("name") or f"媒体_{index}_{media['id']}")[:250]
                    except Exception:
                        continue

                for item in manifest.get("texts", []):
                    text = str(item.get("text") or "").strip()
                    if not text:
                        continue
                    x, y, width, height = _ppt_bounds(item)
                    box = ppt_slide.shapes.add_textbox(x, y, width, height)
                    box.name = str(item.get("name") or f"文本_{index}_{item.get('id')}")[:250]
                    box.rotation = float(item.get("rotation") or 0)
                    frame = box.text_frame
                    frame.clear()
                    frame.word_wrap = True
                    frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
                    frame.vertical_anchor = {
                        "middle": MSO_ANCHOR.MIDDLE,
                        "bottom": MSO_ANCHOR.BOTTOM,
                    }.get(str(item.get("vertical_align") or "").lower(), MSO_ANCHOR.TOP)
                    lines = text.splitlines() or [text]
                    for line_no, line in enumerate(lines):
                        paragraph = frame.paragraphs[0] if line_no == 0 else frame.add_paragraph()
                        paragraph.text = line
                        paragraph.alignment = {
                            "center": PP_ALIGN.CENTER,
                            "right": PP_ALIGN.RIGHT,
                            "justify": PP_ALIGN.JUSTIFY,
                        }.get(str(item.get("align") or "").lower(), PP_ALIGN.LEFT)
                        paragraph.font.size = Pt(max(1, float(item.get("font_size") or 16) * 0.75))
                        paragraph.font.bold = int(item.get("font_weight") or 400) >= 600
                        paragraph.font.italic = str(item.get("font_style") or "").lower() == "italic"
                        paragraph.font.name = _primary_font(str(item.get("font_family") or ""))
                        color = _parse_css_color(str(item.get("color") or ""))
                        if color:
                            paragraph.font.color.rgb = RGBColor(*color)
        finally:
            await browser.close()

    safe_name = _safe_filename(filename or f"{title}_{uuid.uuid4().hex[:8]}_editable.pptx")
    if not safe_name.lower().endswith(".pptx"):
        safe_name += ".pptx"
    output = EXPORT_DIR / safe_name
    prs.save(output)
    for path in temp_paths:
        path.unlink(missing_ok=True)
    return output


_DOM_EXPORT_SCRIPT = r"""() => {
  const root = document.querySelector('.slide') || document.querySelector('main') || document.body;
  const rootRect = root.getBoundingClientRect();
  const sx = 1280 / Math.max(1, rootRect.width);
  const sy = 720 / Math.max(1, rootRect.height);
  const visible = (el, rect, style) => style.display !== 'none' && style.visibility !== 'hidden' && Number(style.opacity || 1) > 0 && rect.width > 1 && rect.height > 1;
  const bounds = (rect) => ({x:(rect.left-rootRect.left)*sx,y:(rect.top-rootRect.top)*sy,width:rect.width*sx,height:rect.height*sy});
  const rotation = (transform) => { const m = String(transform||'').match(/^matrix\(([^)]+)\)$/); if(!m)return 0; const v=m[1].split(',').map(Number); return Math.atan2(v[1],v[0])*180/Math.PI; };
  const texts=[];
  [...root.querySelectorAll('*')].forEach((el,i)=>{
    if(['SCRIPT','STYLE','NOSCRIPT'].includes(el.tagName))return;
    if(el.closest('svg,canvas'))return;
    const direct=[...el.childNodes].filter(node=>node.nodeType===Node.TEXT_NODE).map(node=>node.textContent||'').join(' ').trim();
    const text=(direct || (el.children.length===0 ? (el.innerText||el.textContent||'') : '')).replace(/\n{3,}/g,'\n\n').trim();
    const rect=el.getBoundingClientRect(), style=getComputedStyle(el);
    if(!text || !visible(el,rect,style))return;
    const id=`t${i}`; el.setAttribute('data-a12-ppt-text',id);
    texts.push({id,text,name:el.getAttribute('data-name')||el.getAttribute('aria-label')||el.tagName,...bounds(rect),color:style.color,font_size:parseFloat(style.fontSize)||16,font_weight:parseInt(style.fontWeight)||400,font_style:style.fontStyle,font_family:style.fontFamily,align:style.textAlign,vertical_align:style.alignItems,rotation:rotation(style.transform)});
  });
  const media=[];
  [...root.querySelectorAll('img,svg,canvas,table,video')].forEach((el,i)=>{
    if(el.closest('[data-a12-ppt-media]'))return;
    const rect=el.getBoundingClientRect(), style=getComputedStyle(el);
    if(!visible(el,rect,style))return;
    const id=`m${i}`; el.setAttribute('data-a12-ppt-media',id);
    media.push({id,name:el.getAttribute('alt')||el.getAttribute('data-name')||el.getAttribute('aria-label')||el.tagName,...bounds(rect)});
  });
  return {texts,media};
}"""


def _add_blank_slide(prs):
    """追加一页空白版式幻灯片。

    dom_editable 路径的 PPTX 由 LandPPT/PptxGenJS 直接产出，其母版通常只带一个空白版式，
    沿用 `slide_layouts[6]` 会抛 IndexError（导出接口 500）。这里优先按名称挑空白版式，
    再按可用数量兜底，兼容 python-pptx 默认模板与外部管线两种来源。
    """
    layouts = list(prs.slide_layouts)
    if not layouts:
        raise RuntimeError("PPTX 缺少幻灯片版式（slide layout），无法追加幻灯片")
    for layout in layouts:
        if str(getattr(layout, "name", "") or "").strip().lower() in {"blank", "空白"}:
            return prs.slides.add_slide(layout)
    return prs.slides.add_slide(layouts[min(6, len(layouts) - 1)])


def _ppt_bounds(item: dict[str, Any]):
    from pptx.util import Inches

    x = max(0.0, min(1280.0, float(item.get("x") or 0)))
    y = max(0.0, min(720.0, float(item.get("y") or 0)))
    width = max(1.0, min(1280.0 - x, float(item.get("width") or 1)))
    height = max(1.0, min(720.0 - y, float(item.get("height") or 1)))
    return Inches(x / 96.0), Inches(y / 96.0), Inches(width / 96.0), Inches(height / 96.0)


def _primary_font(value: str) -> str:
    first = (value.split(",", 1)[0] if value else "Microsoft YaHei").strip(" '\"")
    return first or "Microsoft YaHei"


def _parse_css_color(value: str) -> tuple[int, int, int] | None:
    text = value.strip().lower()
    match = re.match(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", text)
    if match:
        return tuple(max(0, min(255, int(part))) for part in match.groups())
    match = re.fullmatch(r"#([0-9a-f]{6})", text)
    if match:
        raw = match.group(1)
        return int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)
    return None


async def _export_high_fidelity_safe(title: str, slides: list[dict[str, Any]], filename: str | None = None):
    # uvicorn reload/workers>1 在 Windows 下主循环是 SelectorEventLoop，不支持子进程，
    # Playwright 无法启动 driver 会静默降级为纯文本；此时放到独立线程 + ProactorEventLoop 渲染。
    if _loop_supports_subprocess():
        return await _export_high_fidelity(title, slides, filename)
    return await asyncio.to_thread(_run_high_fidelity_isolated, title, slides, filename)


def _loop_supports_subprocess() -> bool:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return True
    return not isinstance(loop, asyncio.SelectorEventLoop)


def _run_high_fidelity_isolated(title: str, slides: list[dict[str, Any]], filename: str | None = None):
    loop = asyncio.ProactorEventLoop() if sys.platform == "win32" else asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_export_high_fidelity(title, slides, filename))
    finally:
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        finally:
            loop.close()


def _export_editable_text(title: str, slides: list[dict[str, Any]], filename: str | None = None) -> Path:
    from pptx import Presentation
    from pptx.util import Inches, Pt

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    for index, slide_data in enumerate(slides, 1):
        html = str(slide_data.get("html") or slide_data.get("html_content") or "")
        slide_title, bullets = extract_slide_text(html, slide_data, index)
        slide = _add_blank_slide(prs)

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
            slide = _add_blank_slide(prs)
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


def _temp_png() -> Path:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp:
        return Path(temp.name)


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
            try:
                # 用 "load" 而非 "networkidle"：真实页面一旦引用外部资源，networkidle 每页最多卡 30s，
                # 超时会静默把整批导出降级成纯文本。本项目 HTML 均为自包含（data URI），"load" 足够。
                await page.set_content(markup, wait_until="load", timeout=60000)
                await page.evaluate("document.body.style.margin='0'; document.documentElement.style.margin='0';")
                image_path = _temp_png()
                await page.screenshot(path=str(image_path), full_page=False, type="png")
            except Exception:
                # 单页渲染失败：用兜底 HTML 重试一次；仍失败则跳过该页，不让整批导出退化为纯文本。
                try:
                    slide_title, bullets = extract_slide_text("", slide_data, index)
                    await page.set_content(
                        _fallback_render_html(slide_title, bullets, index, len(slides)),
                        wait_until="load",
                        timeout=60000,
                    )
                    image_path = _temp_png()
                    await page.screenshot(path=str(image_path), full_page=False, type="png")
                except Exception:
                    continue
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
        slide = _add_blank_slide(prs)
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
