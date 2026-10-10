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

双端直连还需配置 `JAVA_AUTH_BASE_URL`（Java 服务地址）、`A12_FRONTEND_ORIGINS`（允许的前端来源）及随机长密钥 `A12_PYTHON_INTERNAL_KEY`。Java 启动进程必须设置**相同**的 `A12_PYTHON_INTERNAL_KEY`，供 Python 后台消费者向 Java 读取业务数据和回写状态；不得放在 `VITE_*` 前端变量中。设置 `A12_RESOURCE_REDIS_URL` 指向 Java 使用的同一 Redis 实例（默认 `redis://127.0.0.1:6379/0`）；`A12_AUTH_REDIS_URL` 可单独指定认证 Redis，未设置时沿用资源 Redis。Python 在浏览器请求进入时、调用模型前都核对 Java 的 `token:user:{userId}`：缺失或被新登录替换返回 401，Redis 不可用返回 503，不降级放行。可信的后台事件没有浏览器令牌，仅以共享内部密钥与 Java 通信。资源变动经 Redis Stream `a12:resource-index:events` 传递，失败重试 3 次后进入 `a12:resource-index:dead-letter`。PPT 社区投稿经 `a12:community-review:events` 触发文科、理科、工科 AI 初审；Python 仅给出结构化意见，Java 决定是否高置信自动放行或留待人工复核。审核事件失败重试 3 次后进入 `a12:community-review:dead-letter`，投稿始终可由人工处理。教师端开发服务器通过 `/api/v1/python` 代理到 FastAPI，其余 `/api` 到 Java；生产环境分别设置 `VITE_PYTHON_API_BASE_URL` 和 `VITE_API_BASE_URL`，并为两个域名启用 HTTPS。未配置内部密钥时 Python 后台消费者不会启动。

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
```

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

社区审核通过且采用 `CC BY` 系列授权的 PPT 会作为 `community:{内容ID}` 自动进入检索；下架或取消公开时由业务事件移除索引。管理端知识库页面以同一登录令牌直连 Python 查询索引，开发环境还需允许管理端 `http://localhost:8888` 来源。社区索引由审核事件维护，不能从浏览器直接写入；每日业务补偿任务会核对漏发事件。

- `model_profile` 与 `reasoning_effort` 会真实参与模型路由；每次调用的模型、耗时、令牌量、成功与降级状态会写入 `a12_ai_run_log`。
- RAG 使用向量与关键词混合召回、分数阈值和逐条引用标识；检索文本按不可信证据处理，不能覆盖系统指令。
- 教师对结果的采纳、拒绝和修改写入 `a12_ai_feedback`，并以时间衰减后的置信度更新教师风格画像。
- 课堂正确率、参与度与困惑点写入 `a12_classroom_event`，可在后续生成中作为补救教学依据。
- 视频解析输出关键帧、字幕/ASR 分段、说话人（供应商提供时）和可检索时间轴；语音输出由 `/audio/tts` 提供。
- 离线回归评测位于 `evals/`，执行 `.venv\Scripts\python.exe evals/run_offline_evals.py` 不消耗外部模型额度。
# 课程知识/技能图谱与 Agent 自更新

`examples/java_programming_course_graph.json` 是一门「Java 程序设计」的**待教师审核示例**，包含概念、技能以及先修、包含、支撑和考核关系。教师可将其作为 `PUT /api/v1/python/courses/graph` 的请求体（加登录 Bearer）；`GET /api/v1/python/courses/{course_id}/graph?user_id=...` 可查看版本。课程图谱按用户隔离，导入新版本不会删除历史课件，但会清除旧图谱证据，需要对关联资料执行 `force_reparse=true` 重新挂载。新资料同步时传 `metadata.course_id`，索引成功后系统仅为已有节点补充资源摘要、SHA-256 和摘录证据；不会让未经审核的资料自动创造课程关系。

大纲 LangGraph 在意图解析后自动匹配或读取课程图谱，按“直接生成 / RAG / 图谱 / 图谱+RAG”选择检索路径，记录所用策略和图谱版本。图谱不可用时回退原路径；本轮明确启用 RAG 时不会被历史偏好关掉。教师反馈仍更新长期画像，针对大纲的接受、修改、拒绝记录用于计算策略修改率；至少积累 5 条反馈才参与策略偏好。这里的“自更新”是知识证据、教师画像与有边界的检索策略更新，**不包含模型权重微调或无审核地改变工作流代码**。

教学助手入口的分流 LangGraph 状态包含 `route` 与 `next_stage`：普通聊天进入 `ordinary_chat`，备课进入 `outline_graph`。大纲生成分两段：意图解析与工具检索后先运行 `generate_learning_graphs`，产出知识、技能双图谱；SSE 发出 `learning_graphs` 和 `done(status=awaiting_graph_confirmation)`，服务端保存待确认状态，**此时不生成大纲**。前端默认展示知识图谱，点击按钮切换技能图谱；教师核对后点击“确认双图谱，生成大纲”，以同一 `session_id` 和 `confirm_learning_graphs=true` 再次请求。服务端只使用保存的图谱与意图快照继续 `build_prompt → generate_outline → reflect → memory`，大纲完成后将 `outline.learning_graphs` 落入 Java 侧 `plan_json`；刷新页面也能恢复待确认的双图谱。审核课程图谱优先；没有可用审核图谱时使用模型提议或确定性草案，并明确标记“请核对”。

双图谱分别表达“需要理解的概念、原理及关系”和“能够完成的可观察任务”。模型技能节点包含 `level`、`task`、`assessment`，`skill.knowledge_links` 以 `knowledge_id`、`skill_id` 表达多对多支撑关系。模型输出必须满足节点数、非重复节点、有效内部关系、技能任务与评价标准、支撑覆盖等校验；不合格结果回退为待核对草案。兜底按具体教学语义建立关系，不按节点序号强制串成链。前端按关系分层展示知识结构和技能递进，支持点击技能查看任务与评价，以及展开知识支撑列表；已保存的课程关系和手动布局继续保留。教师确认后的大纲将技能任务、达标依据对应到页面的学生活动与即时检测。
