# 第三方 PPTX 转换组件

`dom-to-pptx.bundle.js` 取自 [LandPPT](https://github.com/sligter/LandPPT)，
上游版本 `0.3.2`，获取时提交 `19971a1`。

- 上游许可证：Apache License 2.0，完整文本见 `LANDPPT_LICENSE`
- 用途：在浏览器中读取 HTML DOM 与计算样式，并通过 PptxGenJS 生成 PPTX
- 上游文件：`src/landppt/web/static/js/dom-to-pptx.bundle.js`
- 本项目未删除包内 PptxGenJS、html2canvas、JSZip 等依赖的版权与许可证注释

本项目通过 Playwright 在服务端浏览器中加载该文件。普通文字、形状、表格和媒体会尽量转换为
PowerPoint 原生对象；PowerPoint 无法准确表达的复杂 CSS 装饰会局部栅格化。
