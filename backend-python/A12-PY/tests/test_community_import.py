import io
import pytest
from pptx import Presentation
from pptx.util import Inches
from a12_ppt.community_import import import_community_pptx, MAX_FILE_BYTES


def test_uploaded_pptx_imports_real_pages_and_escapes_text():
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    slide.shapes.add_textbox(Inches(1), Inches(1), Inches(5), Inches(2)).text = '<script>alert(1)</script>化学课件'
    slide.shapes.add_table(1, 1, Inches(1), Inches(4), Inches(4), Inches(1)).table.cell(0, 0).text = '表格内容'
    from PIL import Image
    picture = io.BytesIO()
    Image.new('RGB', (16, 16), 'blue').save(picture, format='PNG')
    picture.seek(0)
    slide.shapes.add_picture(picture, Inches(6), Inches(1), width=Inches(1))
    stream = io.BytesIO()
    presentation.save(stream)
    result = import_community_pptx('水解反应.pptx', stream.getvalue())
    assert result['title'] == '水解反应'
    assert result['page_count'] == 1
    html = result['content_data']['slides'][0]['html']
    assert '<script>' not in html
    assert '&lt;script&gt;' in html
    assert '表格内容' in html
    assert 'data:image/png;base64,' in html


@pytest.mark.parametrize('name,data', [('old.ppt', b'old'), ('bad.pptx', b'bad'), ('large.pptx', b'0' * (MAX_FILE_BYTES + 1))], ids=['legacy', 'corrupt', 'oversized'])
def test_invalid_upload_rejected(name, data):
    with pytest.raises(ValueError):
        import_community_pptx(name, data)


@pytest.mark.parametrize('layout', [0, 6])
def test_long_title_is_short_metadata_while_body_is_preserved(layout):
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[layout])
    body = '计算机指令格式与寻址方式。' * 30
    shape = slide.shapes.title if slide.shapes.title else slide.shapes.add_textbox(Inches(1), Inches(1), Inches(8), Inches(4))
    shape.text = body
    stream = io.BytesIO()
    presentation.save(stream)
    page = import_community_pptx('长标题.pptx', stream.getvalue())['content_data']['slides'][0]
    assert len(page['title']) == 80
    assert page['title'].endswith('…')
    assert body in page['html'] and body in page['content']
