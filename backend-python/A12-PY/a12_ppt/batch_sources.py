"""Ordered DOCX chapter extraction; source snapshots outlive temporary uploads."""
import base64
import hashlib
import io
import re
import statistics
import zipfile
from pathlib import Path

from docx import Document
from docx.table import Table
from PIL import Image

SOURCE_DIR = Path(__file__).resolve().parents[1] / 'data' / 'batch-sources'
SOURCE_DIR.mkdir(parents=True, exist_ok=True)


def safe_docx(content: bytes):
    if len(content) > 50 * 1024 * 1024:
        raise ValueError('Word 不能超过 50MB')
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        files = archive.infolist()
        if len(files) > 3000 or sum(item.file_size for item in files) > 150 * 1024 * 1024:
            raise ValueError('Word 解压体积过大，请分章上传')
    return Document(io.BytesIO(content))


def heading_level(paragraph, body_size):
    name = (paragraph.style.name or '').lower()
    if name.startswith('toc') or '目录' in name:
        return 0
    match = re.search(r'(?:heading|标题)\s*([1-3])', name)
    if match:
        return int(match[1])
    text = paragraph.text.strip()
    if len(text) > 100 or not text:
        return 0
    chinese = re.match(r'^第[一二三四五六七八九十百\d]+([章节])',text)
    if chinese:
        return 1 if chinese[1]=='章' else 2
    if re.match(r'^(chapter\s+\d+|[一二三四五六七八九十]+[、.])', text, re.I):
        return 1
    match = re.match(r'^(\d+(?:\.\d+){0,2})(?:[、.．]\s*|\s+)\S', text)
    if match:
        return min(3,match[1].count('.')+1)
    sizes = [run.font.size.pt for run in paragraph.runs if run.font.size]
    if sizes and (max(sizes)>=18 or (max(sizes)>=max(14,body_size+2) and any(run.bold for run in paragraph.runs))):
        return 1 if max(sizes) >= 18 else 2
    return 0


def parse_docx(content: bytes, filename: str):
    doc = safe_docx(content)
    sizes = [run.font.size.pt for p in doc.paragraphs for run in p.runs if run.font.size and p.text.strip()]
    body_size = statistics.median(sizes) if sizes else 11
    roots, stack, intro, assets = [], [], [], []
    warnings, methods = [], set()
    image_bytes = 0
    text_chars = 0

    def table_text(table, depth=0):
        if depth > 8:
            raise ValueError('Word 表格嵌套过深，请简化后重新上传')
        lines=[]
        for row in table.rows:
            cells=[]
            for cell in row.cells:
                blocks=[table_text(block,depth+1) if isinstance(block,Table) else block.text.strip()
                        for block in cell.iter_inner_content()]
                cells.append('\n'.join(filter(None,blocks)))
            lines.append(' | '.join(cells))
        return '\n'.join(lines)

    def collect_images(element):
        nonlocal image_bytes
        for blip in element.xpath('.//a:blip'):
            relation=blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
            part=doc.part.related_parts.get(relation)
            if not part:
                continue
            try:
                with Image.open(io.BytesIO(part.blob)) as original:
                    if original.width*original.height>20_000_000:
                        raise ValueError('图片分辨率过大')
                    original.thumbnail((1600,1200))
                    buffer=io.BytesIO();original.convert('RGB').save(buffer,format='JPEG',quality=85)
                blob=buffer.getvalue()
                if image_bytes+len(blob)>8*1024*1024 or len(assets)>=30:
                    raise ValueError('插图超过素材限额')
                image_bytes+=len(blob)
                value={'id':hashlib.sha256(blob).hexdigest()[:24],'label':f'原文插图 {len(assets)+1}',
                    'data_url':'data:image/jpeg;base64,'+base64.b64encode(blob).decode()}
                assets.append(value)
                if stack:stack[-1]['images'].append(value)
            except Exception:
                warnings.append('部分图片未导入；请在原始 Word 中核对，或在工作台补充')

    for order, item in enumerate(doc.iter_inner_content()):
        block=table_text(item) if isinstance(item,Table) else item.text.strip()
        text_chars += len(block)
        if text_chars>500000 or order>5000:
            raise ValueError('教学计划正文过长，请按册或按学期分批上传')
        if isinstance(item, Table):
            if stack:
                stack[-1]['tables'].append(block)
                stack[-1]['text'] += '\n[表格]\n' + block
            else:
                intro.append('[表格]\n' + block)
            # Drawings may be in table cells or nested tables, not only in
            # body paragraphs. Keep them attached to the current chapter.
            collect_images(item._tbl)
            continue
        text = item.text.strip()
        level = heading_level(item, body_size)
        if level and text:
            methods.add('标题样式' if re.search(r'heading|标题', item.style.name, re.I) else '编号或字号启发式')
            node = {'id': hashlib.sha256(f'{order}:{text}'.encode()).hexdigest()[:24], 'title': text[:180],
                    'level': level, 'text': '', 'tables': [], 'images': [], 'children': []}
            while stack and stack[-1]['level'] >= level:
                stack.pop()
            (stack[-1]['children'] if stack else roots).append(node)
            stack.append(node)
        elif text:
            if stack:
                stack[-1]['text'] += '\n' + text
            else:
                intro.append(text)
        collect_images(item._p)
    title = next((p.text.strip() for p in doc.paragraphs if p.text.strip() and p.style.name.lower() == 'title'), Path(filename).stem)
    if not roots:
        roots = [{'id': 'whole_document', 'title': title[:180], 'level': 1, 'text': '\n'.join(intro),
                  'tables': [], 'images': assets, 'children': []}]
        warnings.append('未发现可靠章节结构，先按单份讲义生成；可在计划卡中补充标题或重新上传带标题样式的 Word')
    elif intro:
        roots[0]['text'] = '[章节前导读]\n' + '\n'.join(intro) + '\n' + roots[0]['text']
    assigned={image['id'] for node in flatten_nodes(roots).values() for image in node.get('images',[])}
    roots[0]['images'].extend(image for image in assets if image['id'] not in assigned)
    if len(roots)>200:
        raise ValueError('目录章节过多，请按册或按学期分批上传')
    return {'title': title[:180], 'chapters': roots, 'warnings': list(dict.fromkeys(warnings)),
            'extraction': '、'.join(sorted(methods)) or '纯文本单份', 'image_count': len(assets)}


def flatten_nodes(roots):
    result = {}
    def visit(node):
        result[node['id']] = node
        for child in node.get('children', []):
            visit(child)
    for node in roots:
        visit(node)
    return result


def node_material(node):
    parts, images = [node['title'], node.get('text', '')], list(node.get('images', []))
    for child in node.get('children', []):
        text, assets = node_material(child)
        parts.append(text); images.extend(assets)
    return '\n'.join(parts), images
