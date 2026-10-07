"""从真实前端组件渲染器到 Chromium DOM/PPTX 的集成回归。"""
import asyncio
import json
import shutil
import subprocess
import unittest
import zipfile
from pathlib import Path

from a12_ppt.presentation.pptx_exporter import _export_dom_to_pptx


class SubjectComponentExportTests(unittest.IsolatedAsyncioTestCase):
    async def test_frontend_subject_components_export_with_editable_titles(self):
        frontend = Path(__file__).resolve().parents[3] / "frontend"
        node = shutil.which("node")
        if not node or not (frontend / "node_modules/vite").exists():
            self.skipTest("需要 Node 和已安装的前端依赖")
        script = r"""
        import {createServer} from 'vite';
        const server=await createServer({server:{middlewareMode:true},appType:'custom'});
        try {
          const m=await server.ssrLoadModule('/src/utils/subjectTool.js');
          const cases=[['公式教学','math_formula',{latex:'y=x^2',display_mode:true}],
                       ['化学式教学','chemical_formula',{formula:'H2O'}],
                       ['函数坐标教学','chart',{option:{a12_function_graph:true,
                         xAxis:{name:'x',data:[-2,-1,0,1,2]},yAxis:{name:'y'},
                         series:[{type:'line',data:[4,1,0,1,4]}]}}]];
          const slides=cases.map(([title,subjectType,data])=>({html:
            '<html><head><meta charset="utf-8"><style>'+m.subjectToolRuntimeCss+
            'html,body{margin:0;width:1280px;height:720px}.slide{position:relative;width:1280px;height:720px}'+
            'h1{position:absolute;left:70px;top:40px;font:42px Arial}.a12-subject-tool{position:absolute;left:100px;top:180px;width:700px;height:360px;padding:24px;font-size:36px}'+
            '</style></head><body><section class="slide"><h1>'+title+'</h1><div class="a12-subject-tool">'+
            m.subjectToolMarkup({subjectType,data})+'</div></section></body></html>'}));
          process.stdout.write('\nA12_RESULT:'+JSON.stringify(slides));
        } finally {await server.close();}
        """
        result = await asyncio.to_thread(subprocess.run, [node, "--input-type=module", "-e", script],
                                         cwd=frontend, capture_output=True, text=True, encoding="utf-8", timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        slides = json.loads(result.stdout.split("A12_RESULT:")[-1])
        try:
            output = await _export_dom_to_pptx("学科组件导出回归", slides, "subject-export-test.pptx")
        except Exception as exc:
            if "Executable doesn't exist" in str(exc):
                self.skipTest("需要安装 Chromium")
            raise
        try:
            with zipfile.ZipFile(output) as archive:
                for index, title in enumerate(["公式教学", "化学式教学", "函数坐标教学"], 1):
                    xml = archive.read(f"ppt/slides/slide{index}.xml").decode("utf-8")
                    self.assertIn(title, xml)
                    self.assertIn("<a:t>", xml)
                self.assertTrue(any(name.startswith("ppt/media/") for name in archive.namelist()))
        finally:
            output.unlink(missing_ok=True)
