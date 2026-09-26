import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";
import { pathToFileURL } from "node:url";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const SOURCE = "C:/Users/32761/Downloads/A12_智核_答辩PPT.pptx";
const WORKSPACE = "D:/GitRepositories/A12";
const BUILD = path.join(WORKSPACE, ".codex-build/tech-ppt");
const OUTPUT = path.join(WORKSPACE, "output");
const FINAL = path.join(OUTPUT, "A12_智核_答辩PPT_技术框架与八项关键技术版.pptx");
const SKILL_DIR = "C:/Users/32761/.codex/plugins/cache/openai-primary-runtime/presentations/26.909.12148/skills/presentations";
const PYTHON = "C:/Users/32761/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe";

const C = {
  bg: "#F5F0E8", red: "#D62828", black: "#1A1A1A", gray: "#6B6560",
  body: "#4A453E", line: "#C9C2B8", pale: "#FFFFFF", soft: "#EAE4DA",
  yellow: "#F4C430", green: "#2D8A63", blue: "#2F6690", redSoft: "#F7DEDB",
};
const FONT = "微软雅黑";

function addText(slide, text, x, y, w, h, opts = {}) {
  const s = slide.shapes.add({
    geometry: "textbox", name: opts.name,
    position: { left: x, top: y, width: w, height: h },
    fill: opts.fill ?? "none",
    line: opts.line ?? { fill: "none", width: 0 },
    borderRadius: opts.borderRadius,
  });
  s.text = text;
  s.text.style = {
    typeface: FONT,
    fontSize: opts.fontSize ?? 15,
    bold: opts.bold ?? false,
    color: opts.color ?? C.body,
    alignment: opts.align ?? "left",
    verticalAlignment: opts.valign ?? "middle",
    autoFit: opts.autoFit ?? "shrinkText",
    wrap: "square",
    insets: opts.insets ?? { left: 4, right: 4, top: 2, bottom: 2 },
    lineSpacing: opts.lineSpacing,
  };
  return s;
}

function addBox(slide, x, y, w, h, opts = {}) {
  const s = slide.shapes.add({
    geometry: opts.geometry ?? "rect", name: opts.name,
    position: { left: x, top: y, width: w, height: h },
    fill: opts.fill ?? C.pale,
    line: opts.line ?? { style: "solid", fill: opts.stroke ?? C.black, width: opts.lineWidth ?? 1.25 },
    borderRadius: opts.radius,
    shadow: opts.shadow,
  });
  if (opts.text) {
    s.text = opts.text;
    s.text.style = {
      typeface: FONT, fontSize: opts.fontSize ?? 15, bold: opts.bold ?? true,
      color: opts.color ?? C.black, alignment: opts.align ?? "center",
      verticalAlignment: opts.valign ?? "middle", autoFit: "shrinkText", wrap: "square",
      insets: opts.insets ?? { left: 5, right: 5, top: 3, bottom: 3 },
    };
  }
  return s;
}

function connect(slide, a, b, opts = {}) {
  return slide.shapes.connect(a, b, {
    kind: opts.kind ?? "straight",
    fromSide: opts.fromSide ?? "right",
    toSide: opts.toSide ?? "left",
    line: { style: opts.dashed ? "dashed" : "solid", fill: opts.color ?? C.gray, width: opts.width ?? 2 },
    head: { type: "none" },
    tail: opts.noHead ? { type: "none" } : { type: "triangle", width: "sm", length: "sm" },
  });
}

function header(slide, section, title, pageNo) {
  slide.background.fill = C.bg;
  addBox(slide, 48, 38.4, 53.76, 53.76, { fill: C.red, stroke: C.red, text: "03", color: "#FFFFFF", fontSize: 21.3, bold: true, lineWidth: 0 });
  addText(slide, section, 119, 33.6, 430, 25, { fontSize: 14, bold: true, color: C.red, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
  addText(slide, title, 119, 57.6, 650, 42, { fontSize: 26.7, bold: true, color: C.black, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
  addText(slide, "03 · TECHNOLOGY", 739, 40.3, 173, 23, { fontSize: 11.3, color: C.gray, align: "right", insets: { left: 0, right: 0, top: 0, bottom: 0 } });
  addBox(slide, 119, 109.4, 793, 4.8, { fill: C.red, stroke: C.red, lineWidth: 0 });
  addBox(slide, 119, 109.4, 106, 4.8, { fill: C.black, stroke: C.black, lineWidth: 0 });
  addBox(slide, 48, 508.8, 864, 1, { fill: C.line, stroke: C.line, lineWidth: 0 });
  addText(slide, "智核 · 多模态AI互动式教学智能体", 78.7, 513.6, 346, 19.2, { fontSize: 9.3, color: C.gray, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
  addBox(slide, 861.1, 517, 7.7, 7.7, { fill: C.red, stroke: C.red, lineWidth: 0 });
  addText(slide, String(pageNo), 871.7, 513.6, 40.3, 19.2, { fontSize: 9.3, color: C.gray, align: "right", insets: { left: 0, right: 0, top: 0, bottom: 0 } });
}

function label(slide, text, x, y, w, color = C.red) {
  return addText(slide, text, x, y, w, 22, { fill: color, color: "#FFFFFF", bold: true, fontSize: 12.5, align: "center", borderRadius: 5, insets: { left: 5, right: 5, top: 1, bottom: 1 } });
}

function techRoute(slide) {
  header(slide, "技术路线", "一次请求贯穿四层，结果可流式返回并导出", 34);
  const y = 158, h = 76;
  const nodes = [
    addBox(slide, 53, y, 145, h, { text: "教师端 / 管理端\nVue 3 · TypeScript", fontSize: 15, fill: "#FFFFFF" }),
    addBox(slide, 238, y, 150, h, { text: "业务网关\nJava 17 · Spring Boot", fontSize: 15, fill: "#FFFFFF" }),
    addBox(slide, 428, y, 160, h, { text: "AI 引擎\nFastAPI · LangGraph", fontSize: 15, fill: C.redSoft, stroke: C.red, lineWidth: 2 }),
    addBox(slide, 628, y, 135, h, { text: "模型服务\nLLM · Embedding", fontSize: 15, fill: "#FFFFFF" }),
    addBox(slide, 803, y, 109, h, { text: "输出\nPPTX / DOCX", fontSize: 15, fill: "#FFFFFF" }),
  ];
  for (let i = 0; i < nodes.length - 1; i++) connect(slide, nodes[i], nodes[i + 1]);
  label(slide, "请求主链路", 53, 128, 100, C.black);
  addText(slide, "JWT 鉴权与接口权限", 242, 241, 142, 24, { fontSize: 11.5, color: C.gray, align: "center" });
  addText(slide, "SSE 透传阶段与逐页结果", 429, 241, 159, 24, { fontSize: 11.5, color: C.red, bold: true, align: "center" });

  label(slide, "数据与资源底座", 53, 286, 116, C.red);
  const stores = [
    [66, "MySQL\n业务数据", C.black], [231, "PostgreSQL\n会话与画像", C.blue],
    [396, "pgvector\n1024维向量", C.green], [561, "Redis\n缓存与任务", C.red], [726, "OSS\n素材与导出", C.gray],
  ].map(([x, text, color]) => addBox(slide, x, 330, 126, 64, { text, fontSize: 14, fill: "#FFFFFF", stroke: color, lineWidth: 2 }));
  const ai = nodes[2];
  for (const s of stores) connect(slide, ai, s, { kind: "elbow", fromSide: "bottom", toSide: "top", color: C.line, width: 1.4 });
  addBox(slide, 53, 425, 859, 49, { fill: C.black, stroke: C.black, lineWidth: 0 });
  addText(slide, "亮点", 70, 434, 58, 28, { color: C.yellow, bold: true, fontSize: 15 });
  addText(slide, "前端只访问 Java 网关，Python 位于内网；AI 生成、业务治理、资源存储可以独立扩展与降级。", 130, 431, 755, 34, { color: "#FFFFFF", fontSize: 14.5 });
}

function techOverview(slide) {
  header(slide, "技术路线", "八项关键技术贯穿理解、生成、交付和持续优化", 36);
  label(slide, "AI 生成主链路", 52, 130, 112, C.black);
  const top = [
    ["01", "Agent 编排", "理解需求\n组织工具"],
    ["02", "多模态解析", "统一资料\n结构"],
    ["03", "RAG 增强", "检索证据\n约束生成"],
    ["04", "课件生成", "规划并发\n校验导出"],
    ["05", "AI 配图", "判断需求\n嵌入素材"],
  ];
  const topShapes = top.map((n, i) => {
    const x = 52 + i * 174;
    addText(slide, n[0], x, 163, 40, 23, { color: C.red, bold: true, fontSize: 16, align: "center" });
    return addBox(slide, x, 188, 148, 70, { text: `${n[1]}\n${n[2]}`, fill: i === 2 ? C.redSoft : "#FFFFFF", stroke: i === 2 ? C.red : C.black, lineWidth: i === 2 ? 2 : 1.2, fontSize: 13.5 });
  });
  for (let i = 0; i < topShapes.length - 1; i++) connect(slide, topShapes[i], topShapes[i + 1], { color: C.gray, width: 1.6 });

  label(slide, "运行与学习闭环", 52, 292, 126, C.red);
  const redisNode = addBox(slide, 106, 338, 196, 82, { text: "06  Redis 工程化\n队列 · 进度 · 缓存 · 限流", fill: "#FFFFFF", stroke: C.red, lineWidth: 2, fontSize: 14 });
  const memoryNode = addBox(slide, 382, 338, 196, 82, { text: "07  教师画像\n偏好证据 · 反馈学习", fill: "#FFFFFF", stroke: C.green, lineWidth: 2, fontSize: 14 });
  const evalNode = addBox(slide, 658, 338, 196, 82, { text: "08  质量评测\n回归 · 事实 · 引用 · 性能", fill: C.black, stroke: C.black, color: "#FFFFFF", lineWidth: 0, fontSize: 14 });
  connect(slide, redisNode, memoryNode, { color: C.red, width: 2 });
  connect(slide, memoryNode, evalNode, { color: C.green, width: 2 });
  connect(slide, evalNode, topShapes[0], { kind: "elbow", fromSide: "top", toSide: "bottom", color: C.gray, dashed: true, width: 1.4 });
  addText(slide, "业务功能对应关系：对话式备课依赖 01–03，课件交付依赖 04–05，平台稳定和持续优化依赖 06–08。", 53, 453, 859, 34, { fill: C.yellow, color: C.black, bold: true, fontSize: 13.5, align: "center" });
}

function systemFramework(slide) {
  header(slide, "系统框架", "双服务分层框架", 34);
  label(slide, "请求与结果主链路", 52, 130, 126, C.black);
  const client = addBox(slide, 53, 176, 150, 72, { text: "访问端\n教师端 · 管理端 · 移动端", fill: "#FFFFFF", stroke: C.black, fontSize: 14 });
  const java = addBox(slide, 255, 176, 171, 72, { text: "Java 业务网关\nJWT · 权限 · SSE 透传", fill: "#FFFFFF", stroke: C.red, fontSize: 14, lineWidth: 2 });
  const python = addBox(slide, 478, 176, 180, 72, { text: "Python AI 引擎\nAgent · RAG · 内容生成", fill: C.redSoft, stroke: C.red, fontSize: 14, lineWidth: 2 });
  const model = addBox(slide, 710, 176, 202, 72, { text: "模型与外部能力\nLLM · Embedding · OCR / ASR", fill: C.black, stroke: C.black, color: "#FFFFFF", fontSize: 14, lineWidth: 0 });
  connect(slide, client, java, { color: C.gray, width: 2 });
  connect(slide, java, python, { color: C.red, width: 2 });
  connect(slide, python, model, { color: C.red, width: 2 });
  addText(slide, "前端只访问 Java 网关", 258, 250, 165, 24, { color: C.gray, fontSize: 11.5, align: "center" });
  addText(slide, "SSE 返回阶段与逐页结果", 482, 250, 174, 24, { color: C.red, bold: true, fontSize: 11.5, align: "center" });

  label(slide, "数据与基础设施", 52, 296, 126, C.red);
  const stores = [
    [53, "MySQL\n业务数据", C.black], [222, "PostgreSQL\n会话与画像", C.blue],
    [391, "pgvector\n向量知识库", C.green], [560, "Redis\n队列与缓存", C.red], [729, "OSS\n素材与导出", C.gray],
  ].map(([x, text, color]) => addBox(slide, x, 340, 150, 66, { text, fill: "#FFFFFF", stroke: color, fontSize: 14, lineWidth: 2 }));
  for (const store of stores) connect(slide, python, store, { kind: "elbow", fromSide: "bottom", toSide: "top", color: C.line, width: 1.2 });
  addText(slide, "框架作用：业务治理与 AI 生成独立演进；模型、数据库或缓存异常时，各层可以按既定链路降级。", 53, 454, 859, 34, { fill: C.yellow, color: C.black, bold: true, fontSize: 13.5, align: "center" });
}

function developmentEnvironment(slide) {
  header(slide, "开发环境", "运行时、框架与协作工具", 35);
  label(slide, "核心运行环境", 52, 130, 112, C.black);
  const columns = [
    { x: 53, w: 260, c: C.black, title: "前端", lines: "Vue 3 + TypeScript + Vite\nSPA 单页应用\nSSE 流式接收\nCapacitor 移动端封装" },
    { x: 350, w: 260, c: C.red, title: "业务后端", lines: "Java 17 + Spring Boot\nRESTful API\nMyBatis 数据访问\nJWT 与接口级权限" },
    { x: 647, w: 265, c: C.blue, title: "AI 后端", lines: "Python 3.11 + FastAPI\nLangGraph / LangChain\nOpenAI 兼容协议\n页面级异步并发" },
  ];
  columns.forEach((col) => {
    addBox(slide, col.x, 166, col.w, 38, { text: col.title, fill: col.c, stroke: col.c, color: "#FFFFFF", fontSize: 15, lineWidth: 0 });
    addBox(slide, col.x, 204, col.w, 116, { text: col.lines, fill: "#FFFFFF", stroke: col.c, color: C.body, fontSize: 13.5, lineWidth: 1.5 });
  });

  label(slide, "数据与多模态组件", 52, 350, 140, C.red);
  addBox(slide, 53, 390, 416, 65, { text: "数据服务\nMySQL · PostgreSQL · pgvector · Redis · OSS", fill: "#FFFFFF", stroke: C.green, fontSize: 13.5, lineWidth: 2 });
  addBox(slide, 496, 390, 416, 65, { text: "解析与导出\nPyPDF2 · python-docx / pptx · OpenCV · Playwright · ASR", fill: "#FFFFFF", stroke: C.red, fontSize: 13.2, lineWidth: 2 });
  addText(slide, "开发工具：IntelliJ IDEA · VS Code · PyCharm · Postman · Figma · Git", 53, 467, 859, 26, { fill: C.black, color: "#FFFFFF", fontSize: 13.5, bold: true, align: "center" });
}

function multimodal(slide) {
  header(slide, "关键技术 02", "多模态资料解析", 38);
  label(slide, "输入资料", 52, 130, 86, C.black);
  const lanes = [
    ["文档", "PDF / DOCX / PPTX", "文本层、段落、表格、图片"],
    ["扫描与图片", "扫描 PDF / 图片", "页面渲染、OCR、视觉理解"],
    ["视频", "视频文件 / 内嵌字幕", "场景检测、6–24 个关键帧、分段 ASR"],
    ["音频与字幕", "音频 / SRT / VTT / ASS", "转写、分段去重、时间戳保留"],
  ];
  const outputs = [];
  lanes.forEach((row, i) => {
    const y = 166 + i * 67;
    addBox(slide, 53, y, 104, 47, { text: row[0], fill: i === 2 ? C.red : C.black, stroke: i === 2 ? C.red : C.black, color: "#FFFFFF", fontSize: 14, lineWidth: 0 });
    const source = addBox(slide, 157, y, 190, 47, { text: row[1], fill: "#FFFFFF", stroke: C.line, fontSize: 13.2, lineWidth: 1.1 });
    const parser = addBox(slide, 397, y, 283, 47, { text: row[2], fill: i === 2 ? C.redSoft : "#FFFFFF", stroke: i === 2 ? C.red : C.gray, fontSize: 13, lineWidth: i === 2 ? 1.8 : 1.1 });
    connect(slide, source, parser, { color: i === 2 ? C.red : C.gray, width: 1.5 });
    outputs.push(parser);
  });
  const unified = addBox(slide, 748, 205, 164, 118, { text: "统一资源结构\n\n正文文本\n页码 / 时间范围\n关键帧时间点\n来源与解析状态", fill: C.black, stroke: C.black, color: "#FFFFFF", fontSize: 14, lineWidth: 0 });
  for (const out of outputs) connect(slide, out, unified, { kind: "elbow", color: C.line, width: 1.2 });
  const chunk = addBox(slide, 748, 362, 164, 66, { text: "进入自适应分块与向量索引\n保留可追溯元数据", fill: "#FFFFFF", stroke: C.green, fontSize: 13.2, lineWidth: 2 });
  connect(slide, unified, chunk, { fromSide: "bottom", toSide: "top", color: C.green, width: 2 });
  addText(slide, "视频解析重点：均匀覆盖与场景变化共同选帧；ASR 每 5 分钟分段并保留 8 秒重叠，转写后再去重。", 53, 454, 859, 34, { color: C.red, bold: true, fontSize: 13, align: "center" });
}

function aiImage(slide) {
  header(slide, "关键技术 05", "AI 配图策略", 41);
  label(slide, "逐页素材决策", 52, 130, 112, C.black);
  const intent = addBox(slide, 53, 177, 170, 82, { text: "用户要求\n明确无图、占位或 AI 配图", fill: "#FFFFFF", stroke: C.black, fontSize: 14 });
  const context = addBox(slide, 53, 298, 170, 100, { text: "页面上下文\n学科 · 页面类型\nvisual_suggestion\n公式与表格默认不强配图", fill: "#FFFFFF", stroke: C.blue, fontSize: 13.5, lineWidth: 2 });
  const policy = addBox(slide, 302, 218, 180, 122, { text: "asset_policy = auto\n\n综合判断素材需求\n控制生成数量与适用页面", fill: C.redSoft, stroke: C.red, fontSize: 14.5, lineWidth: 2 });
  connect(slide, intent, policy, { color: C.gray }); connect(slide, context, policy, { color: C.blue });

  const paths = [
    addBox(slide, 555, 163, 147, 66, { text: "无需图片\n保持版面简洁", fill: "#FFFFFF", stroke: C.gray, fontSize: 13.5 }),
    addBox(slide, 555, 252, 147, 66, { text: "智能占位\n生成失败时自动降级", fill: "#FFFFFF", stroke: C.yellow, fontSize: 13.5, lineWidth: 2 }),
    addBox(slide, 555, 341, 147, 66, { text: "异步文生图\n最多生成 4 张", fill: "#FFFFFF", stroke: C.red, fontSize: 13.5, lineWidth: 2 }),
  ];
  for (const p of paths) connect(slide, policy, p, { kind: "elbow", color: C.line, width: 1.3 });
  const embed = addBox(slide, 775, 218, 137, 122, { text: "下载并本地嵌入\n\n临时 URL 过期后\n课件仍可显示\nPPTX 保留独立图片", fill: C.black, stroke: C.black, color: "#FFFFFF", fontSize: 13.5, lineWidth: 0 });
  connect(slide, paths[2], embed, { kind: "elbow", color: C.red, width: 2 });
  connect(slide, paths[1], embed, { kind: "elbow", color: C.yellow, width: 1.5 });
  addText(slide, "功能作用：控制配图成本和页面适配度，模型超时或未配置时不会中断整套课件生成。", 53, 454, 859, 34, { fill: C.yellow, color: C.black, bold: true, fontSize: 13.5, align: "center" });
}

function redisEngineering(slide) {
  header(slide, "关键技术 06", "Redis 工程化能力", 42);
  label(slide, "后台生成任务", 52, 130, 112, C.black);
  const request = addBox(slide, 53, 180, 135, 70, { text: "Java 网关\n创建生成任务", fill: "#FFFFFF", stroke: C.black, fontSize: 14 });
  const queue = addBox(slide, 235, 180, 135, 70, { text: "Redis 队列\n排队与并发控制", fill: C.redSoft, stroke: C.red, fontSize: 14, lineWidth: 2 });
  const worker = addBox(slide, 417, 180, 135, 70, { text: "Python Worker\n执行课件 / 教案生成", fill: "#FFFFFF", stroke: C.blue, fontSize: 14, lineWidth: 2 });
  const stream = addBox(slide, 599, 180, 135, 70, { text: "进度 Stream\n阶段与已完成页面", fill: "#FFFFFF", stroke: C.green, fontSize: 14, lineWidth: 2 });
  const frontend = addBox(slide, 781, 180, 131, 70, { text: "前端轮询 / SSE\n边生成边预览", fill: C.black, stroke: C.black, color: "#FFFFFF", fontSize: 14, lineWidth: 0 });
  const chain = [request, queue, worker, stream, frontend];
  for (let i = 0; i < chain.length - 1; i++) connect(slide, chain[i], chain[i + 1], { color: C.gray, width: 1.7 });

  label(slide, "同一基础设施承担三类能力", 52, 293, 182, C.red);
  addBox(slide, 53, 337, 246, 92, { text: "任务状态\n结果与进度默认保留 24 小时\n支持断开后重新查询", fill: "#FFFFFF", stroke: C.black, fontSize: 13.5 });
  addBox(slide, 357, 337, 246, 92, { text: "AI 加速\nEmbedding 与 RAG 结果缓存\n减少重复请求", fill: "#FFFFFF", stroke: C.green, fontSize: 13.5, lineWidth: 2 });
  addBox(slide, 661, 337, 251, 92, { text: "运行保护\n用户限流与全局并发控制\n避免模型服务被瞬时请求压满", fill: "#FFFFFF", stroke: C.red, fontSize: 13.5, lineWidth: 2 });
  addText(slide, "降级边界：Redis 不可用时保留原同步与流式接口，核心生成功能仍可继续。", 53, 454, 859, 34, { fill: C.yellow, color: C.black, bold: true, fontSize: 13.5, align: "center" });
}

function evaluation(slide) {
  header(slide, "关键技术 08", "质量评测体系", 44);
  label(slide, "评测流程", 52, 130, 86, C.black);
  const cases = addBox(slide, 53, 172, 158, 76, { text: "固定测试集\n跨学科教学案例\n虚构事实证据", fill: "#FFFFFF", stroke: C.black, fontSize: 14 });
  const run = addBox(slide, 263, 172, 158, 76, { text: "自动运行\n离线回归 + 真实模型\n记录耗时与降级状态", fill: C.redSoft, stroke: C.red, fontSize: 14, lineWidth: 2 });
  const score = addBox(slide, 473, 172, 158, 76, { text: "规则评分\n结构完整性\n教学设计与需求覆盖", fill: "#FFFFFF", stroke: C.blue, fontSize: 14, lineWidth: 2 });
  const audit = addBox(slide, 683, 172, 229, 76, { text: "证据与性能核验\n事实回答、引用编号\n串行与并行对照", fill: C.black, stroke: C.black, color: "#FFFFFF", fontSize: 14, lineWidth: 0 });
  connect(slide, cases, run); connect(slide, run, score); connect(slide, score, audit);

  label(slide, "2026-09-25 实测结果", 52, 286, 158, C.red);
  const metrics = [
    ["5 / 5", "跨学科检索\nTop-1 命中"],
    ["95.24%", "大纲质量\n规则平均分"],
    ["5 / 5", "虚构事实核验\n正确引用证据"],
    ["6.8×", "8 页课件\n并发加速"],
  ];
  metrics.forEach((m, i) => {
    const x = 53 + i * 216;
    addBox(slide, x, 330, 183, 101, { fill: i === 3 ? C.red : "#FFFFFF", stroke: i === 3 ? C.red : C.line, lineWidth: i === 3 ? 0 : 1.2 });
    addText(slide, m[0], x + 8, 342, 167, 34, { color: i === 3 ? "#FFFFFF" : C.red, bold: true, fontSize: 24, align: "center" });
    addText(slide, m[1], x + 8, 379, 167, 41, { color: i === 3 ? "#FFFFFF" : C.body, fontSize: 13.2, align: "center" });
  });
  addText(slide, "口径说明：当前样本量较小；并发数据来自同模型、同大纲、关闭修复重试的一次完整对照实验。", 53, 454, 859, 34, { color: C.gray, fontSize: 12.5, align: "center" });
}

function architecture(slide) {
  header(slide, "系统架构", "双服务解耦，业务治理与 AI 生成独立演进", 35);
  label(slide, "端到端分层", 52, 130, 95, C.black);
  const layers = [
    { y: 164, c: C.black, t: "表示层", d: "教师端 · 管理端 · 移动端 · iframe 沙箱预览" },
    { y: 225, c: C.red, t: "业务网关层", d: "13 个 Controller · JWT 身份覆盖 · 接口级权限 · SSE 透传" },
    { y: 286, c: C.blue, t: "AI 能力层", d: "35 条路由 · Agent 编排 · RAG · 课件 / 教案 / 互动生成" },
    { y: 347, c: C.green, t: "数据访问层", d: "20 个 Mapper · PostgreSQL · Redis · OSS 预签名直传" },
  ];
  const shapes = layers.map((l, i) => {
    addBox(slide, 53, l.y, 126, 47, { fill: l.c, stroke: l.c, text: l.t, color: "#FFFFFF", fontSize: 15, lineWidth: 0 });
    return addBox(slide, 179, l.y, 429, 47, { fill: "#FFFFFF", stroke: l.c, text: l.d, color: C.body, fontSize: 13.3, bold: false, align: "left", insets: { left: 15, right: 8, top: 3, bottom: 3 }, lineWidth: 1.5 });
  });
  for (let i = 0; i < shapes.length - 1; i++) connect(slide, shapes[i], shapes[i + 1], { fromSide: "bottom", toSide: "top", kind: "straight", color: C.gray, width: 1.5 });

  label(slide, "AI 引擎纵深", 650, 130, 104, C.red);
  const mini = ["接入层\nSSE / 任务队列", "编排层\n七节点状态机", "组件层\n解析 / 检索 / 生成", "模型层\n多供应商兼容", "存储层\nPG / Redis / 本地降级"];
  const miniShapes = mini.map((t, i) => addBox(slide, 650, 164 + i * 49, 262, 38, { text: `${i + 1}  ${t}`, fill: i === 1 ? C.redSoft : "#FFFFFF", stroke: i === 1 ? C.red : C.line, fontSize: 12.6, align: "left", insets: { left: 13, right: 6, top: 2, bottom: 2 }, lineWidth: i === 1 ? 1.8 : 1.2 }));
  for (let i = 0; i < miniShapes.length - 1; i++) connect(slide, miniShapes[i], miniShapes[i + 1], { fromSide: "bottom", toSide: "top", kind: "straight", color: C.line, width: 1.2 });
  addText(slide, "平台治理贯穿全层：用户权限、内容审核、资源维护、运行日志与数据看板", 53, 438, 859, 39, { fill: C.black, color: "#FFFFFF", fontSize: 14.5, bold: true, align: "center" });
}

function agentFlow(slide) {
  header(slide, "关键技术 01", "LangGraph Agent 编排", 37);
  label(slide, "LangGraph Agent 主流程", 52, 130, 158, C.black);
  const names = ["画像加载", "意图识别", "工具检索", "提示编排", "大纲生成", "反思校验", "长期记忆"];
  const nodes = names.map((n, i) => addBox(slide, 48 + i * 126, 181, 105, 57, { text: `${String(i + 1).padStart(2, "0")}\n${n}`, fill: i === 1 || i === 5 ? C.redSoft : "#FFFFFF", stroke: i === 1 || i === 5 ? C.red : C.black, fontSize: 14, lineWidth: i === 1 || i === 5 ? 2 : 1.2 }));
  for (let i = 0; i < nodes.length - 1; i++) connect(slide, nodes[i], nodes[i + 1], { color: C.gray, width: 1.7 });

  const clarify = addBox(slide, 174, 290, 232, 66, { text: "要素不足时进入澄清\n主题、年级、学科齐备后继续", fill: "#FFFFFF", stroke: C.yellow, lineWidth: 2, fontSize: 13.5 });
  connect(slide, nodes[1], clarify, { kind: "elbow", fromSide: "bottom", toSide: "top", color: C.yellow, width: 2 });
  const retry = addBox(slide, 647, 290, 218, 66, { text: "质量不达标时自动修订一次\n最终稿再归档并写入记忆", fill: "#FFFFFF", stroke: C.red, lineWidth: 2, fontSize: 13.5 });
  connect(slide, nodes[5], retry, { kind: "elbow", fromSide: "bottom", toSide: "top", color: C.red, width: 2 });
  connect(slide, retry, nodes[4], { kind: "elbow", fromSide: "left", toSide: "bottom", color: C.red, width: 1.5, dashed: true });

  addBox(slide, 52, 405, 860, 70, { fill: C.black, stroke: C.black, lineWidth: 0 });
  addText(slide, "双路径意图识别", 70, 415, 150, 24, { color: C.yellow, fontSize: 14, bold: true });
  addText(slide, "低温模型抽取 13 个白名单字段，异常时回退正则与学科词表。", 215, 414, 670, 27, { color: "#FFFFFF", fontSize: 13.5 });
  addText(slide, "可恢复状态", 70, 444, 150, 22, { color: C.yellow, fontSize: 14, bold: true });
  addText(slide, "多轮对话持续累积上下文；中断后可从会话快照恢复。", 215, 442, 670, 27, { color: "#FFFFFF", fontSize: 13.5 });
}

function ragFlow(slide) {
  header(slide, "关键技术 03", "RAG 知识增强", 39);
  label(slide, "知识入库", 52, 130, 86, C.black);
  const inputs = ["PDF / DOCX / PPTX", "图片 OCR + 视觉", "视频关键帧 + ASR", "音频 / 字幕文本"];
  const inputShapes = inputs.map((t, i) => addBox(slide, 53, 169 + i * 58, 171, 42, { text: t, fill: "#FFFFFF", stroke: i === 1 ? C.red : C.line, fontSize: 12.7, lineWidth: i === 1 ? 1.8 : 1.1 }));
  const parse = addBox(slide, 275, 190, 143, 94, { text: "解析与切分\n\n按资料类型调整\n窗口与重叠", fill: C.redSoft, stroke: C.red, fontSize: 14, lineWidth: 2 });
  const finger = addBox(slide, 275, 320, 143, 70, { text: "SHA-256 指纹\n内容未变不重复解析", fill: "#FFFFFF", stroke: C.black, fontSize: 13, lineWidth: 1.4 });
  for (const inputShape of inputShapes) connect(slide, inputShape, parse, { kind: "elbow", color: C.line, width: 1.1 });
  connect(slide, parse, finger, { fromSide: "bottom", toSide: "top", color: C.gray, width: 1.5 });

  label(slide, "检索与重排", 468, 130, 105, C.red);
  const embed = addBox(slide, 469, 172, 160, 62, { text: "向量化与 HNSW\n当前 1024 维，可配置", fill: "#FFFFFF", stroke: C.green, fontSize: 13.5, lineWidth: 2 });
  const recall = addBox(slide, 469, 270, 160, 62, { text: "候选召回\n取 Top-K 的 4 倍候选", fill: "#FFFFFF", stroke: C.blue, fontSize: 13.5, lineWidth: 2 });
  const rerank = addBox(slide, 469, 368, 160, 76, { text: "混合重排\n0.68 向量 + 0.24 词法\n元数据与整串命中奖励", fill: C.redSoft, stroke: C.red, fontSize: 12.8, lineWidth: 2 });
  connect(slide, parse, embed, { color: C.gray }); connect(slide, embed, recall, { fromSide: "bottom", toSide: "top" }); connect(slide, recall, rerank, { fromSide: "bottom", toSide: "top" });

  label(slide, "生成上下文", 686, 130, 105, C.black);
  const evidence = addBox(slide, 686, 185, 226, 94, { text: "证据片段\n来源文件 · 页码 / 时间戳\n检索分数 · 引用编号", fill: "#FFFFFF", stroke: C.black, fontSize: 14, lineWidth: 1.8 });
  const output = addBox(slide, 686, 334, 226, 94, { text: "受证据约束的生成\n按学段与学科过滤误排\n审计日志支持追溯", fill: C.black, stroke: C.black, color: "#FFFFFF", fontSize: 14, lineWidth: 0 });
  connect(slide, rerank, evidence, { kind: "elbow", color: C.red, width: 2 }); connect(slide, evidence, output, { fromSide: "bottom", toSide: "top", color: C.black, width: 2 });
  addText(slide, "核心亮点：资料解析、检索证据和生成引用形成完整链路，降低“语义相近但学段不符”的误用。", 53, 461, 859, 30, { color: C.red, bold: true, fontSize: 13.5, align: "center" });
}

function generation(slide) {
  header(slide, "关键技术 04", "高质量课件生成管线", 40);
  label(slide, "课件生成质量管线", 52, 130, 150, C.black);
  const names = [
    ["01", "全局规划", "模板风格基因\n视觉规则"], ["02", "逐页 Brief", "教学目标\n内容与视觉建议"],
    ["03", "并发生成", "页面级异步任务\n受控并发"], ["04", "增量推送", "完整页面即刻\nSSE 预览"],
    ["05", "校验修复", "HTML 结构检查\n失败降温重试"], ["06", "可编辑导出", "DOM 转 PPTX\n元素级降级"],
  ];
  const nodes = names.map((n, i) => {
    const x = 52 + i * 145;
    addText(slide, n[0], x, 169, 52, 23, { color: C.red, fontSize: 16, bold: true, align: "center" });
    return addBox(slide, x, 195, 125, 90, { text: `${n[1]}\n${n[2]}`, fill: i === 2 || i === 4 ? C.redSoft : "#FFFFFF", stroke: i === 2 || i === 4 ? C.red : C.black, fontSize: 13, lineWidth: i === 2 || i === 4 ? 2 : 1.2 });
  });
  for (let i = 0; i < nodes.length - 1; i++) connect(slide, nodes[i], nodes[i + 1], { color: C.gray, width: 1.5 });

  addBox(slide, 52, 331, 541, 126, { fill: C.black, stroke: C.black, lineWidth: 0 });
  addText(slide, "流式增量解析", 72, 346, 160, 28, { color: C.yellow, fontSize: 17, bold: true });
  addText(slide, "括号配对状态机只提取已闭合页面；每完成一页就推送预览，整册失败不会抹掉已完成结果。", 72, 376, 488, 58, { color: "#FFFFFF", fontSize: 14.5, valign: "top" });

  addBox(slide, 622, 331, 290, 126, { fill: "#FFFFFF", stroke: C.red, lineWidth: 2 });
  addText(slide, "8 页课件受控对照测试", 643, 343, 248, 24, { color: C.gray, fontSize: 12.5, align: "center" });
  addText(slide, "267.4s", 645, 371, 96, 34, { color: C.gray, fontSize: 22, bold: true, align: "center" });
  addText(slide, "39.3s", 792, 371, 96, 34, { color: C.red, fontSize: 22, bold: true, align: "center" });
  addText(slide, "串行", 645, 403, 96, 21, { color: C.gray, fontSize: 11.5, align: "center" });
  addText(slide, "8 并发", 792, 403, 96, 21, { color: C.red, fontSize: 11.5, bold: true, align: "center" });
  addText(slide, "耗时降低 85.30%，加速 6.8 倍", 641, 427, 252, 24, { fill: C.red, color: "#FFFFFF", fontSize: 13.5, bold: true, align: "center" });
  addText(slide, "注：同一模型、同一大纲、关闭修复重试的一次完整对照实验", 622, 464, 290, 26, { color: C.gray, fontSize: 10.5, align: "center" });
}

function memory(slide) {
  header(slide, "关键技术 07", "教师画像与反馈学习", 43);
  label(slide, "输入证据", 52, 130, 86, C.black);
  const explicit = addBox(slide, 53, 173, 184, 70, { text: "显式偏好\n学段、风格、互动方式", fill: "#FFFFFF", stroke: C.black, fontSize: 14 });
  const implicit = addBox(slide, 53, 269, 184, 70, { text: "隐式行为\n采纳、拒绝、修改内容", fill: "#FFFFFF", stroke: C.red, fontSize: 14, lineWidth: 2 });
  const classroom = addBox(slide, 53, 365, 184, 70, { text: "课堂反馈\n正确率、参与度、困惑点", fill: "#FFFFFF", stroke: C.blue, fontSize: 14, lineWidth: 2 });

  const evidence = addBox(slide, 310, 210, 165, 92, { text: "证据表留档\n记录来源与时间\n支持追溯", fill: C.redSoft, stroke: C.red, fontSize: 14, lineWidth: 2 });
  const profile = addBox(slide, 310, 345, 165, 92, { text: "教师风格画像\n时间衰减置信度\n只保留稳定偏好", fill: C.black, stroke: C.black, color: "#FFFFFF", fontSize: 14, lineWidth: 0 });
  connect(slide, explicit, evidence); connect(slide, implicit, evidence); connect(slide, classroom, profile);
  connect(slide, evidence, profile, { fromSide: "bottom", toSide: "top", color: C.red });

  const prompt = addBox(slide, 548, 210, 160, 92, { text: "提示编排\n当前任务 + RAG 证据\n+ 稳定风格偏好", fill: "#FFFFFF", stroke: C.green, fontSize: 14, lineWidth: 2 });
  const result = addBox(slide, 548, 345, 160, 92, { text: "个性化结果\n首版更贴近教师习惯\n无需重新训练模型", fill: "#FFFFFF", stroke: C.black, fontSize: 14, lineWidth: 1.5 });
  connect(slide, profile, prompt, { kind: "elbow", color: C.green, width: 2 }); connect(slide, prompt, result, { fromSide: "bottom", toSide: "top", color: C.black, width: 2 });

  const feedback = addBox(slide, 779, 244, 133, 159, { text: "反馈回写\n\n采纳\n拒绝\n编辑差异\n\n更新证据与画像", fill: C.red, stroke: C.red, color: "#FFFFFF", fontSize: 14.5, lineWidth: 0 });
  connect(slide, result, feedback, { color: C.red, width: 2 });
  connect(slide, feedback, evidence, { kind: "elbow", fromSide: "top", toSide: "top", color: C.red, width: 1.5, dashed: true });
  addText(slide, "写入规则：证据表与画像表同时成功才标记为已保存；数据库异常会返回不可用状态，避免“假记忆”。", 53, 457, 859, 33, { color: C.red, fontSize: 13, bold: true, align: "center" });
}

function quality(slide) {
  header(slide, "关键技术⑤", "两级质检和受控降级守住课堂可用底线", 40);
  label(slide, "生成结果进入两道质量门", 52, 130, 176, C.black);
  const draft = addBox(slide, 53, 188, 124, 72, { text: "生成草稿\n大纲 + 页面", fill: C.black, stroke: C.black, color: "#FFFFFF", fontSize: 15, lineWidth: 0 });
  const gate1 = addBox(slide, 236, 160, 242, 128, { text: "大纲层 8 项检查\n\n教研链 · 封面 · 目录 · 总结\n页数偏差 · 教学意图\n视觉建议 · 知识点覆盖", fill: "#FFFFFF", stroke: C.red, fontSize: 13.5, lineWidth: 2 });
  const gate2 = addBox(slide, 536, 160, 242, 128, { text: "页面层结构检查\n\n必需标签与层级\n画布约束与嵌套合法性\n危险内容清理", fill: "#FFFFFF", stroke: C.blue, fontSize: 13.5, lineWidth: 2 });
  const pass = addBox(slide, 836, 188, 76, 72, { text: "通过\n可预览 / 导出", fill: C.green, stroke: C.green, color: "#FFFFFF", fontSize: 13.5, lineWidth: 0 });
  connect(slide, draft, gate1, { color: C.red, width: 2 }); connect(slide, gate1, gate2, { color: C.gray, width: 2 }); connect(slide, gate2, pass, { color: C.green, width: 2 });

  const retry = addBox(slide, 236, 335, 242, 88, { text: "质量修订\n反思节点自动重试一次\n失败时降低温度并收紧约束", fill: C.redSoft, stroke: C.red, fontSize: 14, lineWidth: 2 });
  connect(slide, gate1, retry, { kind: "elbow", fromSide: "bottom", toSide: "top", color: C.red, width: 2 });
  connect(slide, retry, gate1, { kind: "elbow", fromSide: "right", toSide: "bottom", color: C.red, width: 1.5, dashed: true });

  const fallback = addBox(slide, 536, 335, 376, 88, { text: "受控降级链\n模型失败：内置模板     PostgreSQL 异常：本地 JSON / 内存\nOCR 不可用：视觉理解互补     DOM 导出失败：元素级 / 基础文本导出", fill: C.black, stroke: C.black, color: "#FFFFFF", fontSize: 13.2, lineWidth: 0, align: "left", insets: { left: 16, right: 8, top: 7, bottom: 5 } });
  connect(slide, gate2, fallback, { kind: "elbow", fromSide: "bottom", toSide: "top", color: C.black, width: 2 });
  addText(slide, "判定标准关注内容与结构合格性。外部服务异常时，系统仍返回可讲授、可预览、可导出的基础结果。", 53, 454, 859, 36, { fill: C.yellow, color: C.black, fontSize: 13.5, bold: true, align: "center" });
}

await fs.mkdir(BUILD, { recursive: true });
await fs.mkdir(OUTPUT, { recursive: true });
const presentation = await PresentationFile.importPptx(await FileBlob.load(SOURCE));
const insertedA = presentation.slides.add();
insertedA.moveTo(40);
const insertedB = presentation.slides.add();
insertedB.moveTo(41);
const insertedC = presentation.slides.add();
insertedC.moveTo(42);
const insertedD = presentation.slides.add();
insertedD.moveTo(43);

const sectionSlide = presentation.slides.getItem(32);
for (const shape of sectionSlide.shapes.items) {
  const current = shape.text?.toString?.() ?? "";
  if (current.includes("本章内容")) shape.text = "本章内容：系统框架 · 开发环境 · 八项关键技术";
}

const builders = [systemFramework, developmentEnvironment, techOverview, agentFlow, multimodal, ragFlow, generation, aiImage, redisEngineering, memory, evaluation];
for (let i = 0; i < builders.length; i++) {
  const slide = presentation.slides.getItem(33 + i);
  slide.shapes.deleteAll();
  for (const image of [...slide.images.items]) slide.images.deleteById(image.id);
  builders[i](slide);
}

const notes = [
  "依据：A12 项目源码与原答辩稿系统架构。此页说明访问端、Java 网关、Python AI 引擎、模型服务和数据基础设施的关系。",
  "依据：frontend、backend-java、backend-python 的依赖配置与 README。此页仅列出项目实际使用的核心运行时、框架和开发工具。",
  "依据：A12 项目源码、CORE_ALGORITHM_REVIEW.md 与用户指定的八项技术。此页用于说明八项技术与业务功能的对应关系。",
  "依据：backend-python/A12-PY/a12_ppt/outline_chat/workflow.py 与 CORE_ALGORITHM_REVIEW.md。",
  "依据：backend-python/A12-PY/README.md 的文档、图片、音频、视频和字幕解析流程。",
  "依据：资源解析、index_store 与 CORE_ALGORITHM_REVIEW.md。向量维度当前为1024，并可通过配置调整。",
  "依据：课件生成器与 AI_BENCHMARK_REPORT.md。性能数据为一次完整串行/并行对照实验。",
  "依据：backend-python/A12-PY/README.md 的 asset_policy、异步文生图、本地嵌入与失败降级说明。",
  "依据：backend-python/A12-PY/README.md 的 Redis 任务队列、进度 Stream、缓存、限流和同步降级说明。",
  "依据：教师画像、反馈与课堂事件链路说明。持久化边界来自 CORE_ALGORITHM_REVIEW.md。",
  "依据：AI_BENCHMARK_REPORT.md，2026-09-25。样本量较小，答辩时需保留测试口径。",
];
for (let i = 0; i < notes.length; i++) presentation.slides.getItem(33 + i).speakerNotes.textFrame.setText(notes[i]);

const { finalizePresentation } = await import(pathToFileURL(path.join(SKILL_DIR, "container_tools/artifact_tool_utils.mjs")).href);
const candidatePath = path.join(BUILD, "candidate-framework-8tech.pptx");
await (await PresentationFile.exportPptx(presentation)).save(candidatePath);
const sourceBytes = await fs.readFile(SOURCE);
const sourceSha256 = crypto.createHash("sha256").update(sourceBytes).digest("hex");
const requirements = {
  explicitTotalSlideCount: 51,
  requiredNativeTableOwnerSlides: [],
  requiredNativeChartOwnerSlides: [],
  sourceTemplatePath: SOURCE,
  requiredTemplateReferenceSlides: [33],
  minimumTemplateCoverageRatio: 0,
};
const result = await finalizePresentation({
  ...requirements,
  workspaceDir: WORKSPACE,
  candidatePath,
  finalPath: FINAL,
  pythonExecutable: PYTHON,
  integrityValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_layout_geometry.py"),
  layoutArgs: ["--expected-slide-size-emu", "9144000,5143500", "--validate-heading-fit"],
  fontPolicy: { basis: "reference", families: ["微软雅黑", "Arial Black"], referencePath: SOURCE, referenceSha256: sourceSha256 },
  verifyArtifactToolImport: true,
  receiptPath: path.join(BUILD, "validation-framework-8tech.json"),
});
console.log(JSON.stringify({ FINAL, result }, null, 2));
