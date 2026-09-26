# A12 Python PPT Service

这是 A12 的后端 Python 服务，负责资料解析、大纲生成、HTML PPT 生成、单页 HTML 修改和 PPTX 导出。

生成链路按 LandPPT 的高质量思路实现：模板风格基因、全局视觉规则、每页创意 brief、HTML 生成、清理校验、失败重试。默认使用 `QUALITY_PRESET=fast`，会并发生成每页 HTML，适合 8 页左右的日常生成；需要最高质量出片时再切换到 `max`。

## 启动

```powershell
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

## 配置

复制 `.env.example` 为 `.env`，然后填写模型配置：

```env
OPENAI_API_KEY=你的模型服务 Key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
EMBEDDING_API_KEY=你的百炼 API Key
EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v4
EMBEDDING_DIMENSIONS=1024
IMAGE_GENERATION_API_KEY=你的百炼 API Key
IMAGE_GENERATION_BASE_URL=https://dashscope.aliyuncs.com/api/v1
IMAGE_GENERATION_MODEL=wan2.2-t2i-flash
MAX_GENERATED_IMAGES=4
REQUEST_TIMEOUT_SECONDS=90
MAX_SLIDE_CONCURRENCY=8
MAX_HTML_RETRIES=1
ENABLE_QUALITY_PIPELINE=true
QUALITY_PRESET=fast
REDIS_URL=redis://127.0.0.1:6379/0
KAFKA_ENABLED=false
KAFKA_BOOTSTRAP_SERVERS=127.0.0.1:9092
```

Redis 开启后提供生成任务队列、可断线续传的进度事件、Embedding/RAG 缓存、请求限流和分布式并发控制。
Kafka 开启后消费资源索引、课堂事件和教师反馈主题，并把索引结果或失败事件写回结果主题/死信主题；Kafka 未开启时 Java 会沿用 HTTP 调用。

百炼的 OpenAI 兼容 Embeddings 请求地址为
`https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings`。API Key 必须与所选地域和计费方案的 Base URL 匹配。

PPT 的 `asset_policy` 默认是 `auto`：服务会先识别用户是否明确要求无图、图片占位或 AI 配图，
再结合学科、页面类型和 `visual_suggestion` 逐页选择。AI 配图使用百炼异步文生图接口，最多生成
`MAX_GENERATED_IMAGES` 张；公式、表格、练习和总结页默认不强行配图。生成结果会立即下载并嵌入 HTML，
因此百炼临时 URL 过期后课件仍可显示，导出 PPTX 时图片也会作为独立图片元素保留。未配置图片模型、
生成超时或调用失败时会自动降级为智能占位，不会中断整套课件。

速度建议：

- `fast`: 推荐默认值，8 页并发生成，速度最快。
- `balanced`: 先生成一次全局风格规则和页面 brief，再并发生成页面。
- `max`:  最高规格，分步抽风格、定规则、写 brief、生成和修复，质量最高但最慢。

## 接口

- `GET /api/v1/python/health`
- `POST /api/v1/python/resources/upload`
- `GET /api/v1/python/templates`
- `POST /api/v1/python/outlines/generate`
- `POST /api/v1/python/intent/recognize`
- `POST /api/v1/python/outlines/chat/stream`
- `GET /api/v1/python/outlines/chat/sessions`
- `POST /api/v1/python/outlines/chat/sessions`
- `GET /api/v1/python/outlines/chat/sessions/{session_id}`
- `PATCH /api/v1/python/outlines/chat/sessions/{session_id}`
- `DELETE /api/v1/python/outlines/chat/sessions/{session_id}`
- `GET /api/v1/python/teacher-style/profile`
- `POST /api/v1/python/outlines/update`
- `POST /api/v1/python/presentations/generate`
- `POST /api/v1/python/presentations/slides/modify`
- `POST /api/v1/python/presentations/html/validate`
- `POST /api/v1/python/presentations/export/pptx`

## 推荐后端流程

1. 前端输入主题、学科、年级、页数、补充要求。
2. 如果上传 PDF/Word/TXT，先调用 `/resources/upload`，保存返回的 `resource_id`。
3. 推荐调用 `/outlines/chat/stream` 做 ChatGPT 式大纲对话，必须传 `user_id`，并传 `message`、`resource_ids`、`enable_rag`、`enable_web`。
4. 如果后端返回 `question` 事件，前端把用户回复再次传给 `/outlines/chat/stream`，并带上同一个 `session_id`。
5. 当 SSE 返回 `final` 事件时，保存其中的 `outline`。
6. 用户也可以编辑返回的 `outline`，或者调用 `/outlines/update` 按新要求重生成。
7. 调用 `/templates` 获取模板列表，前端选择 `templates[n].theme`。
8. 调用 `/presentations/generate`，传确认后的 `outline` 和 `theme`，返回每页 HTML。
9. 前端在线编辑 HTML；单页 AI 修改可调用 `/presentations/slides/modify`。
10. 点击导出时，把最终 slides 传给 `/presentations/export/pptx`，接口直接返回 PPTX 下载文件。

## 对话式大纲 SSE

请求：

```json
{
  "user_id": "10001",
  "session_id": "outline_chat_xxx",
  "message": "帮我做一个七年级生物光合作用8页PPT，加入课堂互动",
  "resource_ids": ["res_xxx"],
  "enable_rag": true,
  "enable_web": false,
  "slide_count": 8,
  "known_context": {}
}
```

事件：

- `session`: 返回或创建 `session_id`
- `stage`: 当前节点，例如解析输入、工具调用、构造 prompt、生成大纲
- `question`: 信息不足时返回澄清问题
- `tool_result`: RAG/联网工具结果摘要
- `prompt`: 合并多轮上下文后的最终大纲 prompt
- `progress`: 模型生成期间的保活进度
- `outline_delta`: 单页大纲增量
- `final`: 完整大纲结果
- `done`: 本轮结束

长期记忆：

- PostgreSQL 建表脚本在 `postgresql_schema.sql`。
- 默认连接配置是 `POSTGRES_DSN=postgresql://postgres:postgres@127.0.0.1:5432/postgres`。
- 会话、消息、大纲生成记录、教师教学风格画像都会按 `user_id` 关联保存。
- 每次大纲生成后，服务会评估用户输入是否体现稳定教学风格；有必要才写入教师画像。
- 可通过 `/outlines/chat/sessions?user_id=10001` 找回用户会话。
- 可通过 `/teacher-style/profile?user_id=10001` 查询教师画像。

当前 PPTX 默认使用 `dom_editable`：Playwright 在 Chromium 中渲染每页 HTML，随后通过随项目部署的 LandPPT `dom-to-pptx`/PptxGenJS 转换器生成 PowerPoint 原生对象。文字、基础形状、表格和媒体尽量保持可编辑；复杂渐变、滤镜、裁切和多重阴影等 PowerPoint 无法准确表达的装饰会局部栅格化。浏览器或主转换器不可用时，会自动降级为 A12 元素级导出，再降级为基础文本版。

首次部署需安装 Chromium：`python -m playwright install chromium`。第三方组件来源及 Apache-2.0 许可证保存在 `a12_ppt/presentation/vendor/`。

## 教学视频解析

视频资料会先读取时长、分辨率和帧率，再根据视频时长动态选择 6～24 个代表画面。关键帧由均匀覆盖和场景变化检测共同决定，随后与内嵌字幕或每 5 分钟一段的 ASR 转写按时间轴对齐。音频片段前后保留 8 秒重叠并在转写后去重，降低分段边界丢字概率。解析结果按时间片独立分块和向量化，每个检索结果都带有 `start_seconds`、`end_seconds` 和可显示的时间戳。

完整 `timeline` 和关键帧列表只保存在资源主记录；向量 chunk 只保存自身时间范围和帧时间点，避免长视频元数据在每个向量块中重复存储。

- 服务优先使用系统 `FFmpeg`；未安装时会使用 `imageio-ffmpeg` 随 Python 依赖提供的可执行文件。
- `ffprobe` 不可用时会回落到 OpenCV 获取视频时长、分辨率和帧率。
- 音轨转写需要配置 `ASR_API_KEY`、`ASR_BASE_URL` 和 `ASR_MODEL`；未单独配置时会回落到 `OPENAI_*`。
- 关键帧视觉理解需要 `ENABLE_VISION_PARSE=true`，且 `OPENAI_MODEL` 必须支持图片输入。
- 支持将 `.srt`、`.vtt`、`.ass` 字幕作为文本资料单独上传；视频内嵌字幕存在时会优先使用，避免重复 ASR。

## Project structure

Current package layout:

- `a12_ppt/llm/`: shared LangChain `ChatOpenAI` / `OpenAIEmbeddings` factories, `LLMClient`, and `EmbeddingClient`. All model and embedding calls should go through this package.
- `a12_ppt/presentation/`: outline generation, HTML PPT generation, template loading, HTML validation, and PPTX export.
- `a12_ppt/resources/`: uploaded file text extraction, MySQL URL resource indexing, metadata update, deletion, and RAG chunk retrieval.
- `a12_ppt/outline_chat/`: LangGraph-based ChatGPT-style outline conversation workflow, session storage, PostgreSQL long memory, and teacher-style profile memory.
- `a12_ppt/tools/`: tool-call adapters used by the workflow, such as RAG search and web search.
- Root compatibility modules such as `a12_ppt/generator.py`, `a12_ppt/resource_store.py`, and `a12_ppt/llm_client.py` only re-export the new package implementations. New code should import from the structured packages.

## AI 能力与评测

- `model_profile` 与 `reasoning_effort` 会真实参与模型路由；每次调用的模型、耗时、令牌量、成功与降级状态会写入 `a12_ai_run_log`。
- RAG 使用向量与关键词混合召回、分数阈值和逐条引用标识；检索文本按不可信证据处理，不能覆盖系统指令。
- 教师对结果的采纳、拒绝和修改写入 `a12_ai_feedback`，并以时间衰减后的置信度更新教师风格画像。
- 课堂正确率、参与度与困惑点写入 `a12_classroom_event`，可在后续生成中作为补救教学依据。
- 视频解析输出关键帧、字幕/ASR 分段、说话人（供应商提供时）和可检索时间轴；语音输出由 `/audio/tts` 提供。
- 离线回归评测位于 `evals/`，执行 `.venv\Scripts\python.exe evals/run_offline_evals.py` 不消耗外部模型额度。
