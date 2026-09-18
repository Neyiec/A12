# 核心算法实现核查

核查日期：2026-09-14。依据用户提供的五层算法图与当前仓库源码。结论：影响主流程的代码缺口已补齐，真实模型、生产数据库、OCR/ASR 质量和大文件性能仍需在部署环境联调验收。

| 图中能力 | 代码结论 | 实现依据与边界 |
|---|---|---|
| 七节点 LangGraph 状态机 | 已实现 | `backend-python/A12-PY/a12_ppt/outline_chat/workflow.py` 的 `_build_graph`：load_profile → parse_input → tools → build_prompt → generate_outline → reflect → memory；意图缺失时提前澄清，生成失败时退出 |
| LLM + 规则意图识别、澄清 | 已实现 | 同文件 `_extract_intent_with_model` 使用 temperature=0.15；异常回退正则/学科列表；主题、年级、学科缺失时模板化追问。当前侧重备课参数抽取，不能等同于工作台全部动作分类 |
| 工具检索与提示编排 | 已实现 | `outline_chat/workflow.py` 调用 `tools/rag.py`、`web_search.py`、`diagram.py`，将工具结果与教师画像放入生成上下文；联网采用 DuckDuckGo HTML 抓取，图示是规则生成 Mermaid |
| RAG 指纹增量同步 | 已修正 | 下载后计算文件字节 SHA-256；摘要未变化时不再执行解析和向量写入，同地址同大小内容替换也能识别 |
| 自适应语义分块 | 已实现规则版本 | `resources/chunks.py` 按课件、时间线、学科、问答、段落调整窗口与重叠；采用正则语义边界，并非另一个语义模型 |
| pgvector HNSW + 加权重排 | 已实现，运行待验证 | `resources/index_store.py` 建 HNSW cosine 索引，`_rerank_matches` 使用 0.68 向量基础分 + 0.24 词法分 + 元数据分和精确匹配增益；数据库/向量不可用时走降级检索 |
| 文档文本层解析 | 已补齐扫描 PDF 回退 | PDF 先提取文本层，对无文本页面用 pypdfium2 渲染并走 OCR/视觉理解（每份最多 20 页）；DOCX 解析段落/表格，PPTX 解析文本与图片。旧版 DOC/PPT 仍需先转换格式 |
| 图片 OCR + 视觉双通道 | 已实现，依赖待验证 | `vision_parser.py` 使用 pytesseract 与多模态模型，缺失依赖或模型失败时可返回空文本 |
| 音频 ASR | 已实现，依赖待验证 | 输入语音和资源音频统一复用 `asr/service.py`，使用 `.env` 中配置的兼容 ASR 模型，不再在资源解析器中写死模型 |
| 视频关键帧 + 语音转写 | 已补齐 | 关键帧走 OCR/视觉理解；FFmpeg 提取 16 kHz 单声道音轨后走配置的 ASR，两路文本合并进入索引；无 FFmpeg、无音轨或超限时返回明确降级原因 |
| PPT、教案、互动生成 | 已实现 | `presentation/generator.py` 先生成质量规划素材再逐页 HTML，`lesson_plan/generator.py` 生成结构化 JSON，`interactive/generator.py` 生成受提示约束的 HTML 并做基础校验；模型失败可回退模板，不能以模板响应判断真实模型成功 |
| 流式增量解析 | 已实现 | `presentation/generator.py` 的 `_skip_string`、`_object_end`、`_extract_completed_slides` 处理转义、括号配对和完整页对象，workflow 产出 outline_delta |
| 反思与低质量重试 | 已修正归档一致性 | 反思节点最多自动修订一次，只在修订完成后保存最终助手消息、生成记录和会话快照，并通过 `outline_replace/final` 返回最终稿；前置 delta 仍明确标记为预览 |
| 教师风格评估、入库合并 | 已修正返回语义，持久化待验证 | 保存证据与画像的两个 SQL 均成功才返回 `stored=true`；数据库异常返回 false 并将 `available=false`，避免把失败误报为已入库 |
| LLM 缓存、多供应商兼容 | 已实现协议层 | `llm/model_factory.py` 缓存 ChatOpenAI 实例，通过 base_url 接兼容服务；具体供应商能力仍需联调 |
| 1536 维 Embedding | 与图不一致 | 当前 `.env.example` 为百炼 text-embedding-v4、1024 维；`resources/index_store.py` 默认也选 1024。图应改成“可配置维度，当前 1024”，并核对实际数据库向量列与模型输出维度 |
| PostgreSQL + 本地降级 | 已实现部分降级 | 索引有 JSON 降级，会话有内存回退；教师画像持久化失败会准确返回 `stored=false/available=false`，但画像本身仍没有本地持久化副本 |
| 全部前端走 Java | 本次完成路由迁移 | 前端 AI 引擎请求统一 `/api/v1/ai/engine`，Java 复用原转发器；已有业务会话、意图、模板管理路由保留。删除 Vite 直连 Python 的专用代理 |
| 工作台通用聊天 | 已补齐 | Python 新增 `/workspace/chat/stream`，支持通用讨论、动作分类和大纲修复，按 OpenAI 兼容增量格式输出；Java 覆盖用户身份后转发，前端不直连 Python |
| 学习科学驱动的课堂参与设计 | 已补齐生成与质检链路 | 课件按“问题与关联→预测前测→分段新知→分步样例→学生尝试→即时反馈→提取与迁移”组织；每页记录 BOPPPS 阶段、ARCS/ICAP 等理论依据、学生行为层级、认知负荷、支架和反馈策略，并在 HTML 生成、教师备注、前端大纲和质量报告中贯通 |
| 移动端教师界面 | 已补齐响应式入口 | 窄屏将四个主功能改为底部导航，恢复文字标签；教学助手历史通过移动端顶部菜单访问，录音入口沿用响应式聊天界面 |

## 本次网关变更

- Java `PythonProxyController` 新增 `/api/v1/ai/engine` 前缀，保留旧 Java 路径；固定路由逐项转发，未开放任意目标地址代理。
- 新增工作台聊天 SSE 转发方法，复用大纲 SSE 转发逻辑；上游错误以 error 事件返回；非成功 HTTP 响应关闭上游流。
- 会话、意图、教师画像使用 Java 当前用户 ID，SSE 在进入后台线程之前固定身份。
- 前端 `teacher.js` 中原 Python 路径已迁移；既有 `/api/v1/ai/sessions/**`、`/api/v1/ai/intent/**` 业务链路继续复用。
- `API_DOCUMENTATION.md` 增补 Java/Python 映射，完整保留 Python 接口规格；Python 侧补齐工作台、音视频、指纹、最终稿持久化和课堂参与度逻辑。

## 尚需补齐的验收项

1. 旧版 DOC/PPT 仍需先转换为 DOCX/PPTX，应明确产品格式范围或增加 LibreOffice 转换服务。
2. 以真实配置验证 1024 维百炼向量写入、HNSW 查询、ASR、视觉模型和 PostgreSQL 持久化，记录降级状态。
3. 原生索引管理接口的资源归属/管理员授权边界仍需继续收紧；JWT 认证不等于完整租户隔离。
4. 生产部署必须把 Python 放在私有网络，仅允许 Java 访问；当前本机入口绑定 `127.0.0.1` 且已移除浏览器跨域中间件。

## 验证结果

- 前端 `npm run build` 通过。
- Java `mvn -Dtest=AiEngineGatewayTest test` 通过（4 项测试）：新旧路径与 JWT 认证、用户身份覆盖、multipart/二进制转发、工作台中文 SSE 及上游错误事件。
- Python `python -m unittest discover -s tests -p "test_*.py" -v` 通过（5 项测试）：课堂参与字段、工作台增量协议、内容 SHA-256 去重、扫描 PDF 渲染、视频无 FFmpeg 降级。
- 前端生产构建通过；测试未调用收费模型、生产数据库或邮件服务。
