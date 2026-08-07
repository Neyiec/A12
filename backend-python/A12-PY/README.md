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
EMBEDDING_API_KEY=不填则复用 OPENAI_API_KEY
EMBEDDING_BASE_URL=不填则复用 OPENAI_BASE_URL
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=
REQUEST_TIMEOUT_SECONDS=90
MAX_SLIDE_CONCURRENCY=8
MAX_HTML_RETRIES=1
ENABLE_QUALITY_PIPELINE=true
QUALITY_PRESET=fast
```

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

当前 PPTX 导出是稳定文本版，能保证可下载和基础内容落地。如果要做到浏览器 HTML 级别高保真，需要后续接入 Playwright 截图或 DOM-to-PPTX 转换。
## Project structure

Current package layout:

- `a12_ppt/llm/`: shared LangChain `ChatOpenAI` / `OpenAIEmbeddings` factories, `LLMClient`, and `EmbeddingClient`. All model and embedding calls should go through this package.
- `a12_ppt/presentation/`: outline generation, HTML PPT generation, template loading, HTML validation, and PPTX export.
- `a12_ppt/resources/`: uploaded file text extraction, MySQL URL resource indexing, metadata update, deletion, and RAG chunk retrieval.
- `a12_ppt/outline_chat/`: LangGraph-based ChatGPT-style outline conversation workflow, session storage, PostgreSQL long memory, and teacher-style profile memory.
- `a12_ppt/tools/`: tool-call adapters used by the workflow, such as RAG search and web search.
- Root compatibility modules such as `a12_ppt/generator.py`, `a12_ppt/resource_store.py`, and `a12_ppt/llm_client.py` only re-export the new package implementations. New code should import from the structured packages.
