import asyncio
import tempfile
from pathlib import Path

from .common import ParsedResource, merge_text_blocks, plain_text_file
from .vision_parser import describe_image, parse_image


async def parse_pdf(path: Path) -> ParsedResource:
    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(str(path))
        extracted = [(page.extract_text() or "").strip() for page in reader.pages]
        page_blocks = {index: f"第 {index + 1} 页文本:\n{text}" for index, text in enumerate(extracted) if text}
        empty_page_indexes = [index for index, text in enumerate(extracted) if not text]
        # 扫描版 PDF 没有文本层，只渲染空白文本页再走 OCR + 视觉理解，避免整份资料静默为空。
        rendered_pages = await asyncio.to_thread(_render_pdf_pages, path, empty_page_indexes[:20])
        try:
            scanned_results = await asyncio.gather(*[
                parse_image(image_path, f"这是扫描版教学 PDF 的第 {page_index + 1} 页，请提取文字、图表含义、知识点和例题信息。")
                for page_index, image_path in rendered_pages
            ])
            for (page_index, _), (text, _metadata) in zip(rendered_pages, scanned_results):
                if text:
                    page_blocks[page_index] = f"第 {page_index + 1} 页扫描识别:\n{text}"
        finally:
            for _, image_path in rendered_pages:
                image_path.unlink(missing_ok=True)
        return ParsedResource(
            text=merge_text_blocks([page_blocks[index] for index in sorted(page_blocks)]),
            metadata={
                "modality": "document",
                "parser": "PyPDF2+pypdfium2+OCR/vision" if empty_page_indexes else "PyPDF2",
                "page_count": len(reader.pages),
                "text_layer_pages": len(reader.pages) - len(empty_page_indexes),
                "scan_pages_detected": len(empty_page_indexes),
                "scan_pages_processed": len(rendered_pages),
                "scan_pages_skipped": max(0, len(empty_page_indexes) - 20),
            },
        )
    except Exception as exc:
        return ParsedResource(text="", metadata={"modality": "document", "parser": "PyPDF2", "error": str(exc)})


def _render_pdf_pages(path: Path, page_indexes: list[int]) -> list[tuple[int, Path]]:
    if not page_indexes:
        return []
    rendered: list[tuple[int, Path]] = []
    try:
        import pypdfium2 as pdfium

        document = pdfium.PdfDocument(str(path))
        try:
            for page_index in page_indexes:
                if page_index < 0 or page_index >= len(document):
                    continue
                page = document[page_index]
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp:
                    image_path = Path(temp.name)
                bitmap = page.render(scale=2)
                bitmap.to_pil().save(image_path, format="PNG")
                bitmap.close()
                page.close()
                rendered.append((page_index, image_path))
        finally:
            document.close()
    except Exception:
        for _, image_path in rendered:
            image_path.unlink(missing_ok=True)
        return []
    return rendered


async def parse_word(path: Path) -> ParsedResource:
    try:
        from docx import Document

        doc = Document(str(path))
        paragraphs = [paragraph.text for paragraph in doc.paragraphs if paragraph.text]
        table_blocks = []
        for table_index, table in enumerate(doc.tables):
            rows = [" | ".join(cell.text.strip() for cell in row.cells) for row in table.rows]
            table_blocks.append(f"表格 {table_index + 1}:\n" + "\n".join(rows))
        return ParsedResource(
            text=merge_text_blocks(paragraphs + table_blocks),
            metadata={
                "modality": "document",
                "parser": "python-docx",
                "paragraph_count": len(paragraphs),
                "table_count": len(doc.tables),
            },
        )
    except Exception as exc:
        return ParsedResource(text="", metadata={"modality": "document", "parser": "python-docx", "error": str(exc)})


async def parse_text(path: Path) -> ParsedResource:
    return ParsedResource(
        text=plain_text_file(path),
        metadata={"modality": "text", "parser": "plain-text"},
    )


async def parse_presentation(path: Path) -> ParsedResource:
    try:
        from pptx import Presentation

        presentation = Presentation(str(path))
        blocks: list[str] = []
        image_count = 0
        for slide_index, slide in enumerate(presentation.slides):
            texts = []
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text:
                    texts.append(shape.text.strip())
            image_summaries = await _describe_slide_images(slide, slide_index + 1)
            image_count += len(image_summaries)
            blocks.append(merge_text_blocks([
                f"第 {slide_index + 1} 页 PPT 文本:\n" + "\n".join(texts),
                *image_summaries,
            ]))
        return ParsedResource(
            text=merge_text_blocks(blocks),
            metadata={
                "modality": "presentation",
                "parser": "python-pptx+vision",
                "slide_count": len(presentation.slides),
                "image_count": image_count,
            },
        )
    except Exception as exc:
        return ParsedResource(text="", metadata={"modality": "presentation", "parser": "python-pptx", "error": str(exc)})


async def _describe_slide_images(slide, slide_no: int) -> list[str]:
    summaries: list[str] = []
    for shape_index, shape in enumerate(slide.shapes):
        if not hasattr(shape, "image"):
            continue
        try:
            image = shape.image
            suffix = "." + (image.ext or "png")
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
                image_path = Path(temp.name)
                temp.write(image.blob)
            try:
                summary = await describe_image(
                    image_path,
                    f"这是一页 PPT 中的图片，位于第 {slide_no} 页。请提取图片中的文字、图表含义和与教学内容相关的信息。",
                )
                if summary:
                    summaries.append(f"第 {slide_no} 页图片 {shape_index + 1} 视觉理解:\n{summary}")
            finally:
                image_path.unlink(missing_ok=True)
        except Exception:
            continue
    return summaries
