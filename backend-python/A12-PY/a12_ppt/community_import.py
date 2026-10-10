"""将上传的 PPTX 转为社区可审核、预览与复用的页面，不调用大模型。"""
import base64
import io
import zipfile
from html import escape
from pathlib import Path

MAX_FILE_BYTES = 10 * 1024 * 1024


def slide_title(value: str, number: int) -> str:
    """Use a short first non-empty line, not a complete body paragraph as metadata."""
    title = next((line.strip() for line in str(value or '').splitlines() if line.strip()), f'第 {number} 页')
    return title if len(title) <= 80 else title[:79] + '…'


def import_community_pptx(filename: str, content: bytes) -> dict:
    if Path(filename).suffix.lower() != '.pptx':
        raise ValueError('目前支持 PPTX 课件，请将旧版 PPT 另存为 PPTX 后上传')
    if not content or len(content) > MAX_FILE_BYTES:
        raise ValueError('课件不能为空且不能超过 10MB')
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            if sum(item.file_size for item in archive.infolist()) > 100 * 1024 * 1024:
                raise ValueError('课件解压体积超过 100MB，请压缩图片后上传')
            if 'ppt/presentation.xml' not in archive.namelist():
                raise ValueError('文件不是有效的 PPTX 课件')
        from pptx import Presentation
        presentation = Presentation(io.BytesIO(content))
    except (zipfile.BadZipFile, KeyError) as error:
        raise ValueError('课件文件损坏或不是有效的 PPTX') from error
    if not 1 <= len(presentation.slides) <= 100:
        raise ValueError('课件页数需在 1–100 页之间')
    width, height = presentation.slide_width, presentation.slide_height
    slides = []
    warnings = set()
    encoded_size = 0
    for number, slide in enumerate(presentation.slides, 1):
        elements, texts = [], []
        for shape in slide.shapes:
            style = (f'position:absolute;left:{shape.left / width * 100:.3f}%;'
                     f'top:{shape.top / height * 100:.3f}%;width:{shape.width / width * 100:.3f}%;'
                     f'height:{shape.height / height * 100:.3f}%;overflow:hidden;box-sizing:border-box;')
            if shape.shape_type == 13:
                image = shape.image
                if image.content_type not in {'image/png', 'image/jpeg', 'image/gif', 'image/bmp', 'image/webp'}:
                    warnings.add('部分矢量图片未导入，请在工作台补充')
                    continue
                encoded = base64.b64encode(image.blob).decode('ascii')
                encoded_size += len(encoded)
                if encoded_size > 16 * 1024 * 1024:
                    raise ValueError('课件图片数据过大，请压缩图片后上传')
                elements.append(f'<img alt="课件图片" style="{style}object-fit:contain" src="data:{image.content_type};base64,{encoded}">')
            elif shape.has_text_frame:
                texts.append(shape.text)
                paragraphs = []
                for paragraph in shape.text_frame.paragraphs:
                    runs = []
                    for run in paragraph.runs:
                        font = run.font
                        size = (font.size.pt if font.size else 20) * 1280 / width * 914400 / 72
                        runs.append(f'<span style="font-size:{size:.2f}px;font-weight:{700 if font.bold else 400}">{escape(run.text)}</span>')
                    paragraphs.append('<p style="margin:0;white-space:pre-wrap">' + ''.join(runs) + '</p>')
                elements.append(f'<div style="{style}">' + ''.join(paragraphs) + '</div>')
            elif shape.has_table:
                rows = ['<tr>' + ''.join(f'<td style="border:1px solid #ccc;padding:4px">{escape(cell.text)}</td>' for cell in row.cells) + '</tr>' for row in shape.table.rows]
                elements.append(f'<table style="{style}border-collapse:collapse">' + ''.join(rows) + '</table>')
                texts.extend(cell.text for row in shape.table.rows for cell in row.cells)
            else:
                warnings.add('图表、组合形状、动画和主题样式可能简化，请核对预览后提交')
        title = slide.shapes.title.text if slide.shapes.title else next((t.splitlines()[0] for t in texts if t.strip()), f'第 {number} 页')
        title = slide_title(title, number)
        html = f'<html><body style="margin:0"><section style="position:relative;width:1280px;height:{1280 * height / width:.2f}px;background:white;color:#172b4d;font-family:Arial,Microsoft YaHei,sans-serif">' + ''.join(elements) + '</section></body></html>'
        slides.append({'slide_no': number, 'title': title, 'html': html, 'content': '\n'.join(texts)})
    return {'title': Path(filename).stem, 'filename': Path(filename).name,
            'content_data': {'source': 'a12-uploaded-pptx', 'slides': slides},
            'page_count': len(slides), 'warnings': sorted(warnings)}
