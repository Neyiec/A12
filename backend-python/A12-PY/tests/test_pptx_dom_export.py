import unittest
import zipfile

from a12_ppt.presentation.pptx_exporter import (
    LANDPPT_DOM_TO_PPTX_BUNDLE,
    _export_dom_to_pptx,
)


class DomToPptxExportTests(unittest.IsolatedAsyncioTestCase):
    def test_vendored_landppt_bundle_is_present(self):
        self.assertTrue(LANDPPT_DOM_TO_PPTX_BUNDLE.is_file())
        bundle_head = LANDPPT_DOM_TO_PPTX_BUNDLE.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("exportToPptx", bundle_head)
        self.assertIn("HYBRID RASTER MODE", bundle_head)

    async def test_dom_export_keeps_text_editable_and_rasterizes_complex_decoration(self):
        html = """<!doctype html><html><head><meta charset="utf-8"><style>
        html,body{margin:0;width:1280px;height:720px;font-family:Arial,sans-serif}
        .slide{position:relative;width:1280px;height:720px;background:#f7f8fa;overflow:hidden}
        h1{position:absolute;left:80px;top:60px;font-size:52px;margin:0}
        .card{position:absolute;left:80px;top:190px;width:600px;height:260px;padding:32px;
          box-sizing:border-box;border-radius:24px;font-size:28px;
          background:conic-gradient(from 45deg,#ffd9a0,#ff9db0,#a0c8ff,#ffd9a0);
          box-shadow:0 8px 20px rgba(0,0,0,.18),inset 0 1px #fff}
        </style></head><body><section class="slide">
        <h1>可编辑教学标题</h1><div class="card">复杂背景局部栅格化，文字仍然可以编辑。</div>
        </section></body></html>"""
        try:
            output = await _export_dom_to_pptx("DOM导出测试", [{"html": html}], "dom-export-test.pptx")
        except Exception as exc:
            if "Executable doesn't exist" in str(exc) or "playwright install" in str(exc):
                self.skipTest(f"Chromium is not installed: {exc}")
            raise

        try:
            with zipfile.ZipFile(output) as archive:
                slide_xml = archive.read("ppt/slides/slide1.xml").decode("utf-8")
                media = [name for name in archive.namelist() if name.startswith("ppt/media/")]
            self.assertIn("可编辑教学标题", slide_xml)
            self.assertIn("复杂背景局部栅格化", slide_xml)
            self.assertIn("<p:pic>", slide_xml)
            self.assertTrue(media)
        finally:
            output.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
