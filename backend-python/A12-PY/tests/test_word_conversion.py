import asyncio

import httpx
import pytest
from docx import Document

from a12_ppt import direct_auth
from a12_ppt.resources.parsers.document_parser import parse_word
from a12_ppt.batch_sources import parse_docx


def test_word_parser_preserves_table_position(tmp_path):
    path = tmp_path / "lesson.docx"
    document = Document()
    document.add_paragraph("Learning objective")
    document.add_table(rows=1, cols=1).cell(0, 0).text = "Classroom activity"
    document.add_paragraph("Exit ticket")
    document.save(path)

    result = asyncio.run(parse_word(path))
    assert result.text.index("Learning objective") < result.text.index("Classroom activity") < result.text.index("Exit ticket")


def test_chapter_material_retains_cell_images_and_nested_table_text():
    from io import BytesIO
    from PIL import Image
    from a12_ppt.batch_planner import items_from_document
    document=Document()
    for chapter,color in [('第一章 变量','blue'),('第二章 条件','green')]:
        document.add_heading(chapter,1)
        table=document.add_table(rows=1,cols=1);cell=table.cell(0,0)
        cell.text='本章练习'
        image=BytesIO();Image.new('RGB',(40,30),color).save(image,format='PNG');image.seek(0)
        cell.paragraphs[0].add_run().add_picture(image)
        cell.add_table(rows=1,cols=1).cell(0,0).text='嵌套任务 '+chapter
    blob=BytesIO();document.save(blob)
    parsed=parse_docx(blob.getvalue(),'course.docx')
    items=items_from_document(parsed)
    assert parsed['image_count']==2 and len(items)==2
    assert all(len(item['images'])==1 and '嵌套任务 '+item['title'] in item['source_text'] for item in items)
    assert items[0]['images'][0]['id']!=items[1]['images'][0]['id']


@pytest.mark.parametrize("allow_ai,filename,expected", [(0, "lesson.docx", 403), (1, "lesson.doc", 400), (1, "lesson.docx", None)])
def test_library_conversion_checks_current_permissions_before_download(monkeypatch, allow_ai, filename, expected):
    requests = []

    def respond(request):
        requests.append(request.method)
        data = {"allow_ai": allow_ai, "file_name": filename} if request.method == "GET" else {
            "download_url": "http://storage.test/lesson.docx"
        }
        return httpx.Response(200, json={"code": 200, "data": data})

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    monkeypatch.setattr(direct_auth.httpx, "AsyncClient", lambda **kwargs: client)
    scope = direct_auth.direct_bearer.set("test")
    try:
        if expected:
            with pytest.raises(direct_auth.HTTPException) as error:
                asyncio.run(direct_auth.signed_personal_resource_url("7", require_ai_permission=True))
            assert error.value.status_code == expected
            assert requests == ["GET"]
        else:
            assert asyncio.run(direct_auth.signed_personal_resource_url("7", require_ai_permission=True)) == "http://storage.test/lesson.docx"
            assert requests == ["GET", "POST"]
    finally:
        direct_auth.direct_bearer.reset(scope)
