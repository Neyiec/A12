import asyncio
from unittest.mock import AsyncMock
from PyPDF2 import PdfWriter

from a12_ppt.resources.parsers import document_parser as parser


def test_blank_pdf_has_actionable_error_and_skips_ocr(tmp_path, monkeypatch):
    path = tmp_path / 'blank.pdf'
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    with path.open('wb') as output:
        writer.write(output)
    monkeypatch.setattr(parser, '_render_pdf_pages', lambda *args: (_ for _ in ()).throw(AssertionError('空白页不应OCR')))
    result = asyncio.run(parser.parse_pdf(path))
    assert not result.text
    assert '空白文档' in result.metadata['error']


def test_encrypted_pdf_reports_password_requirement(tmp_path):
    path = tmp_path / 'encrypted.pdf'
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    writer.encrypt('secret-password')
    with path.open('wb') as output:
        writer.write(output)
    result = asyncio.run(parser.parse_pdf(path))
    assert '已加密' in result.metadata['error']


def test_one_page_ocr_failure_does_not_discard_other_text(tmp_path, monkeypatch):
    import PyPDF2
    class Content:
        def get_data(self): return b'image-content'
    class Page:
        def __init__(self, text): self.text = text
        def extract_text(self): return self.text
        def get_contents(self): return Content()
        def get(self, key): return None
    class Reader:
        is_encrypted = False
        pages = [Page('有效正文'), Page('')]
    monkeypatch.setattr(PyPDF2, 'PdfReader', lambda *args: Reader())
    image = tmp_path / 'scan.png'
    image.touch()
    monkeypatch.setattr(parser, '_render_pdf_pages', lambda *args: [(1, image)])
    monkeypatch.setattr(parser, 'parse_image', AsyncMock(side_effect=RuntimeError('OCR失败')))
    result = asyncio.run(parser.parse_pdf(tmp_path / 'input.pdf'))
    assert '有效正文' in result.text
    assert result.metadata['warnings']
    assert not image.exists()
