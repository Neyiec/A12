# API 接口文档


> 项目: A12 — 智能备课与教学成果管理平台  
> 基础路径: `/api/v1`  
> 统一响应格式: `Result<T>` (code=200 成功, message 描述, data 实际数据体)  
> 分页响应: `PageResult<T>` (total 总数, page 当前页, size 每页条数, records 列表)

---

# 后端变更记录（2026-08-10）

本节汇总近期实现中新增的后端接口和文档变更；各接口的详细定义仍保留在下方对应章节。

## 1. 意图识别与大纲会话流程

| 接口 | 变更说明 |
|---|---|
| `POST /api/v1/ai/intent/recognize` | Java 文本意图识别网关；支持 `user_id/session_id`、长会话续接及 Python 意图状态持久化。 |
| `POST /api/v1/ai/intent/recognize-audio` | Java 语音意图识别网关；先把音频提交给 Python 语音转写，再调用 Python 意图识别。 |
| `POST /api/v1/python/intent/recognize` | Python 意图识别已接入大纲对话会话，并保存消息和意图状态。 |
| `POST /api/v1/python/outlines/chat/stream` | 意图信息完整后可在同一会话继续生成大纲；SSE 输出 `tool_result`、`reflection`、`memory`、`outline_delta`、`final`、`done`。 |

重要字段：`session_id`、`need_clarification`、`missing_fields`、`clarification_question`、`status=intent_recognized`。

## 2. RAG、工具调用与反思

| 字段/工具 | 变更说明 |
|---|---|
| `tool_trace` | 记录 RAG、联网搜索和图示工具的调用过程。 |
| `diagram_assets` | 由 `diagram_tool` 生成 Mermaid 图示资源，前端可渲染为 SVG。 |
| `reflection` | 生成质量反思结果，包含问题、修复、重试次数和工具轨迹。 |
| `quality_report` | 供反思节点使用的规则化质量报告。 |
| `teaching_design_chain` | 在原大纲 JSON 之上增加供前端展示的完整教学设计链。 |
| `rag_search` | 上传资料用于增强查询，实际检索覆盖全局和本地知识库索引。 |
| `web_search` | 当 `enable_web=true` 时可选用 DuckDuckGo HTML 联网搜索。 |
| `diagram_tool` | 当意图涉及图示、流程或概念图时触发的规则化 Mermaid 图生成器。 |

Java 将 Python 返回的反思、工具轨迹和质量报告保存到 `AiTask.reflections`，最终大纲 JSON 保存到 `AiTask.plan_json`。

RAG 索引现已支持语义分块、学科感知窗口、混合重排、直接检索接口、索引概览/资源/详情接口、Python 检索日志，以及 Java `kb_retrieval_log` 对大纲生成检索轨迹的持久化。

## 2A. PPTX/Word 导出服务

| 接口 | 变更说明 |
|---|---|
| `POST /api/v1/python/presentations/export/pptx` | 将最终页面 JSON/HTML 转为 `.pptx`；默认以 LandPPT DOM 转换器和 PptxGenJS 生成可编辑对象，复杂 CSS 装饰局部栅格化。 |
| `POST /api/v1/python/lesson-plans/export/docx` | 将教案 JSON 转为带固定教案章节和页脚的 `.docx`。 |
| `POST /api/v1/export-tasks` | Java 导出任务调用 Python，在 `a12.export.local-dir` 保存真实文件，填充 `file_size/file_url/download_url` 并写入 `quality_report`。 |
| `/exports/**` | Java 通过静态资源处理器提供本地导出文件。 |

Java 任务模式支持的导出配置键：`slides`、`lesson_plan`、`outline`、`title`、`filename`、`subject`、`grade`、`duration_minutes`、`teaching_goals`、`requirements`、`reference_text`、`fidelity`、`package_static_assets`。

## 3. 创作工作台页面 JSON 接口

| 接口 | 变更说明 |
|---|---|
| `GET /api/v1/projects/{id}` | `ProjectVO` 新增 `pages`，前端可用完整页面 JSON 打开项目。 |
| `GET /api/v1/projects/{id}/pages` | 读取项目全部页面。 |
| `GET /api/v1/projects/{id}/pages/{pageId}` | 读取单页 JSON。 |
| `POST /api/v1/projects/{id}/pages` | 创建页面。 |
| `PUT /api/v1/projects/{id}/pages/{pageId}` | 使用 `expected_page_version` 保存完整页面 JSON。 |
| `POST /api/v1/projects/{id}/pages/batch-save` | 用于自动保存或离开页面场景的批量保存。 |
| `DELETE /api/v1/projects/{id}/pages/{pageId}` | 删除项目页面。 |
| `POST /api/v1/projects/{id}/components` | 旧版兼容接口，等价于创建页面。 |
| `PATCH /api/v1/projects/{id}/components/{componentId}` | 旧版兼容接口，等价于保存页面。 |

新增页面字段：`page_version`、`expected_page_version`、`client_version`、`autosave`、`dirty`、`last_saved_at`。

校验规则：`page_content` 必须是 JSON 对象字符串；`components` 必须是 JSON 数组字符串；保存时会校验受支持的学科工具组件。

迁移脚本：`backend-java/A12/database/20260810_ws_page_workspace_save_migration.sql`。

## 4. 学科工具组件接口

| 接口 | 用途 |
|---|---|
| `POST /api/v1/projects/tools/validate-component` | 在学科工具组件写入工作台页面 `components` 前进行校验。 |

支持类型：`math_formula`、`chemical_formula`、`mermaid_diagram`、`chart`、`table`、`geometry`。

响应字段：`valid`、`normalized`、`render_hint`、`errors`、`warnings`。

## 5. 资源元数据、标签与分类

| 接口 | 变更说明 |
|---|---|
| `GET /api/v1/resources` | 新增 `category`、`tag`、`access_type`、`allow_ai`、`ai_index_status`、`start_time`、`end_time` 筛选。 |
| `GET /api/v1/resources/tags` | 返回受管标签及实时使用次数。 |
| `POST /api/v1/resources/tags` | 创建或恢复受管标签。 |
| `PATCH /api/v1/resources/tags/{dictId}` | 更新受管标签。 |
| `DELETE /api/v1/resources/tags/{dictId}` | 软删除受管标签。 |
| `GET /api/v1/resources/categories` | 返回受管分类及实时使用次数。 |
| `POST /api/v1/resources/categories` | 创建或恢复受管分类。 |
| `PATCH /api/v1/resources/categories/{dictId}` | 更新受管分类。 |
| `DELETE /api/v1/resources/categories/{dictId}` | 软删除受管分类。 |

资源元数据校验：`categories/tags/authorized_users` 必须是 JSON 数组字符串；`access_type` 必须为 `private/shared/authorized`；`allow_ai` 必须为 `0/1`。

批量操作：`categorize`、`tag`、`delete`、`allow_ai`、`deny_ai`。

删除资源时将软删除 MySQL 数据、删除 Python 索引 `personal:{id}`，并尝试删除原 OSS 对象。

迁移脚本：`backend-java/A12/database/20260810_res_metadata_dictionary_migration.sql`。

新增或变更类：`ResourceTaxonomyDTO`、`Res_Metadata_Dictionary`、`ResMetadataDictionaryMapper`、`MaterialQueryDTO`、`Res_Material`、`MaterialVO`。

## 5A. 社区发布与审核

| 接口 | 变更说明 |
|---|---|
| `GET /api/v1/community/items/{id}` | 仅返回 `status=public` 的内容，草稿、审核中和下线内容不会出现在公开详情。 |
| `PUT /api/v1/community/items/{id}/favorite` | 收藏前校验目标是否公开，并使用真实 `content_type`。 |
| `POST /api/v1/community/items/{id}/view-events` | 写入浏览行为和计数前校验公开可见性。 |
| `POST /api/v1/community/items/{id}/reuse` | 复制到个人项目之前校验公开可见性。 |
| `POST /api/v1/community/submissions` | 创建已校验的草稿；`content_data` 必须为 JSON 对象，`input_variables` 可为 JSON 对象或数组。 |
| `PATCH /api/v1/community/submissions/{id}` | 仅草稿可更新，并持久化包括 `content_type/subject/grade/lesson_type` 在内的全部可编辑字段。 |
| `POST /api/v1/community/submissions/{id}/versions` | 保存版本时向 `version_history` 追加 JSON 快照并递增 `version`。 |
| `POST /api/v1/community/submissions/{id}/submit` | 阻止重复待审任务，并将内容状态更新为 `reviewing`。 |
| `POST /api/v1/community/reports` | 校验目标内容、目标类型、公开可见性及同一用户的重复待处理举报。 |
| `GET /api/v1/community/reports` | 用户举报列表仅返回 `audit_type=report`，不混入投稿审核任务。 |
| `POST /api/v1/admin/moderation/tasks/{id}/decisions` | 仅允许处理待审任务，并通过明确状态机更新内容状态。 |
| `POST /api/v1/admin/reports/{id}/resolution` | 仅允许处理待处理举报，可下线或恢复被举报内容。 |

社区内容状态：`draft` 提交后进入 `reviewing`，通过后进入 `public`；`reject` 进入 `offline`；`rework` 返回 `draft`。

## 5B. 管理端看板统计

| 接口 | 变更说明 |
|---|---|
| `GET /api/v1/admin/dashboard` | 看板改为读取真实业务表，不再返回占位数据。 |

看板数据包括总量、今日增量、7 日趋势、状态/类型分布、质量指标和最近活动。

数据来源：`sys_user`、`res_material`、`adm_resource`、`ai_task`、`exp_task`、`adm_audit`、`com_content`、`sys_log`。

## 6. 依赖与运行说明

大纲工作流使用固定兼容范围：`langchain-core>=1.4.9,<2.0.0`、`langchain-openai>=1.1.0,<2.0.0`、`langgraph>=1.2.5,<1.3.0`。

---

# 一、认证模块

## API-01 POST /api/v1/auth/register

**功能**: 注册教师账号。先通过 API-02 发送验证码到邮箱，再将验证码连同注册信息提交至此接口。服务端校验验证码后创建账号（直接激活，is_active=1）

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `username` | String | **是** | 登录用户名 |
| `password` | String | **是** | 密码（前端传明文，后端哈希后存储） |
| `real_name` | String | **是** | 真实姓名 |
| `phone` | String | **是** | 手机号 |
| `email` | String | **是** | 邮箱 |
| `avatar` | String | 否 | 头像 URL |
| `code` | String | **是** | 验证码 |


**后端 DTO**: ``

**响应 VO**: `Result<UserVO>` — 注册成功返回用户信息

---

## API-02 POST /api/v1/auth/verification-codes

**功能**: 发送邮箱验证码

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `username` | String | **是** | 注册场景填邮箱，密码重置场景填用户名 |
| `scene` | String | **是** | 场景: `register` / `password_reset` |
| `channel` | String | **是** | 发送渠道: 仅支持 `email` |

**后端 DTO**: 暂无独立 DTO

**响应 VO**: `Result<Void>` — 仅返回成功/失败状态

---

## API-03 POST /api/v1/auth/verify

**功能**: 校验验证码（目前仅用于密码重置场景；注册场景的验证码校验在 API-01 中完成）

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `username` | String | **是** | 账号 |
| `code` | String | **是** | 验证码 |
**后端 DTO**: 暂无独立 DTO

**响应 VO**: `Result<Void>`

---

## API-04 POST /api/v1/auth/login

**功能**: 统一验证三类账号（教师/审核员/后台管理员）

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `username` | String | **是** | 账号 |
| `password` | String | **是** | 密码（前端传明文，后端哈希后存储） |

**后端 DTO**: `LoginDTO { username, password }`

**响应 VO**: `Result<LoginVO>` — 含 token、用户基本信息、角色权限

| LoginVO 字段 | 类型 | 说明 |
|---|---|---|
| `token` | String | 会话令牌 |
| `user_id` | int | 用户ID |
| `username` | String | 用户名 |
| `real_name` | String | 真实姓名 |
| `avatar` | String | 头像URL |
| `user_type` | String | 用户类型: `teacher` / `admin` |
| `roles` | String(JSON) | 角色列表 |
| `permissions` | String(JSON) | 权限列表 |
| `last_login_at` | LocalDateTime | 本次登录写入后的最后登录时间 |
| `created_at` | LocalDateTime | 账号创建时间 |

## API-05 POST /api/v1/auth/initial-password-change

**功能**: 批量创建账号后首次登录需强制改密

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `username` | String | **是** | 账号 |
| `initial_password` | String | **是** | 初始密码（前端传明文，后端哈希后校验） |
| `new_password` | String | **是** | 新密码（前端传明文，后端哈希后存储） |

**后端 DTO**: 暂无独立 DTO

**响应 VO**: `Result<LoginVO>` — 改密成功后签发正常会话

---

## API-06 POST /api/v1/auth/password-reset

**功能**: 通过验证码重置密码

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `username` | String | **是** | 账号 |
| `code` | String | **是** | 密码重置验证码 |
| `new_password` | String | **是** | 新密码（前端传明文，后端哈希后存储） |

**后端 DTO**: 暂无独立 DTO

**响应 VO**: `Result<Void>` — 成功后撤销所有已有会话

---

## API-07 POST /api/v1/users/me/password-change

**功能**: 已登录用户修改当前密码

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `current_password` | String | **是** | 当前密码（前端传明文，后端哈希后校验） |
| `new_password` | String | **是** | 新密码（前端传明文，后端哈希后存储） |

**后端 DTO**: 暂无独立 DTO

**响应 VO**: `Result<Void>` — 更新密码后按策略撤销其他会话

---

## API-08 POST /api/v1/auth/logout

**功能**: 退出登录，撤销当前会话

**请求头**: `Authorization: Bearer <token>`

**后端参数**: 无请求体，从请求头获取token

**响应 VO**: `Result<Void>`

---

# 二、用户模块


## API-09 GET /api/v1/users/me

**功能**: 获取当前用户、角色、权限、联系方式和账号状态

**请求头**: `Authorization: Bearer <token>`

**后端参数**: 无（从SecurityContext获取当前用户）

**响应 VO**: `Result<UserVO>`

| UserVO 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int | 用户ID |
| `username` | String | 用户名 |
| `real_name` | String | 真实姓名 |
| `phone` | String | 手机号 |
| `email` | String | 邮箱 |
| `avatar` | String | 头像URL |
| `user_type` | String | 用户类型 |
| `roles` | String(JSON) | 角色列表 |
| `permissions` | String(JSON) | 权限列表 |
| `is_active` | int | 是否激活: 1是/0否 |
| `email_verified` | Integer | 邮箱是否已验证: 1是/0否 |
| `phone_verified` | Integer | 手机号是否已验证: 1是/0否 |
| `last_login_at` | LocalDateTime | 最后登录时间 |
| `last_login_ip` | String | 最后登录IP |
| `password_changed_at` | LocalDateTime | 密码最后修改时间 |
| `deleted_at` | LocalDateTime | 软删除时间，正常账号为 `null` |
| `created_at` | LocalDateTime | 创建时间 |
| `updated_at` | LocalDateTime | 更新时间 |

---

## API-10 GET /api/v1/users/by-username

**功能**: 根据用户名查询用户ID和基本信息

**查询参数**: username(String, 必填) — 用户名

**响应 VO**: Result<{id: int, username: String, real_name: String, email: String}>

---

## API-11 GET /api/v1/users/by-email

**功能**: 根据邮箱查询用户ID和基本信息

**查询参数**: email(String, 必填) — 邮箱

**响应 VO**: Result<{id: int, username: String, real_name: String, email: String}>

---

# 三、AI 教学引擎

> 当前定位: Java AI 模块保留为业务网关和任务记录层。真正的大纲生成、RAG/联网增强、长期记忆、教师画像和 HTML PPT 生成由 Python 服务承担。Java 负责登录态、权限、任务状态、项目关联、审计日志，并转发 Python 接口。
> MySQL 建表语句已按该定位更新到 `table_created.txt`；如果旧库已建表，可使用 `mysql_ai_gateway_migration.sql` 做无损增量迁移。

## API-12 POST /api/v1/ai/sessions

**功能**: 创建 Java 侧备课会话和 AI 任务记录。此接口不直接调用模型，只创建业务壳子，后续消息会转发 Python 对话式大纲接口。

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `title` | String | **是** | 会话标题 |
| `subject` | String | **是** | 学科 |
| `grade` | String | **是** | 年级 |
| `messages` | String(JSON) | 否 | 初始对话消息 |
| `uploaded_refs` | String(JSON) | 否 | 参考资料ID列表 |
| `status` | String | 否 | 默认 `active` |
| `resource_ids` | String(JSON) | 否 | Python 上传资料返回的 resource_id 列表，例如 `["res_xxx"]` |
| `enable_rag` | Boolean | 否 | 后续默认是否启用 RAG |
| `enable_web` | Boolean | 否 | 后续默认是否启用联网 |
| `slide_count` | int | 否 | 期望页数，默认 8 |

**后端 DTO**: `TaskCreateDTO { title, subject, grade, status, uploaded_refs, plan_json, messages, resource_ids, enable_rag, enable_web, slide_count }`

**响应 VO**: `Result<TaskVO>` — 含 Java 会话ID `conversation_id`。Java 会尽量同步创建 Python 大纲对话会话并写入 `python_session_id`；如果 Python 服务暂时不可用，会在 API-13 首次发送消息时自动创建。`resource_ids/enable_rag/enable_web/slide_count` 会保存为本会话默认生成选项；后续 API-13/API-13A 没传这些字段时自动沿用，传了则以本轮请求为准。

---

## API-12A GET /api/v1/ai/sessions

**功能**: 查询当前登录用户的 AI 备课会话列表，用于 ChatGPT 式左侧历史会话栏。

**请求头**: `Authorization: Bearer <token>`

**响应 VO**: `Result<List<ConversationVO>>`

| ConversationVO 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int | Java 会话ID，后续发送消息、读取详情、重命名、删除都使用该 ID |
| `user_id` | int | 用户ID |
| `title` | String | 会话标题 |
| `status` | String | `active` / `completed` / `archived` 等 |
| `messages` | String(JSON) | 轻量消息历史，数组元素包含 `role/content`，可直接用于恢复对话页面 |
| `context_summary` | String | Python intent 或前端摘要 |
| `python_session_id` | String | Python 大纲对话会话ID |
| `last_question` | String | 最近一次澄清问题；为空表示没有待回答问题 |
| `created_at` | LocalDateTime | 创建时间 |
| `updated_at` | LocalDateTime | 更新时间 |

---

## API-12B GET /api/v1/ai/sessions/{id}

**功能**: 获取某个 Java 会话详情和历史消息。前端点击左侧历史会话时调用此接口，把 `messages` 渲染回聊天窗口，再用同一个 `{id}` 调 API-13 继续对话。

**路径参数**: `id` — Java 会话ID

**请求头**: `Authorization: Bearer <token>`

**响应 VO**: `Result<ConversationVO>`

---

## API-12C PATCH /api/v1/ai/sessions/{id}

**功能**: 重命名会话或更新会话状态。Java 会同步更新本地 `ai_conversation`；如果已有 `python_session_id`，也会同步更新 Python 会话标题。

**路径参数**: `id` — Java 会话ID

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `title` | String | 否 | 新会话标题 |
| `status` | String | 否 | 新状态，例如 `active` / `archived` |
| `context_summary` | String | 否 | 前端摘要 |

**后端 DTO**: `ConversationDTO { title, status, context_summary }`

**响应 VO**: `Result<ConversationVO>`

---

## API-12D DELETE /api/v1/ai/sessions/{id}

**功能**: 删除当前用户的 Java 会话及其关联 `ai_task`；如果已有 `python_session_id`，会同步删除 Python 会话。用于前端历史会话栏删除操作。

**路径参数**: `id` — Java 会话ID

**响应 VO**: `Result<Void>`

---

## API-13 POST /api/v1/ai/sessions/{id}/messages

**功能**: 对话中补充需求、回答澄清问题或提交反馈。Java 会把本轮消息转发给 Python `/api/v1/python/outlines/chat/stream`，聚合 SSE 结果后写回 `ai_conversation` 和 `ai_task`。

**路径参数**: `id` — 会话ID

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `message` | String | 推荐 | 用户本轮自然语言输入；新前端建议传这个字段 |
| `messages` | String(JSON/String) | 否 | 兼容旧字段；当 `message` 为空时作为本轮输入 |
| `resource_ids` | String(JSON) | 否 | 上传参考资料ID列表，例如 `["res_xxx"]`；用于提取格式、语气、案例、内容，并参与构造 RAG 检索 query，不作为向量库检索范围 |
| `enable_rag` | Boolean | 否 | 是否启用本地知识库 RAG；为 `true` 时使用用户输入、已识别意图和上传参考资料内容融合检索 |
| `enable_web` | Boolean | 否 | 是否启用 Python 联网搜索 |
| `slide_count` | int | 否 | 期望页数 |
| `known_context` | String(JSON) | 否 | 已知上下文，例如 `{"title":"光合作用","subject":"生物","grade":"七年级"}` |
| `title` | String | 否 | 更新会话标题 |
| `status` | String | 否 | 更新会话状态 |
| `context_summary` | String | 否 | 前端或 Java 侧摘要 |

**后端 DTO**: `ConversationDTO { title, status, messages, context_summary, message, resource_ids, enable_rag, enable_web, slide_count, known_context }`

**响应 VO**: `Result<ConversationVO>` — 更新后的会话信息。Java 会把本轮用户消息和 Python assistant 结果追加写入 `messages`，前端切换回该会话时可直接恢复聊天窗口。若 Python 返回澄清问题，`last_question` 有值；若生成完成，`TaskVO.plan_json` 会保存 Python 返回的大纲。`enable_rag/enable_web` 为本轮覆盖开关；不传时沿用 API-12 创建会话时保存的默认开关。

---

## API-13S POST /api/v1/ai/sessions/{id}/messages/stream

**功能**: 与 API-13 等价但以 `text/event-stream`（SSE）流式发送会话消息。Java 后台线程把 Python `/api/v1/python/outlines/chat/stream` 的事件原样逐条透传给前端（边生成边回传），不等待整轮生成完成；流结束后 Java 会把本轮用户消息和生成结果一次性落库。适合需要实时展示大纲生成进度的聊天场景。

**响应类型**: `text/event-stream`

**路径参数**: `id` — 会话ID（Java 会话）; 会话必须归属当前登录用户，否则返回错误并关闭流。

**请求体 (JSON)** — 与 API-13 完全一致
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `message` | String | 推荐 | 用户本轮自然语言输入 |
| `messages` | String(JSON/String) | 否 | 兼容旧字段；当 `message` 为空时作为本轮输入 |
| `resource_ids` | String(JSON) | 否 | 上传参考资料ID列表，例如 `["res_xxx"]`；用于提取格式、语气、案例、内容，并参与构造 RAG 检索 query，不作为向量库检索范围 |
| `enable_rag` | Boolean | 否 | 是否启用本地知识库 RAG；不传沿用会话默认 |
| `enable_web` | Boolean | 否 | 是否启用 Python 联网搜索；不传沿用会话默认 |
| `slide_count` | int | 否 | 期望页数 |
| `known_context` | String(JSON) | 否 | 已知上下文，例如 `{"title":"光合作用","subject":"生物","grade":"七年级"}` |
| `title` | String | 否 | 更新会话标题（流结束后随消息一起落库） |
| `status` | String | 否 | 更新会话状态 |
| `context_summary` | String | 否 | 前端或 Java 侧摘要 |

**SSE 事件** — Python 事件原样透传，data 保持 Python 原始 JSON 结构；Java 在流结束后追加 `done` 事件：
| event | data 说明 |
|---|---|
| `session` | 返回 `user_id` 和 `session_id`（Python 会话ID），Java 会写入 `python_session_id` |
| `question` | 信息不足时返回澄清问题，含 `session_id`、`question`、`intent`；前端展示给用户并等待下一轮回复 |
| `outline_delta` | 单页大纲增量，data 形如 `{"slide": {...}}` 单页大纲对象；前端可逐页追加显示 |
| `memory` | 长期记忆数据对象 |
| `reflection` | 大纲生成后的质量反思、问题列表、修正记录、工具调用轨迹 |
| `final` | 完整大纲结果，含 `outline_id`、`outline`、`slides`、`title` 等；前端可直接据此渲染最终大纲 |
| `error` | Python 节点异常，data 含 `message` |
| `done` | **Java 追加**，本轮完成标志：`{"status": "completed"\|"need_clarification"\|"failed", "message": ""}`；随后关闭连接 |

**结束语义**: 流正常结束时 Java 先统一调用与 API-13 共享的落库逻辑（写入 `ai_conversation.messages`、更新 `last_question`、保存 `plan_json` 到大纲任务、记录审计日志），再发送 `done` 事件并关闭连接。若后台处理/透传过程发生异常，Java 只发送一个 `error` 事件（data 含 `message`）后立即关闭连接，不发送 `done`。`SseEmitter` 超时约 620 秒，与后端调用 Python 的 600 秒超时对齐；生成耗时较长时需相应调大前端请求/读取超时，避免中途断开。

**后端接口**: `AIController#sendMessageStream` → `AIService#sendMessageStream`（后台线程 `runOutlineStream`）→ `PythonPptClient#streamOutlineChatStreamed`。原始 JSON 接口 API-13 仍保留，供 `CreationWorkspace.vue` 使用。

> Spring Boot 的 HTTP 响应被上层网关/代理缓存或切分时，SSE 可能被缓冲；如前端迟迟收不到事件，需确认代理未关闭响应流缓冲（`X-Accel-Buffering: no` 等）。本接口需 JWT 认证。

---

## API-13A POST /api/v1/ai/sessions/{id}/audio-messages

**功能**: 语音输入对话编排接口。前端上传教师语音到 Java，Java 先调用 Python `/api/v1/python/audio/asr` 转写文本，再把转写文本作为本轮 `message` 复用 API-13 的对话生成逻辑。前端不需要自己串联 Python ASR 和大纲对话接口。

**请求类型**: `multipart/form-data`

**路径参数**: `id` — 会话ID

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `file` | File | **是** | 语音文件，建议 `wav/mp3/m4a/webm` |
| `language` | String | 否 | 语音语言，例如 `zh` |
| `message` | String | 否 | 手动补充文本；如果同时传，会拼接在语音转写文本前面 |
| `resource_ids` | String(JSON) | 否 | 上传参考资料ID列表，例如 `["res_xxx"]`；用于提取格式、语气、案例、内容，并参与构造 RAG 检索 query，不作为向量库检索范围 |
| `enable_rag` | Boolean | 否 | 是否启用本地知识库 RAG；为 `true` 时使用用户输入、已识别意图和上传参考资料内容融合检索 |
| `enable_web` | Boolean | 否 | 是否启用 Python 联网搜索 |
| `slide_count` | int | 否 | 期望页数 |
| `known_context` | String(JSON) | 否 | 已知上下文，例如 `{"title":"光合作用","subject":"生物","grade":"七年级"}` |
| `context_summary` | String | 否 | 前端或 Java 侧摘要 |

**响应 VO**: `Result<ConversationVO>` — 与 API-13 一致。Java 会把最终转写后的文本写入会话消息历史。

---

## API-13B POST /api/v1/ai/intent/recognize

**功能**: 独立意图识别接口。只接收教师文本输入和可选上下文，返回结构化教学意图、缺失字段、是否需要澄清和置信度；不创建会话、不生成大纲、不触发 PPT/Word 生成。适合前端在进入正式备课流程前做“需求理解预检”。

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `user_id` | String | 否 | 用户ID；不传也可识别，传入后会透传给 Python intent |
| `session_id` | String | 否 | Python 会话ID；首次不传会自动创建，后续传回可继续同一会话 |
| `title` | String | 否 | 会话标题；首次创建会话时可传 |
| `message` | String | **是** | 教师自然语言输入 |
| `history` | String(JSON) | 否 | 历史消息数组，例如 `[{"role":"user","content":"..."}]` |
| `known_context` | String(JSON) | 否 | 前端已知字段，例如 `{"title":"光合作用","subject":"生物"}` |
| `resource_ids` | String(JSON) | 否 | 上传参考资料ID列表，例如 `["res_xxx"]`；用于意图记录和后续 RAG query 融合，不代表向量库检索范围 |
| `enable_rag` | Boolean | 否 | 是否记录本轮启用 RAG 意图；本接口不执行检索 |
| `enable_web` | Boolean | 否 | 是否记录本轮启用联网意图；本接口不执行联网 |
| `slide_count` | int | 否 | 默认页数，默认 `8` |
| `language` | String | 否 | 输出语言，默认 `zh-CN` |

**后端 DTO**: `IntentRecognitionDTO { user_id, session_id, title, message, history, known_context, resource_ids, enable_rag, enable_web, slide_count, language }`

**响应 VO**: `Result<IntentRecognitionVO>`。如果请求带 `user_id`，Python 会自动创建或复用 PostgreSQL 长期会话，并在响应中返回 `session_id`；前端下一轮继续传该 `session_id` 即可延续同一条意图识别对话。

| IntentRecognitionVO 字段 | 类型 | 说明 |
|---|---|---|
| `intent` | Object(JSON) | 结构化意图，包含主题、学科、年级、课时、知识点、互动需求等 |
| `need_clarification` | Boolean | 是否还需要追问 |
| `missing_fields` | List<String> | 缺失关键字段，当前包括 `title/grade/subject` |
| `clarification_question` | String | 可直接展示给教师的澄清问题 |
| `confidence` | double | 识别置信度，范围 `0.1~0.95` |
| `input_type` | String | `text` |
| `model_used` | Boolean | 是否使用大模型完成抽取；false 表示走规则兜底 |
| `user_id` | String | 可选，保存会话时返回 |
| `session_id` | String | 可选，Python 长期会话ID |
| `postgres_available` | Boolean | 可选，是否成功接入 PostgreSQL；false 时会退回进程内存储 |

**请求示例**
```json
{
  "user_id": "10001",
  "title": "光合作用备课",
  "message": "帮我做一个七年级生物光合作用8页PPT，加入一个课堂小游戏",
  "known_context": "{}",
  "resource_ids": "[\"res_abcd1234\"]",
  "enable_rag": true,
  "enable_web": false,
  "slide_count": 8,
  "language": "zh-CN"
}
```

**响应示例**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "intent": {
      "title": "光合作用",
      "subject": "生物",
      "grade": "七年级",
      "requirements": "帮我做一个七年级生物光合作用8页PPT，加入一个课堂小游戏",
      "slide_count": 8,
      "language": "zh-CN",
      "enable_web": false,
      "enable_rag": true,
      "resource_ids": ["res_abcd1234"],
      "user_id": "10001",
      "interactive_policy": {
        "needs_interactive_assets": true,
        "needs_animation": false,
        "needs_game": true,
        "preferred_formats": ["html5"]
      }
    },
    "need_clarification": false,
    "missing_fields": [],
    "clarification_question": "",
    "confidence": 0.86,
    "input_type": "text",
    "model_used": true,
    "user_id": "10001",
    "session_id": "outline_chat_abcd1234",
    "postgres_available": true
  }
}
```

**长期存储说明**: 该接口复用 Python 大纲对话的 PostgreSQL 表：`a12_outline_chat_session` 保存合并后的 `intent/status/last_message_at`，`a12_outline_chat_message` 保存本轮用户输入和 assistant 的识别摘要，消息 metadata 中会记录 `type=intent_recognition_input/intent_recognition_result`、`confidence`、`missing_fields` 等信息。

---

## API-13C POST /api/v1/ai/intent/recognize-audio

**功能**: 独立语音意图识别接口。前端上传教师语音到 Java，Java 先调用 Python ASR 转写，再调用 Python `/api/v1/python/intent/recognize` 返回结构化意图。此接口不创建会话、不生成大纲。

**请求类型**: `multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `file` | File | **是** | 教师语音文件，建议 `wav/mp3/m4a/webm` |
| `language` | String | 否 | 语音语言，例如 `zh`；不传则模型自动识别 |
| `user_id` | String | 否 | 用户ID |
| `session_id` | String | 否 | Python 会话ID；首次不传会自动创建 |
| `title` | String | 否 | 会话标题 |
| `message` | String | 否 | 手动补充文本；如果同时传，会拼接在语音转写文本前面 |
| `history` | String(JSON) | 否 | 历史消息数组 |
| `known_context` | String(JSON) | 否 | 前端已知字段 |
| `resource_ids` | String(JSON) | 否 | 上传参考资料ID列表；用于意图记录和后续 RAG query 融合，不代表向量库检索范围 |
| `enable_rag` | Boolean | 否 | 是否记录启用 RAG 意图 |
| `enable_web` | Boolean | 否 | 是否记录启用联网意图 |
| `slide_count` | int | 否 | 默认页数，默认 `8` |

**响应 VO**: `Result<IntentRecognitionVO>` — 字段同 API-13B，额外包含 `asr` 字段，保存语音转写结果。

**响应示例**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "intent": {
      "title": "光合作用",
      "subject": "生物",
      "grade": "七年级",
      "slide_count": 8,
      "language": "zh-CN"
    },
    "need_clarification": false,
    "missing_fields": [],
    "clarification_question": "",
    "confidence": 0.86,
    "input_type": "audio",
    "model_used": true,
    "asr": {
      "text": "帮我做一个七年级生物光合作用8页PPT",
      "status": "completed"
    }
  }
}
```

---

## API-14 GET /api/v1/ai/sessions/{id}/plan

**功能**: 获取当前教学设计大纲及版本。大纲内容来自 Python 生成结果，Java 存在 `ai_task.plan_json`。

**路径参数**: `id` — 会话ID

**后端参数**: 无请求体

**响应 VO**: `Result<TaskVO>` — 其中的 `plan_json`、`python_session_id`、`python_outline_id` 和 `plan_confirm_status` 字段包含大纲和 Python 关联信息。

---

## API-15 POST /api/v1/ai/sessions/{id}/plan-confirmations

**功能**: 确认、退回或补充教学设计大纲

**路径参数**: `id` — 会话ID

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `action` | String | **是** | 操作: `confirm` / `reject` / `supplement` |
| `comment` | String | 否 | 退回或补充说明 |
| `plan_version` | int | **是** | 大纲版本号（防并发冲突） |

**后端 DTO**: 暂无独立 DTO

**响应 VO**: `Result<Void>`

---

## API-16 POST /api/v1/ai/sessions/{id}/runs

**功能**: 标记 Java 侧执行任务。当前不在 Java 内部生成 PPT，后续整套 PPT HTML 应调用 Python API-138。

**路径参数**: `id` — 会话ID

**后端参数**: 无请求体

**响应 VO**: `Result<TaskVO>` — 含任务ID，status 转为 `executing`，`exec_steps` 标记等待 Python PPT 生成。

---

## API-17 GET /api/v1/ai/runs/{runId}

**功能**: 查询生成、反思及失败状态

**路径参数**: `runId` — 执行任务ID

**后端参数**: 无请求体

**响应 VO**: `Result<TaskVO>`

---

## API-18 GET /api/v1/ai/runs/{runId}/events

**功能**: 通过 SSE 接收阶段、进度和预览更新，支持断线续传

**路径参数**: `runId` — 执行任务ID

**查询参数**:
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `lastEventId` | String | 否 | 断线续传时携带最后收到的 eventId |

**后端 DTO**: 无，流式返回

**响应**: 返回 `text/event-stream`（SSE），包含阶段进度和预览数据

---

# 四、项目模块

> **权限说明**：所有需要对项目进行写操作的接口，均需校验当前用户是否为项目拥有者（user_id == currentId）或被授权用户（currentId 存在于 permissions JSON 数组中）。

## API-20 POST /api/v1/projects

**功能**: 创建个人教学项目或社区派生项目

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `project_name` | String | **是** | 项目名称 |
| `project_type` | String | **是** | 类型: `ppt` / `word` / `h5` / `mixed` |
| `status` | String | 否 | 默认 `draft` |
| `snapshots` | String(JSON) | 否 | 版本快照列表 |
| `edit_history` | String(JSON) | 否 | 编辑历史 |
| `permissions` | String(JSON) | 否 | 初始授权用户ID列表，一般创建时不传 |

**后端 DTO**: `ProjectCreateDTO { project_name, project_type, status, snapshots, edit_history, permissions }`

**响应 VO**: `Result<ProjectVO>`

---

## API-21 GET /api/v1/projects

**功能**: 按名称、课程、成果类型、状态和更新时间分页查询项目

**查询参数**:
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `keyword` | String | 否 | 名称/课程关键字模糊搜索 |
| `project_type` | String | 否 | 筛选类型: `ppt`/`word`/`h5`/`mixed` |
| `status` | String | 否 | 筛选状态: `draft`/`editing`/`confirmed`/`exported` |
| `user_id` | Integer | 否 | 筛选用户（后端自动设为当前用户） |
| `page` | int | 否 | 默认1 |
| `size` | int | 否 | 默认10 |

**后端 DTO**: `ProjectQueryDTO extends PageQuery { user_id, project_type, status, keyword }`

**响应 VO**: `Result<PageResult<ProjectVO>>`

---

## API-22 GET /api/v1/projects/{id}

**功能**: 获取项目内容、元数据、当前版本和权限
**权限**: 仅项目拥有者或被授权用户可以查看

**路径参数**: `id` — 项目ID

**响应 VO**: `Result<ProjectVO>` — 现在会包含 `pages` 页面列表，前端打开创意工作台时可一次性拿到完整页面 JSON。

| ProjectVO 新增字段 | 类型 | 说明 |
|---|---|---|
| `pages` | List<PageVO> | 项目页面列表，按 `page_order` 升序排列 |

| PageVO 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int | 页面ID |
| `project_id` | int | 所属项目ID |
| `page_order` | int | 页面顺序 |
| `page_type` | String | 页面类型 |
| `page_title` | String | 页面标题 |
| `page_content` | String(JSON) | 完整页面 JSON，例如 `html/css/elements/layout/notes` |
| `components` | String(JSON) | 组件列表 JSON |
| `page_version` | int | 页面级版本号，保存时用于乐观锁 |
| `client_version` | String | 前端客户端版本或草稿版本标识 |
| `autosave` | Boolean | 是否自动保存产生 |
| `dirty` | Boolean | 前端是否仍标记为脏数据 |
| `last_saved_at` | LocalDateTime | 最近保存时间 |

---

## API-22A GET /api/v1/projects/{id}/pages

**功能**: 读取项目页面列表，供创意工作台恢复完整页面 JSON。

**响应 VO**: `Result<List<PageVO>>`

---

## API-22B GET /api/v1/projects/{id}/pages/{pageId}

**功能**: 读取单个页面 JSON。

**响应 VO**: `Result<PageVO>`

---

## API-22C POST /api/v1/projects/{id}/pages

**功能**: 新建页面并保存页面 JSON。后端校验 `page_content` 必须是合法 JSON Object，`components` 必须是合法 JSON Array。

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `page_order` | int | 否 | 页面顺序，不传则追加到末尾 |
| `page_type` | String | 否 | 页面类型，默认 `content` |
| `page_title` | String | 否 | 页面标题 |
| `page_content` | String(JSON Object) | 否 | 页面完整 JSON，默认 `{}`，建议包含 `html/css/elements/layout/notes` |
| `components` | String(JSON Array) | 否 | 组件列表 JSON，默认 `[]` |
| `client_version` | String | 否 | 前端草稿版本标识 |
| `autosave` | Boolean | 否 | 是否自动保存 |
| `dirty` | Boolean | 否 | 前端脏数据标记 |

**响应 VO**: `Result<PageVO>`

---

## API-22D PUT /api/v1/projects/{id}/pages/{pageId}

**功能**: 保存单个页面完整 JSON。使用 `expected_page_version` 做页面级乐观锁，避免多端覆盖。

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `expected_page_version` | int | **是** | 前端当前持有的页面版本号 |
| `page_order` | int | 否 | 新页面顺序 |
| `page_type` | String | 否 | 新页面类型 |
| `page_title` | String | 否 | 新页面标题 |
| `page_content` | String(JSON Object) | 否 | 新页面完整 JSON，必须以 `{}` 对象形式提交 |
| `components` | String(JSON Array) | 否 | 新组件列表 JSON，必须以 `[]` 数组形式提交 |
| `client_version` | String | 否 | 前端草稿版本标识 |
| `autosave` | Boolean | 否 | 是否自动保存 |
| `dirty` | Boolean | 否 | 前端脏数据标记 |

**响应 VO**: `Result<PageVO>` — 保存成功后 `page_version` 自动加 1。

---

## API-22E POST /api/v1/projects/{id}/pages/batch-save

**功能**: 批量保存创意工作台页面 JSON，适合自动保存或离开页面前保存。

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `current_version` | int | 否 | 项目版本号；传入时后端会校验是否与当前项目一致 |
| `client_version` | String | 否 | 批量保存的客户端草稿版本 |
| `autosave` | Boolean | 否 | 是否自动保存 |
| `pages` | List<PageDTO> | **是** | 页面列表；已有页面传 `page_id/expected_page_version`，新页面不传 `page_id` |

**响应 VO**: `Result<List<PageVO>>`

---

## API-22F DELETE /api/v1/projects/{id}/pages/{pageId}

**功能**: 删除项目中的单个页面。

**响应 VO**: `Result<Void>`

---

## API-22G POST /api/v1/projects/tools/validate-component

**功能**：在创作工作台保存学科工具组件 JSON 前进行校验，支持公式编辑器、化学式/分子数据、Mermaid 图、图表、表格和几何画板组件。

**请求体（JSON）**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `component_id` | String | 否 | 前端组件 ID |
| `type` | String | **是** | 组件类型：`math_formula` / `chemical_formula` / `mermaid_diagram` / `chart` / `table` / `geometry` |
| `data` | Object | **是** | 核心组件数据；公式使用 `latex`，化学组件使用 `formula/smiles/molfile`，图表使用 `option` |
| `render` | Object | 否 | 前端渲染配置 |
| `style` | Object | 否 | 前端样式配置 |

**响应 VO**：`Result<SubjectComponentValidateVO>`

| 字段 | 类型 | 说明 |
|---|---|---|
| `valid` | Boolean | 是否校验通过 |
| `normalized` | Object | 可存入 `components` 的规范化组件 JSON |
| `render_hint` | Object | 建议的前端渲染引擎，例如 `katex`、`kekule`、`echarts`、`jsxgraph` |
| `errors` | List<String> | 阻断保存的校验错误 |
| `warnings` | List<String> | 不阻断保存的警告 |

**保存时校验**：`POST /projects/{id}/pages`、`PUT /projects/{id}/pages/{pageId}` 和 `POST /projects/{id}/pages/batch-save` 也会校验 `components` 内受支持的学科组件；未知的普通组件允许保存，不会阻断操作。

**Example**
```json
{
  "type": "math_formula",
  "data": {
    "latex": "E=mc^2",
    "display_mode": true
  }
}
```

---

## API-23 PATCH /api/v1/projects/{id}

**功能**: 修改项目名称、类型、状态等元数据，使用版本号防并发覆盖

**路径参数**: `id` — 项目ID

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `project_name` | String | 否 | 新名称 |
| `project_type` | String | 否 | 新类型 |
| `status` | String | 否 | 新状态 |
| `current_version` | int | **是** | 当前版本号（乐观锁，防止覆盖） |
| `snapshots` | String(JSON) | 否 | 兼容旧字段，新的版本快照主要写入 `ws_version.snapshot_data` |
| `edit_history` | String(JSON) | 否 | 编辑历史 |
| `permissions` | String(JSON) | 否 | 授权用户ID列表 |

**后端 DTO**: `ProjectCreateDTO`

**响应 VO**: `Result<ProjectVO>`

---

## API-24 POST /api/v1/projects/{id}/copies

**功能**: 复制有权访问的项目并创建新的私有项目

**路径参数**: `id` — 源项目ID

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `new_name` | String | 否 | 新项目名称（默认原名称+副本） |

**后端 DTO**: 暂无独立 DTO

**响应 VO**: `Result<ProjectVO>` — 新项目的完整信息

---

## API-25 POST /api/v1/projects/{id}/archive

**功能**: 归档项目，禁止继续编辑

**路径参数**: `id` — 项目ID

**后端参数**: 无请求体

**响应 VO**: `Result<ProjectVO>` — 状态更新为 `archived`

---

## API-26 POST /api/v1/projects/{id}/restore

**功能**: 将归档或可恢复删除状态的项目恢复为可用

**路径参数**: `id` — 项目ID

**后端参数**: 无请求体

**响应 VO**: `Result<ProjectVO>`

---

## API-27 DELETE /api/v1/projects/{id}

**功能**: 校验权限后软删除项目。后端写入 `deleted_at`，项目从普通查询中隐藏，页面和版本历史会保留，可通过 API-26 恢复。

**路径参数**: `id` — 项目ID

**后端参数**: 无请求体

**响应 VO**: `Result<Void>`

---

## API-28 POST /api/v1/projects/{id}/ai-revisions

**功能**: 对指定页面或组件执行自然语言修改

**路径参数**: `id` — 项目ID

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `target_type` | String | **是** | 修改目标: `page` / `component` |
| `target_id` | String | **是** | 目标标识 |
| `instruction` | String | **是** | 自然语言修改指令 |
| `context` | String(JSON) | 否 | 附加上下文 |

**后端 DTO**: 暂无独立 DTO

**响应 VO**: `Result<PageVO>` — 修改后的页面内容

---

## API-29 POST /api/v1/projects/{id}/components

**功能**: 兼容旧接口。当前实际等价于新建页面并保存 `page_content/components`，新前端建议改用 API-22C。

**路径参数**: `id` — 项目ID

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `page_id` | int | **是** | 目标页面ID |
| `page_order` | int | **是** | 页面顺序 |
| `page_type` | String | **是** | 页面类型: `cover`/`toc`/`content`/`summary` |
| `page_title` | String | 否 | 页面标题 |
| `page_content` | String(JSON) | 否 | 页面内容 |
| `components` | String(JSON) | 否 | 组件列表 |

**后端 DTO**: `PageDTO { page_order, page_type, page_title, page_content, components }`

**响应 VO**: `Result<PageVO>`

---

## API-30 PATCH /api/v1/projects/{id}/components/{componentId}

**功能**: 兼容旧接口。当前实际等价于保存页面 JSON，新前端建议改用 API-22D。

**路径参数**: `id` — 项目ID, `componentId` — 组件ID

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `page_content` | String(JSON) | 否 | 更新的页面内容 |
| `components` | String(JSON) | 否 | 更新的组件列表 |

**后端 DTO**: `PageDTO`

**响应 VO**: `Result<PageVO>`

---

## API-31 POST /api/v1/projects/{id}/versions

**功能**: 保存不可变项目版本并返回版本编号。后端会把当前项目元数据和页面列表写入 `ws_version.snapshot_data`，用于后续恢复。

**路径参数**: `id` — 项目ID

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `description` | String | 否 | 版本说明 |

**后端 DTO**: 暂无独立 DTO

**响应 VO**: `Result<{version_id: int, version_number: int}>`

---

## API-32 GET /api/v1/projects/{id}/versions

**功能**: 分页查询项目历史版本、创建人、说明和创建时间

**路径参数**: `id` — 项目ID

**查询参数**:
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `page` | int | 否 | 默认1 |
| `size` | int | 否 | 默认10 |

**后端 DTO**: `PageQuery { page, size }`

**响应 VO**: `Result<PageResult<VersionVO>>`

| VersionVO 字段 | 类型 | 说明 |
|---|---|---|
| `version_id` | int | 版本记录ID |
| `version_number` | int | 项目内版本号 |
| `description` | String | 版本说明 |
| `snapshot_data` | String(JSON) | 版本快照，包含项目元数据和页面列表 |
| `created_by` | Integer | 创建人ID |
| `created_at` | LocalDateTime | 创建时间 |

---

## API-33 GET /api/v1/projects/{id}/versions/{versionId}/diff

**功能**: 将目标版本与指定版本或当前版本进行差异比较

**路径参数**: `id` — 项目ID, `versionId` — 目标版本ID

**查询参数**:
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `compare_version_id` | Integer | 否 | 对比版本ID（不传则比较当前版本） |

**响应 VO**: `Result<{differences: Array, summary: String}>`

---

## API-34 POST /api/v1/projects/{id}/versions/{versionId}/restore

**功能**: 基于历史版本快照恢复项目元数据和页面列表，并创建新的当前版本号，不修改原历史记录。

**路径参数**: `id` — 项目ID, `versionId` — 源版本ID

**后端参数**: 无请求体

**响应 VO**: `Result<ProjectVO>` — 恢复后的项目（current_version 递增）

---

## API-35 POST /api/v1/projects/{id}/permissions

**功能**: 添加项目授权用户。仅项目创建者（拥有者）可以调用，将被授权用户的ID加入到项目的 `permissions` JSON 数组中（去重）。

**路径参数**: `id` — 项目ID

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `user_id` | Integer | **是** | 要授权的用户ID（需已注册） |

**后端 DTO**: `ProjectPermissionDTO { user_id }`

**响应 VO**: `Result<ProjectVO>` — 更新后的项目信息（含最新的 `permissions` 列表）

---

# 五、个人资源库

## API-36 POST /api/v1/resources/upload-tokens

 **功能**: 获取 OSS 签名上传 URL。后端生成唯一 objectKey 并返回签名 PUT URL，前端拿到 URL 后直传阿里云 OSS

 **请求体 (JSON)**
 | 字段 | 类型 | 必填 | 说明 |
 |---|---|---|---|
 | `file_name` | String | **是** | 文件名 |
 | `file_type` | String | 否 | 文件类型: `word`/`pdf`/`ppt`/`txt`/`image`/`audio`/`video`（不传则根据扩展名自动检测） |
 | `description` | String | 否 | 文件描述 |
 | `replace_target_id` | Integer | 否 | 要替换的资源ID（替换时后端会清理旧文件并软删除旧记录） |

 **后端 DTO**: `UploadTokenDTO { file_name, file_type, description, replace_target_id }`

 **响应 VO**: `Result<UploadTokenVO>`

 | UploadTokenVO 字段 | 类型 | 说明 |
 |---|---|---|
 | `object_key` | String | OSS 对象键 |
 | `upload_url` | String | 签名 PUT URL（有效期60分钟） |
 | `expires_at` | LocalDateTime | URL 过期时间 |

---

## API-37 POST /api/v1/resources/uploaded-files

 **功能**: 前端直传 OSS 成功后通知后端确认。后端验证文件已存在于 OSS，创建个人资源记录并存入 MySQL。个人资源默认 `allow_ai=0`，不会立刻进入 Python 向量/索引库；用户后续开启“允许 AI 使用”后，Java 会通知 Python 解析 URL 并保存索引。

 **请求体 (JSON)**
 | 字段 | 类型 | 必填 | 说明 |
 |---|---|---|---|
 | `object_key` | String | **是** | API-36 返回的 object_key |
 | `file_name` | String | **是** | 文件名 |
 | `file_size` | long | **是** | 文件大小（字节） |
 | `file_type` | String | 否 | 文件类型，不传则根据扩展名自动检测 |
 | `description` | String | 否 | 文件描述 |
 | `replace_target_id` | Integer | 否 | 要替换的资源ID |

 **后端 DTO**: `ResourceUploadConfirmDTO { object_key, file_name, file_size, file_type, description, replace_target_id }`

 **响应 VO**: `Result<MaterialVO>` — 资源元数据，包含 `ai_index_status / ai_indexed_at / ai_index_error`

---

## API-38 GET /api/v1/resources

**功能**：按关键字、文件类型、标签、分类、访问类型、AI 权限、AI 索引状态和时间范围查询当前用户资源。

**查询参数**：
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `keyword` | String | 否 | 在文件名、描述、标签和分类中搜索 |
| `file_type` | String | 否 | `word/pdf/ppt/txt/image/audio/video/other` |
| `category` | String | 否 | 精确匹配 `categories` JSON 数组中的一项 |
| `tag` | String | 否 | 精确匹配 `tags` JSON 数组中的一项 |
| `access_type` | String | 否 | `private/shared/authorized` |
| `allow_ai` | int | 否 | `0/1`，是否允许 AI 使用该资源 |
| `ai_index_status` | String | 否 | `pending/indexing/completed/failed/disabled` |
| `user_id` | Integer | 否 | 后端会用当前用户 ID 覆盖该值 |
| `start_time` | LocalDateTime | 否 | 创建时间下限 |
| `end_time` | LocalDateTime | 否 | 创建时间上限 |
| `page` | int | 否 | 默认 `1` |
| `size` | int | 否 | 默认 `10` |

**后端 DTO**：`MaterialQueryDTO extends PageQuery { user_id, file_type, category, tag, access_type, allow_ai, ai_index_status, keyword, start_time, end_time }`

**响应 VO**：`Result<PageResult<MaterialVO>>`

---

## API-38A GET /api/v1/resources/tags

**功能**：返回受管标签字典项及其在当前用户资源中的实时使用次数；资源中存在但未纳入字典的标签也会返回，并标记 `managed=false`。

**响应 VO**：`Result<List<{id: int|null, name: String, type: "tag", count: int, color: String|null, sort_order: int, managed: boolean}>>`

---

## API-38B GET /api/v1/resources/categories

**功能**：返回受管分类字典项及其在当前用户资源中的实时使用次数；资源中存在但未纳入字典的分类也会返回，并标记 `managed=false`。

**响应 VO**：`Result<List<{id: int|null, name: String, type: "category", count: int, color: String|null, sort_order: int, managed: boolean}>>`

---

## API-38C POST /api/v1/resources/tags

**功能**：创建或恢复一个受管标签字典项。

**请求体（JSON）**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | String | **是** | 标签名，最多 80 个字符 |
| `color` | String | 否 | 前端展示颜色 |
| `sort_order` | int | 否 | 排序值，默认 `1000` |

**响应 VO**：`Result<{id, name, type, count, color, sort_order, managed}>`

---

## API-38D PATCH /api/v1/resources/tags/{dictId}

**功能**：更新一个受管标签字典项；修改字典名称不会重写已有资源元数据。

**请求体（JSON）**：同 API-38C，全部字段可选。

**响应 VO**：`Result<{id, name, type, count, color, sort_order, managed}>`

---

## API-38E DELETE /api/v1/resources/tags/{dictId}

**功能**：软删除一个受管标签字典项，不会移除已有资源元数据中的标签值。

**响应 VO**：`Result<Void>`

---

## API-38F POST /api/v1/resources/categories

**功能**：创建或恢复一个受管分类字典项。

**请求体（JSON）**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | String | **是** | 分类名，最多 80 个字符 |
| `color` | String | 否 | 前端展示颜色 |
| `sort_order` | int | 否 | 排序值，默认 `1000` |

**响应 VO**：`Result<{id, name, type, count, color, sort_order, managed}>`

---

## API-38G PATCH /api/v1/resources/categories/{dictId}

**功能**：更新一个受管分类字典项；修改字典名称不会重写已有资源元数据。

**请求体（JSON）**：同 API-38F，全部字段可选。

**响应 VO**：`Result<{id, name, type, count, color, sort_order, managed}>`

---

## API-38H DELETE /api/v1/resources/categories/{dictId}

**功能**：软删除一个受管分类字典项，不会移除已有资源元数据中的分类值。

**响应 VO**：`Result<Void>`

---

## API-39 GET /api/v1/resources/{id}

**功能**: 获取资源元数据、分类、解析状态和当前权限摘要

**路径参数**: `id` — 资源ID

**响应 VO**: `Result<MaterialVO>`

---

## API-40 PATCH /api/v1/resources/{id}

**功能**：更新文件名、描述、缩略图、标签、分类、访问类型及 AI 权限等资源元数据。

**路径参数**：`id`—资源 ID

**请求体（JSON）**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `file_name` | String | 否 | 新展示文件名 |
| `thumbnail` | String | 否 | 缩略图 URL |
| `description` | String | 否 | 资源描述 |
| `categories` | String(JSON Array) | 否 | 分类，例如 `["数学","函数"]`；后端校验 JSON 数组 |
| `tags` | String(JSON Array) | 否 | 标签，例如 `["重点","案例"]`；后端校验 JSON 数组 |
| `access_type` | String | 否 | `private/shared/authorized` |
| `authorized_users` | String(JSON Array) | 否 | 被授权用户 ID 列表；后端校验 JSON 数组 |
| `allow_ai` | int | 否 | `0/1`；修改后同步更新 Python 资源索引的可用状态 |

**后端 DTO**：`MaterialDTO`

**响应 VO**：`Result<MaterialVO>`

---

## API-41 DELETE /api/v1/resources/{id}

**功能**：软删除资源、删除对应 Python 索引 `personal:{id}`，并尝试删除原 OSS 对象。

**路径参数**：`id`—资源 ID

**请求体**：无

**响应 VO**：`Result<Void>`

---

## API-42 POST /api/v1/resources/batch-actions

**功能**：批量删除资源、启用/禁用 AI 使用、替换分类或替换标签。

**请求体（JSON）**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `idempotent_key` | String | 否 | 客户端幂等键；当前仅由客户端记录 |
| `action` | String | **是** | `categorize` / `tag` / `delete` / `allow_ai` / `deny_ai` |
| `resource_ids` | String | **是** | 资源 ID；支持 `1,2,3` 形式的逗号字符串或 `[1,2,3]` 形式的 JSON 数组字符串 |
| `target` | String | 否 | `categorize/tag` 的目标值，可为单个字符串或 JSON 数组字符串 |

**后端 DTO**：`ResourceBatchActionDTO`

**响应 VO**：`Result<Void>`

---

## API-43 GET /api/v1/resources/{id}/permission

**功能**: 获取资源私有/共享状态、共享对象及访问权限

**路径参数**: `id` — 资源ID

**响应 VO**: `Result<{access_type: String, authorized_users: String(JSON), allow_ai: int}>`

---

## API-44 PUT /api/v1/resources/{id}/permission

**功能**: 设置资源私有状态、共享对象及访问权限。`allow_ai` 从 `0` 改为 `1` 时，Java 会调用 Python `/api/v1/python/resources/index/sync` 解析并保存索引；从 `1` 改为 `0` 时，不重复解析，只把索引 metadata 里的 `available/allow_ai` 改为 `false`。

**路径参数**: `id` — 资源ID

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `access_type` | String | **是** | `private` / `shared` / `authorized` |
| `authorized_users` | String(JSON) | 否 | 授权用户ID列表 |
| `allow_ai` | int | 否 | 允许AI访问: 1/0 |

**后端 DTO**: `MaterialDTO { access_type, authorized_users, allow_ai }`

**响应 VO**: `Result<MaterialVO>`

---

## API-45 GET /api/v1/resources/{id}/audit-logs

**功能**: 查看权限和元数据修改记录

**路径参数**: `id` — 资源ID

**查询参数**:
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `page` | int | 否 | 默认1 |
| `size` | int | 否 | 默认10 |

**响应 VO**: `Result<PageResult<LogVO>>`

---

## API-46 POST /api/v1/resources/{id}/download-url

**功能**: 校验权限并生成短时下载地址

**路径参数**: `id` — 资源ID
**后端参数**: 无请求体
**响应 VO**: `Result<{download_url: String, expires_at: LocalDateTime}>`

---

# 六、成果导出中心

## API-47 POST /api/v1/projects/{id}/export-prechecks

**功能**: 检查项目快照、素材、字体、兼容性、版权和敏感信息

**路径参数**: `id` — 项目ID
**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `snapshot_version` | Integer | **是** | 绑定的快照版本号 |
| `export_type` | String | **是** | 导出类型: `pptx` / `word` / `package` |
**响应 VO**: `Result<{passed: boolean, warnings: Array, errors: Array}>`

---

## API-48 POST /api/v1/export-tasks

**功能**: 创建导出任务并生成真实文件。Java 会读取项目页面 JSON 或 `config.slides/config.lesson_plan`，调用 Python 文件生成服务，保存文件到 `a12.export.local-dir`，并返回可访问的 `file_url/download_url`。

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `project_id` | int | **是** | 项目ID |
| `snapshot_version` | Integer | **是** | 快照版本 |
| `export_type` | String | **是** | 导出类型: `pptx` / `word` / `package` |
| `config` | String(JSON) | 否 | 导出配置参数 |

**后端 DTO**: `ExportTaskDTO { project_id, snapshot_version, export_type, config }`
**响应 VO**: `Result<ExportTaskVO>`

**config 支持字段**
| 字段 | 类型 | 说明 |
|---|---|---|
| `slides` | List<Object> | PPTX/package 导出优先使用；为空时从 `ws_page.page_content` 自动转换 |
| `lesson_plan` | Object | Word 导出优先使用；为空时 Java 先调用 Python `/lesson-plans/generate` 生成教案 JSON |
| `outline` | Object | 生成 Word 教案时作为大纲输入 |
| `title` | String | 导出标题 |
| `filename` | String | 文件名 |
| `fidelity` | String | PPTX 导出模式：`dom_editable`（默认）/ `high_fidelity` / `editable_text`（兼容值） |
| `package_static_assets` | Boolean | 是否打包互动资源 |
| `subject/grade/duration_minutes/teaching_goals/requirements/reference_text` | Mixed | 生成 Word 教案时传给 Python |

**文件保存规则**: 文件保存到 `a12.export.local-dir`，默认 `data/exports`；访问前缀为 `a12.export.public-prefix`，默认 `/exports`。生成成功时 `file_size > 0`，`file_status=available`，`status=success`；生成失败时 `status=failed`，`error_msg` 和 `quality_report.errors` 会记录失败原因。

---

## API-49 GET /api/v1/export-tasks

**功能**: 分页查询本人或获授权的导出任务

**查询参数**:
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `status` | String | 否 | 筛选状态 |
| `export_type` | String | 否 | 筛选导出类型 |
| `page` | int | 否 | 默认1 |
| `size` | int | 否 | 默认10 |

**响应 VO**: `Result<PageResult<ExportTaskVO>>`

---

## API-50 GET /api/v1/export-tasks/{id}

**功能**: 查看进度、失败原因、质量状态和文件状态

**路径参数**: `id` — 导出任务ID
**响应 VO**: `Result<ExportTaskVO>`

| ExportTaskVO 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int | 任务ID |
| `user_id` | int | 用户ID |
| `project_id` | int | 项目ID |
| `snapshot_version` | Integer | 快照版本 |
| `export_type` | String | 导出类型 |
| `status` | String | 状态: `queued`/`generating`/`checking`/`success`/`partial`/`failed`/`cancelled` |
| `config` | String(JSON) | 导出配置 |
| `file_name` | String | 文件名 |
| `file_url` | String | 文件URL |
| `file_size` | long | 文件大小 |
| `download_url` | String | 下载地址 |
| `url_expire_at` | LocalDateTime | 链接过期时间 |
| `file_status` | String | 文件状态: `available`/`expired`/`cleaned` |
| `quality_report` | String(JSON) | 质量报告 |
| `error_msg` | String | 错误信息 |
| `progress` | Integer | 任务进度: 0-100 |
| `retry_count` | Integer | 重试次数 |
| `worker_id` | String | 执行节点标识 |
| `started_at` | LocalDateTime | 开始时间 |
| `created_at` | LocalDateTime | 创建时间 |
| `updated_at` | LocalDateTime | 更新时间 |
| `completed_at` | LocalDateTime | 完成时间 |

---

## API-51 POST /api/v1/export-tasks/{id}/cancel
**功能**: 取消排队中或生成中的任务
**路径参数**: `id` — 导出任务ID
**响应 VO**: `Result<ExportTaskVO>`

---

## API-52 POST /api/v1/export-tasks/{id}/retry
**功能**: 按原快照和参数重新执行
**路径参数**: `id` — 导出任务ID
**响应 VO**: `Result<ExportTaskVO>`

---

## API-53 GET /api/v1/export-tasks/{id}/quality-report
**功能**: 获取导出质量报告、警告和降级项
**路径参数**: `id` — 导出任务ID
**响应 VO**: `Result<{quality_report: String(JSON)}>`

---

## API-54 GET /api/v1/export-artifacts/{id}
**功能**: 获取成果文件元数据、文件状态、缩略图清单和可预览类型
**路径参数**: `id` — 成果文件ID
**响应 VO**: `Result<ExportTaskVO>`

---

## API-55 POST /api/v1/export-artifacts/{id}/preview-url
**功能**: 生成成果缩略图或预览文件的短时访问地址
**路径参数**: `id` — 成果文件ID
**响应 VO**: `Result<{preview_url: String, expires_at: LocalDateTime}>`

---

## API-56 POST /api/v1/export-artifacts/{id}/download-url
**功能**: 生成成果文件的短时下载链接
**路径参数**: `id` — 成果文件ID
**响应 VO**: `Result<{download_url: String, expires_at: LocalDateTime}>`

## API-56B POST /export-artifacts/{id}/file

**功能**: 生成成果文件的短时下载链接
**路径参数**: `id` — 成果文件ID
**响应 VO**: `成果文件字节流`

---

# 七、社区模块

## API-57 GET /api/v1/community/items
**功能**: 检索公开可用的 Skill 和教学案例

**查询参数**:
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `content_type` | String | 否 | 内容类型: `skill` / `lesson_case` |
| `subject` | String | 否 | 学科 |
| `grade` | String | 否 | 年级 |
| `keyword` | String | 否 | 关键字搜索 |
| `page` | int | 否 | 默认1 |
| `size` | int | 否 | 默认10 |

**后端 DTO**: `ContentQueryDTO extends PageQuery { content_type, subject, grade, status, keyword }`
**响应 VO**: `Result<PageResult<ContentVO>>`

---

## API-58 GET /api/v1/community/items/{id}
**功能**: 获取公开内容的用途、变量、示例、作者、版本和授权信息；仅允许读取 `status=public` 的内容
**路径参数**: `id` — 内容ID
**响应 VO**: `Result<ContentVO>`

| ContentVO 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int | 内容ID |
| `content_type` | String | 内容类型 |
| `author_id` | int | 作者ID |
| `title` | String | 标题 |
| `description` | String | 描述 |
| `subject` | String | 学科 |
| `grade` | String | 年级 |
| `lesson_type` | String | 课型 |
| `content_data` | String(JSON) | 内容数据 |
| `input_variables` | String(JSON) | 输入变量 |
| `example_effect` | String | 示例效果 |
| `version` | int | 版本号 |
| `version_history` | String(JSON) | 版本历史 |
| `license` | String | 授权信息 |
| `status` | String | 状态 |
| `is_top` | int | 是否置顶 |
| `view_count` | int | 浏览数 |
| `use_count` | int | 使用数 |
| `created_at` | LocalDateTime | 创建时间 |
| `updated_at` | LocalDateTime | 更新时间 |

---

## API-59 PUT /api/v1/community/items/{id}/favorite
**功能**: 收藏指定公开社区内容；若内容不存在或非 `public` 状态则拒绝
**路径参数**: `id` — 内容ID
**响应 VO**: `Result<Void>`

---

## API-60 DELETE /api/v1/community/items/{id}/favorite
**功能**: 取消收藏
**路径参数**: `id` — 内容ID
**响应 VO**: `Result<Void>`

---

## API-61 POST /api/v1/community/items/{id}/view-events
**功能**: 记录公开内容浏览事件（按用户和内容幂等更新）；非公开内容不会写入浏览记录
**路径参数**: `id` — 内容ID
**响应 VO**: `Result<Void>`

---

## API-62 GET /api/v1/community/favorites
**功能**: 分页查询当前用户收藏的公开可用内容
**查询参数**: page(默认1), size(默认10)
**响应 VO**: `Result<PageResult<ContentVO>>`

---

## API-63 GET /api/v1/community/recent-views
**功能**: 分页查询当前用户最近浏览记录
**查询参数**: page(默认1), size(默认10)
**响应 VO**: `Result<PageResult<{item: ContentVO, viewed_at: LocalDateTime}>>`

---

## API-64 DELETE /api/v1/community/recent-views/{itemId}
**功能**: 移除指定最近浏览记录
**路径参数**: `itemId` — 内容ID
**响应 VO**: `Result<Void>`

---

## API-65 POST /api/v1/community/items/{id}/reuse
**功能**: 校验公开状态、版本和授权，复制到个人空间并返回派生项目
**路径参数**: `id` — 内容ID
**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `target_version` | Integer | 否 | 复用指定版本（默认最新） |
| `new_project_name` | String | 否 | 派生项目名称 |
**后端 DTO**: `InteractionDTO { action_type, target_type, target_id, target_version, bind_materials }`
**响应 VO**: `Result<ProjectVO>`

---

## API-66 POST /api/v1/community/submissions
**功能**: 创建投稿草稿；后端会规范化 `content_type` 并校验 JSON 字段
**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `content_type` | String | **是** | `skill` / `lesson_case` |
| `title` | String | **是** | 标题 |
| `description` | String | 否 | 描述 |
| `subject` | String | 否 | 学科 |
| `grade` | String | 否 | 年级 |
| `lesson_type` | String | 否 | 课型 |
| `content_data` | String(JSON Object) | 否 | 内容数据，必须是合法 JSON 对象 |
| `input_variables` | String(JSON Object/Array) | 否 | 输入变量，必须是合法 JSON 对象或数组 |
| `example_effect` | String | 否 | 示例效果 |
| `license` | String | **是** | 授权协议 |
**后端 DTO**: `ContentDTO { content_type, title, description, subject, grade, lesson_type, content_data, input_variables, example_effect, license }`
**响应 VO**: `Result<ContentVO>`

**校验规则**: `content_type` 支持 `skill`、`lesson_case`，兼容 `case -> lesson_case`；创建时 `content_type/title/license` 必填；新建内容初始状态为 `draft`，`version=1`，`version_history=[]`。

---

## API-67 GET /api/v1/community/submissions
**功能**: 分页查询当前教师的投稿及审核状态
**查询参数**: status(否), page(否), size(否)
**后端 DTO**: `ContentQueryDTO extends PageQuery { status }`
**响应 VO**: `Result<PageResult<ContentVO>>`

---

## API-68 GET /api/v1/community/submissions/{id}
**功能**: 获取投稿草稿、版本、审核状态和退回意见
**路径参数**: `id` — 投稿ID
**响应 VO**: `Result<ContentVO>`

---

## API-69 PATCH /api/v1/community/submissions/{id}
**功能**: 修改当前教师自己的草稿投稿；当前后端仅允许 `status=draft` 修改
**路径参数**: `id` — 投稿ID
**请求体**: 与 API-66 相同结构，全选填
**后端 DTO**: `ContentDTO`
**响应 VO**: `Result<ContentVO>`

**可更新字段**: `content_type/title/description/subject/grade/lesson_type/content_data/input_variables/example_effect/license`。其中 `content_data` 和 `input_variables` 使用 API-66 相同 JSON 校验规则。

---

## API-70 POST /api/v1/community/submissions/{id}/versions
**功能**: 保存投稿版本快照
**路径参数**: `id` — 投稿ID
**请求体**: description(否)
**响应 VO**: `Result<{version_id, version_number}>`

**版本规则**: 后端将当前 `title/subject/grade/lesson_type/content_data/input_variables/example_effect/license` 等字段追加到 `version_history` JSON 数组，并将 `version` 自增。

---

## API-71 POST /api/v1/community/submissions/{id}/submit
**功能**: 提交审核；状态从 `draft` 变更为 `reviewing`，并创建一条 `audit_type=audit` 的待审任务
**路径参数**: `id` — 投稿ID
**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `source_declaration` | String | **是** | 来源声明 |
| `notes` | String | 否 | 审核备注 |
**响应 VO**: `Result<Void>`

**约束**: 仅作者本人可提交；仅 `draft` 可提交；同一内容存在 `pending` 审核任务时会拒绝重复提交。

---

## API-72 POST /api/v1/community/reports
**功能**: 创建举报记录；后端校验举报目标存在、类型匹配且为公开内容
**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `target_type` | String | **是** | 举报对象类型: `skill` / `lesson_case`，可兼容 `case` |
| `target_id` | int | **是** | 举报对象ID |
| `reason` | String | **是** | 举报原因 |
| `description` | String | 否 | 详细描述 |
**后端 DTO**: `AuditDTO { audit_type, target_type, target_id, reason, action, comment }`
**响应 VO**: `Result<{report_id: int}>`

**约束**: 同一用户对同一内容已有 `pending` 举报时拒绝重复提交；举报任务写入 `adm_audit.audit_type=report`。

---

## API-73 GET /api/v1/community/reports
**功能**: 分页查询本人举报及处理状态；仅返回 `audit_type=report`
**查询参数**: status(否), page(否), size(否)
**响应 VO**: `Result<PageResult<AuditVO>>`

---

## API-74 GET /api/v1/community/reports/{id}
**功能**: 获取举报受理状态及处理结果；仅允许举报人读取自己的举报
**路径参数**: `id` — 举报ID
**响应 VO**: `Result<AuditVO>`

---

# 八、后台 — 用户权限模块

## API-75 GET /api/v1/admin/users
**功能**: 按角色、账号状态和关键词分页查询用户
**查询参数**: keyword(否), user_type(否), is_active(否), page(默认1), size(默认10)
**后端 DTO**: `UserQueryDTO extends PageQuery { keyword, user_type, is_active }`
**响应 VO**: `Result<PageResult<UserVO>>`

---

## API-76 GET /api/v1/admin/users/{id}
**功能**: 获取用户状态、角色、权限摘要及安全状态
**路径参数**: `id` — 用户ID
**响应 VO**: `Result<UserVO>`

---

## API-77 PATCH /api/v1/admin/users/{id}/status
**功能**: 启用、停用或锁定用户账号
**路径参数**: `id` — 用户ID
**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `is_active` | int | **是** | 0=停用, 1=启用, -1=锁定 |
**响应 VO**: `Result<UserVO>`

---

## API-78 POST /api/v1/admin/users
**功能**: 创建单个后台账号
**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `username` | String | **是** | 用户名 |
| `password` | String | **是** | 密码（前端传明文，后端哈希后存储） |
| `real_name` | String | **是** | 真实姓名 |
| `phone` | String | 否 | 手机号 |
| `email` | String | 否 | 邮箱 |
| `user_type` | String | **是** | `admin` |
| `roles` | String(JSON) | **是** | 角色列表 |
**后端 DTO**: `UserDTO { username, password, real_name, phone, email, avatar, user_type, roles, permissions, is_active }`
**响应 VO**: `Result<UserVO>`

---

## API-79 POST /api/v1/admin/users/batch
**功能**: 批量创建后台账号
**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `idempotent_key` | String | **是** | 幂等键 |
| `users` | Array | **是** | 用户列表（每个同API-78结构，密码传明文，后端哈希后存储） |
**响应 VO**: `Result<{results: Array<{username, success, initial_credentials, error}>>}`

---

## API-80 GET /api/v1/admin/roles
**功能**: 查询后台角色、权限集合及审核范围
**响应 VO**: `Result<Array<{role_id, role_code, role_name, description, permissions, audit_scope, status, member_count, created_at}>>`
**说明**: permissions 为权限矩阵 JSON 字符串 `[{"moduleKey","moduleLabel","actions":[{"key","label","granted"}]}]`；member_count 为该角色下有效（未软删除）用户数；status 1=启用/0=停用；结果缓存 10 分钟，角色/权限变更时自动失效
**后端实现**: `AdminUserServiceImpl#listRoles`（Redis 缓存键 `admin:roles`）

---

## API-80A POST /api/v1/admin/roles
**功能**: 创建后台角色（不包含权限配置，创建后通过 API-82 配置权限）
**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `role_code` | String | **是** | 角色标识，全局唯一，小写字母开头，可含小写字母/数字/下划线 |
| `role_name` | String | **是** | 角色名称，全局唯一，最长 50 字符 |
| `description` | String | 否 | 角色说明，最长 255 字符 |
| `sort_order` | Integer | 否 | 展示排序，缺省追加到现有角色末尾 |
| `status` | Integer | 否 | 1=启用（默认）/ 0=停用 |
**后端 DTO**: `RoleDTO`
**响应 VO**: `Result<Map>` — 与 API-80 列表项结构一致（新建角色 permissions 全未授权、member_count 为 0）
**说明**: 创建成功后清除 `admin:roles` 角色列表缓存
**所需权限**: `roles:create`

---

## API-80B PUT /api/v1/admin/roles/{id}
**功能**: 更新角色信息（仅更新请求体中传入的字段）
**路径参数**: `id` — 角色ID
**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `role_name` | String | 否 | 角色名称，全局唯一（排除自身），最长 50 字符 |
| `description` | String | 否 | 角色说明，最长 255 字符 |
| `sort_order` | Integer | 否 | 展示排序 |
| `status` | Integer | 否 | 1=启用 / 0=停用 |
**说明**: `role_code` 为角色标识不可修改；启停角色会即时改变持有该角色用户的有效权限（其鉴权缓存同步失效）
**后端 DTO**: `RoleUpdateDTO`
**响应 VO**: `Result<Map>` — 与 API-80 列表项结构一致
**所需权限**: `roles:edit`

---

## API-80C DELETE /api/v1/admin/roles/{id}
**功能**: 删除角色（硬删除，`sys_user_role`/`sys_role_permission` 关联行由外键级联清理）
**路径参数**: `id` — 角色ID
**说明**: 删除后持有该角色的用户将立即失去对应权限（其鉴权缓存同步失效），操作与影响人数写入业务日志；前端应在删除前向管理员二次确认并展示成员数
**响应 VO**: `Result<Void>`
**所需权限**: `roles:delete`

---

## API-81 PUT /api/v1/admin/users/{id}/roles
**功能**: 分配系统管理员或内容审核员角色
**路径参数**: `id` — 用户ID
**请求体 (JSON)**: `roles`(String JSON) **是**
**响应 VO**: `Result<UserVO>`

---

## API-82 PUT /api/v1/admin/roles/{id}/permissions
**功能**: 配置后台功能权限及审核范围
**路径参数**: `id` — 角色ID
**请求体 (JSON)**: `permissions`(String JSON) **是**
**响应 VO**: `Result<Void>`

---

## API-82A PUT /api/v1/admin/users/{id}
**功能**: 更新后台用户信息（仅更新请求体中非空的字段，未传字段保持原值）
**路径参数**: `id` — 用户ID
**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `username` | String | 否 | 用户名，变更时校验重名（软删除用户不参与查重） |
| `password` | String | 否 | 明文密码，传入即重置（后端哈希存储并更新 password_changed_at），不传保持原密码 |
| `real_name` | String | 否 | 真实姓名 |
| `phone` | String | 否 | 手机号 |
| `email` | String | 否 | 邮箱 |
| `avatar` | String | 否 | 头像URL |
| `roles` | String(JSON) | 否 | 角色列表 |
| `permissions` | String(JSON) | 否 | 权限列表 |
**说明**: 账号启用/停用走 API-77，本接口不处理 `is_active`；`user_type` 不支持通过本接口修改
**后端 DTO**: `UserDTO`（同 API-78）
**响应 VO**: `Result<UserVO>`

---

## API-82B DELETE /api/v1/admin/users/{id}
**功能**: 删除用户（软删除：置 `deleted_at` 并停用，所有查询自动过滤已删除用户）
**路径参数**: `id` — 用户ID
**说明**: 不能删除当前登录账号；删除后同时清除该用户的 Redis 登录态与资料缓存，并写入业务日志
**响应 VO**: `Result<Void>`

---

# 九、后台 — 公共资源模块

## API-83 GET /api/v1/admin/public-resources
**功能**: 分页查询公共资源
**查询参数**: resource_type(否), status(否), page(默认1), size(默认10)
**响应 VO**: `Result<PageResult<ResourceVO>>`

| ResourceVO 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int | 资源ID |
| `resource_type` | String | 资源类型 |
| `title` | String | 标题 |
| `subject` | String | 学科 |
| `grade` | String | 年级 |
| `file_url` | String | 文件URL |
| `template_data` | String(JSON) | 模板数据 |
| `thumbnail` | String | 缩略图 |
| `description` | String | 描述 |
| `status` | int | 状态 |
| `uploaded_by` | Integer | 上传者ID |
| `ai_index_status` | String | Python资源索引状态: `pending/indexing/completed/failed/disabled` |
| `ai_indexed_at` | LocalDateTime | Python索引完成时间 |
| `ai_index_error` | String | Python索引失败原因 |
| `created_at` | LocalDateTime | 创建时间 |
| `updated_at` | LocalDateTime | 更新时间 |

---

## API-84 POST /api/v1/admin/public-resources/uploads
**功能**: 创建公共资源上传会话。该接口只创建 MySQL 记录和 OSS 上传 URL，资源状态为待完成，Python 此时不会解析。
**请求体 (JSON)**: resource_type(**是**), title(**是**), file_name(建议传), file_type(建议传), file_size(**是**)
**后端 DTO**: `ResourceDTO { resource_type, title, subject, grade, file_name, file_type, file_url, template_data, thumbnail, description, status }`
**说明**: `resource_type` 是业务分类，不是文件类型。前端应传 `file_name/file_type`，Java 会保留 OSS objectKey 后缀，并在完成上传后把真实 `file_type` 传给 Python，避免公共资源入库时被识别为 `other`。
**响应 VO**: `Result<{upload_id, upload_url, expires_at}>`

---

## API-85 POST /api/v1/admin/public-resources/uploads/{id}/complete
**功能**: 完成上传并触发 Python 资源解析和索引保存。Java 会读取 MySQL 中的 `file_url/uploaded_by/id/status` 等字段，向 Python 发送同步请求；Python 使用 `public:{id}` 作为唯一资源键，已解析过且 URL/大小未变化时只跳过解析并更新 metadata。
**路径参数**: `id` — 上传会话ID
**响应 VO**: `Result<ResourceVO>`

---

## API-86 GET /api/v1/admin/public-resources/{id}
**功能**: 获取公共资源详情
**路径参数**: `id` — 资源ID
**响应 VO**: `Result<ResourceVO>`

---

## API-87 PATCH /api/v1/admin/public-resources/{id}
**功能**: 更新公共资源元数据
**路径参数**: `id` — 资源ID
**请求体**: title(否), subject(否), grade(否), description(否)
**后端 DTO**: `ResourceDTO`
**响应 VO**: `Result<ResourceVO>`

---

## API-88 PUT /api/v1/admin/public-resources/{id}/status
**功能**: 启用/停用公共资源。该接口不会重复解析文件，只会把 Python 索引 metadata 中的 `available/allow_ai` 同步为对应状态。
**路径参数**: `id` — 资源ID
**请求体**: status(int) **是** 0=停用 1=启用
**响应 VO**: `Result<ResourceVO>`

---

## API-89 GET /api/v1/admin/public-resources/{id}/processing-status
**功能**: 查询处理状态
**路径参数**: `id` — 资源ID
**响应 VO**: `Result<{security_check, parse_status, index_status, error_msg}>`

---

## API-89-1 POST /api/v1/admin/public-resources/ai-index/bootstrap
**功能**: 初始化或修复 Python 资源索引库。Java 遍历 MySQL 中所有 `adm_resource.status=1` 的公共资源，以及 `res_material.status=1 AND allow_ai=1` 的个人资源，批量推送给 Python。Python 侧保证幂等，同一资源默认只解析保存一次。公共资源的 `adm_resource.resource_type` 是业务分类，Java 会额外根据 `file_url` 后缀推断真实 `file_type` 后传给 Python。

**查询参数**: `force_reparse`，Boolean，默认 `false`。为 `true` 时即使资源已索引也会重新下载 URL 并解析。

**资源ID约定**:
| 资源来源 | Python resource_id 格式 | MySQL 表 | 说明 |
|---|---|---|---|
| 公共资源 | `public:{adm_resource.id}` | `adm_resource` | metadata 包含 `uploaded_by/resource_id/available/file_url/mysql_table/resource_type/detected_file_type` |
| AI可用个人资源 | `personal:{res_material.id}` | `res_material` | metadata 包含 `owner_user_id/uploaded_by/allow_ai/available/file_url/mysql_table` |

**响应 VO**: `Result<{total, indexed, skipped, failed, results}>`

---

## API-89-2 GET /api/v1/admin/public-resources/ai-index/overview
**功能**: 知识索引总览统计（KPI 数据源）。透传 Python `GET /resources/index/overview`，实时聚合 PostgreSQL `a12_resource_index`。
**权限**: `resources:view`
**响应 VO**: `Result<{postgres_available, embedding_dimensions, resource_count, chunk_count, retrieval_log_count, groups: [{source_type, parse_status, available, allow_ai, resource_count, chunk_count}]}>`

---

## API-89-3 GET /api/v1/admin/public-resources/ai-index/tasks
**功能**: 分页查询知识索引任务列表（public + personal 双域）。透传 Python `GET /resources/index/resources`，随后 Java 对当页 items 按域各一次批量查询 MySQL `ai_index_status`，合成 `effective_status`（indexing 覆盖 PG 终态 parse_status）。
**权限**: `resources:view`
**查询参数**: source_type(public/personal，否), parse_status(completed/failed，否), keyword(否，title/resource_id ILIKE), page(默认1), size(默认10，上限200)
**响应 VO**: `Result<{total, limit, offset, items: [{resource_key, source_type, resource_id, title, available, allow_ai, parse_status, error_message, text_length, chunk_count, metadata, indexed_at, updated_at, effective_status}]}>`

---

## API-89-4 GET /api/v1/admin/public-resources/ai-index/resources/{sourceType}/{resourceId}
**功能**: 单资源索引明细（含真实分块）。透传 Python `GET /resources/index/resources/{source_type}/{resource_id}`；资源无 PG 行时返回 400「该资源尚未建立索引或索引已被移除」。
**权限**: `resources:view`
**路径参数**: sourceType(public/personal), resourceId(数字ID)
**查询参数**: chunk_limit(默认50，0-200)
**响应 VO**: `Result<{resource_key, ..., chunks: [{chunk_id, chunk_index, content(≤1500字符), metadata}]}>`

---

## API-89-5 POST /api/v1/admin/public-resources/ai-index/search
**功能**: 知识条目真实向量检索（pgvector 余弦召回 + 混合重排），与大纲工作流 RAG 共用 `search_context` 链路，命中写入 `a12_retrieval_log`。
**权限**: `resources:view`
**请求体 (JSON)**: query(String) **是**；source_type(String，否，public/personal)；top_k(int，否，1-30，默认10)
**响应 VO**: `Result<{query, matches: [{resource_id("public:3"), chunk_id, chunk_index, content, metadata(含 title), score(0-1), rank, match_type}], search_mode, latency_ms}>`

---

## API-89-6 POST /api/v1/admin/public-resources/ai-index/{sourceType}/{resourceId}/reparse
**功能**: 单资源强制重解析（双域统一入口，异步）。public 复用 `/{id}/reparse` 链路（adm_resource 校验 status=1 → 标 indexing → PublicResourceIndexSyncService @Async）；personal 校验 res_material allow_ai=1 → 标 indexing → ResourceIndexSyncService @Async（force_reparse=true）。两者均立即返回，前端轮询任务行 parse_status 获取终态。
**权限**: `resources:edit`
**路径参数**: sourceType(public/personal), resourceId(数字ID)
**响应 VO**: `Result<{source_type, resource_id, status}>`（status 固定 'indexing'）

---

# 十、后台 — 内容审核与举报处理

## API-90 GET /api/v1/admin/moderation/tasks
**功能**: 按状态、对象类型和审核员查询审核任务
**查询参数**: status(否), target_type(否), handler_id(否), page(默认1), size(默认10)
**响应 VO**: `Result<PageResult<AuditVO>>`

---

## API-91 GET /api/v1/admin/moderation/tasks/{id}
**功能**: 获取待审内容、投稿人、来源版本、授权信息和检测结果；仅返回 `audit_type=audit` 的审核任务
**路径参数**: `id` — 审核任务ID
**响应 VO**: `Result<AuditVO>`

---

## API-92 POST /api/v1/admin/moderation/tasks/{id}/decisions
**功能**: 提交审核决定；仅允许处理 `pending` 审核任务
**路径参数**: `id` — 审核任务ID
**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `action` | String | **是** | `approve` / `reject` / `rework` |
| `comment` | String | 否 | 审核意见 |
**后端 DTO**: `AuditDTO { audit_type, target_type, target_id, reason, action, comment }`
**响应 VO**: `Result<Void>`

**状态机**: `approve -> content.status=public`；`reject -> content.status=offline`；`rework -> content.status=draft`。处理完成后 `adm_audit.status=processed`。

---

## API-93 PUT /api/v1/admin/community-items/{id}/status
**功能**: 上架/下架/停用社区内容
**路径参数**: `id` — 社区内容ID
**请求体**: status(String) **是** 支持 `published/public`、`unpublished/disabled/offline`、`reviewing`、`draft`
**响应 VO**: `Result<ContentVO>`

**落库规则**: `published/public -> public`；`unpublished/disabled/offline -> offline`；`reviewing` 和 `draft` 保持原值。

---

## API-94 PUT /api/v1/admin/community-items/{id}/recommendation
**功能**: 设置推荐或置顶
**路径参数**: `id` — 社区内容ID
**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `is_top` | int | **是** | 0=取消推荐, 1=推荐 |
| `expires_at` | LocalDateTime | 否 | 到期时间 |
**响应 VO**: `Result<ContentVO>`

---

## API-95 GET /api/v1/admin/reports
**功能**: 分页查询举报
**查询参数**: status(否): `pending`/`processing`/`resolved`, page(否), size(否)
**响应 VO**: `Result<PageResult<AuditVO>>`

---

## API-96 GET /api/v1/admin/reports/{id}
**功能**: 查看举报详情；仅返回 `audit_type=report` 的举报任务
**路径参数**: `id` — 举报ID
**响应 VO**: `Result<AuditVO>`

---

## API-97 POST /api/v1/admin/reports/{id}/resolution
**功能**: 提交举报处理结论；仅允许处理 `pending` 举报任务
**路径参数**: `id` — 举报ID
**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `action` | String | **是** | `approve` / `offline` / `ignore` / `reject` / `restore` |
| `comment` | String | 否 | 处理说明 |
**后端 DTO**: `AuditDTO`
**响应 VO**: `Result<Void>`

**状态机**: `approve/offline -> content.status=offline`；`restore -> content.status=public`；`ignore/reject` 只记录处理结论不改变内容状态。处理完成后 `adm_audit.status=processed`。

---

# 十一、后台 — 导出模板模块

## API-98 GET /api/v1/admin/export-templates
**功能**: 分页查询导出模板（数据源为 Python PPT 服务模板 JSON 文件，`id` 即 Python 侧 `theme`）
**查询参数**: export_type(否), status(否), page(否), size(否)
**响应 VO**: `Result<PageResult<{id, name, export_type, version, status, size, is_default, created_at, updated_at}>>`

> 说明：模板真实存储于 Python 服务（`a12_ppt/templates/*.json`）；`export_type` 固定 `pptx`、`status` 固定 `published`、`version` 固定 `1`；`size` 为模板文件字节数；Python 不提供创建/更新时间（返回 null）。

---

## API-99 POST /api/v1/admin/export-templates
**功能**: 创建导出模板（转发 Python 落盘为 `{theme}.json`，theme 即 `name`）
**请求体 (JSON)**: name(**是**), export_type(**是**，目前仅支持 `pptx`), template_data(**是**，模板 JSON 文件文本内容，顶层对象且必须含 `html_template` 字段), description(否)
**响应 VO**: `Result<{id, version}>`（id 即 theme，version 固定 1）
**错误**: 模板名称重复 / 非法字符、JSON 非法或缺 `html_template` 字段时返回 code=400

---

## API-100 PATCH /api/v1/admin/export-templates/{id}
**功能**: 替换模板内容（转发 Python 覆盖 `{theme}.json`；默认模板「素白风」不可替换）
**路径参数**: `id` — 模板ID（即 theme）
**请求体**: name(忽略), template_data(**是**，新模板 JSON 文件文本内容), description(否)
**响应 VO**: `Result<{id, version}>`

---

## API-101 PUT /api/v1/admin/export-templates/{id}/status
**功能**: 发布或停用模板版本
**路径参数**: `id` — 模板ID
**请求体**: status(String) **是** `published`/`unpublished`
**响应 VO**: `Result<Void>`

---

## DELETE /api/v1/admin/export-templates/{id}
**功能**: 删除导出模板（转发 Python 删除 `{theme}.json`；默认模板「素白风」不可删除）
**路径参数**: `id` — 模板ID（即 theme）
**响应 VO**: `Result<Void>`

---

## GET /api/v1/admin/export-templates/{id}/download
**功能**: 下载模板 JSON 文件（从 Python 拉取字节流，`Content-Type: application/json`，UTF-8 附件文件名 `{theme}.json`）
**路径参数**: `id` — 模板ID（即 theme）
**响应**: 文件字节流；模板不存在时返回 code=400 JSON 错误体

---

# 十二、后台 — AI配置模块

## API-102 GET /api/v1/admin/ai-configs
**功能**: 查询模型、工具和运行参数配置
**查询参数**: config_group(否)
**响应 VO**: `Result<Array<ConfigVO>>`

| ConfigVO 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int | 配置ID |
| `config_group` | String | 分组: `ai_model`/`platform`/`security`/`template`/`sensitive_word` |
| `config_key` | String | 配置键 |
| `config_value` | String | 配置值 |
| `description` | String | 描述 |
| `updated_by` | Integer | 更新人 |
| `updated_at` | LocalDateTime | 更新时间 |

---

## API-103 POST /api/v1/admin/ai-configs
**功能**: 创建AI配置版本
**请求体 (JSON)**: config_group(**是**), config_key(**是**), config_value(**是**), description(否)
**后端 DTO**: `ConfigDTO { config_group, config_key, config_value, description }`
**响应 VO**: `Result<ConfigVO>`

---

## API-121 POST /api/v1/admin/ai-configs/{id}/publish
**功能**: 发布AI配置版本
**路径参数**: `id` — 配置ID
**响应 VO**: `Result<{node_status: Array<{node, status}>>}`

---

## API-122 POST /api/v1/admin/ai-configs/{id}/rollback
**功能**: 回滚到指定历史配置
**路径参数**: `id` — 配置ID
**请求体 (JSON)**: target_version(int **是**), reason(String **是**)
**响应 VO**: `Result<ConfigVO>`

---

# 十三、后台 — 安全策略

## API-123 GET /api/v1/admin/security-policies
**功能**: 获取安全策略及当前生效版本
**响应 VO**: `Result<Array<ConfigVO>>`

---

## API-124 PUT /api/v1/admin/security-policies/{id}
**功能**: 更新安全策略（版本号防并发覆盖）
**路径参数**: `id` — 策略ID
**请求体 (JSON)**: config_value(**是**), version(int **是**)
**后端 DTO**: `ConfigDTO`
**响应 VO**: `Result<ConfigVO>`

---

## API-125 POST /api/v1/admin/security-policies/{id}/publish
**功能**: 发布安全策略
**路径参数**: `id` — 策略ID
**响应 VO**: `Result<{published: boolean}>`

---

# 十四、后台 — 日志与看板

## API-126 GET /api/v1/admin/audit-logs
**功能**: 查询脱敏后的业务审计日志
**查询参数**: user_id(否), log_type(否), module(否), start_time(否), end_time(否), page(默认1), size(默认10)
**后端 DTO**: `LogQueryDTO extends PageQuery { user_id, log_type, module, start_time, end_time }`
**响应 VO**: `Result<PageResult<LogVO>>`

| LogVO 字段 | 类型 | 说明 |
|---|---|---|
| `id` | long | 日志ID |
| `user_id` | Integer | 操作者ID |
| `log_type` | String | 日志类型: `operation`/`download`/`browse`/`audit`/`system` |
| `module` | String | 所属模块 |
| `action` | String | 操作动作 |
| `target_type` | String | 目标类型 |
| `target_id` | Integer | 目标ID |
| `detail` | String(JSON) | 详细信息 |
| `ip` | String | IP地址 |
| `request_id` | String | 请求ID，来自 `X-Request-Id` |
| `method` | String | HTTP方法 |
| `path` | String | 请求路径 |
| `user_agent` | String | User-Agent |
| `status` | String | 处理状态 |
| `error_message` | String | 错误信息 |
| `duration_ms` | Integer | 耗时毫秒 |
| `created_at` | LocalDateTime | 创建时间 |

---

## API-127 GET /api/v1/admin/system-logs
**功能**: 查询脱敏后的系统运行及异常日志
**查询参数**: log_type(否: operation/audit/download/browse), module(否), keyword(否: 模糊匹配 action/detail), start_time(否), end_time(否), page(默认1), size(默认10)
**后端 DTO**: `LogQueryDTO`
**响应 VO**: `Result<PageResult<LogVO>>`
**说明**: 结果按 created_at 倒序；查询结果缓存 20 秒（缓存键包含全部筛选参数）
**所需权限**: `settings:view`

---

## API-128 GET /api/v1/admin/dashboard
**功能**: 查询后台数据看板。后端从用户、资源、AI任务、导出任务、社区内容、审核举报、日志等真实业务表聚合统计，并缓存 60 秒。

**响应 VO**: `Result<Map<String, Object>>`

| 顶层字段 | 类型 | 说明 |
|---|---|---|
| `user_count` | long | 启用且未删除用户数 |
| `resource_count` | long | 可用个人资源 + 可用平台资源总数 |
| `personal_resource_count` | long | 可用个人资源数 |
| `platform_resource_count` | long | 可用平台资源数 |
| `ai_task_count` | long | AI 教学任务总数 |
| `export_task_count` | long | 导出任务总数 |
| `community_content_count` | long | 社区内容总数 |
| `moderation_pending_count` | long | 待处理审核/举报总数 |
| `review_pending_count` | long | 待审核投稿数 |
| `report_pending_count` | long | 待处理举报数 |
| `log_count` | long | 系统日志总数 |
| `today` | Object | 今日新增指标 |
| `trend_7d` | Array<Object> | 近 7 天趋势 |
| `distribution` | Object | 类型/状态分布 |
| `quality` | Object | 成功率和失败数 |
| `recent_activities` | Array<Object> | 最近 10 条操作日志 |
| `generated_at` | String | 看板生成时间 |

**today 字段**:
| 字段 | 类型 | 说明 |
|---|---|---|
| `new_user_count` | long | 今日新增用户 |
| `new_resource_count` | long | 今日新增资源 |
| `new_ai_task_count` | long | 今日新增 AI 任务 |
| `new_export_task_count` | long | 今日新增导出任务 |
| `new_community_content_count` | long | 今日新增社区内容 |
| `new_log_count` | long | 今日新增日志 |

**trend_7d 每项字段**:
| 字段 | 类型 | 说明 |
|---|---|---|
| `date` | String | 日期，格式 `yyyy-MM-dd` |
| `new_users` | long | 当日新增用户 |
| `new_resources` | long | 当日新增资源 |
| `ai_tasks` | long | 当日 AI 任务数 |
| `export_tasks` | long | 当日导出任务数 |
| `community_contents` | long | 当日社区内容数 |
| `logs` | long | 当日日志数 |

**distribution 字段**:
| 字段 | 类型 | 说明 |
|---|---|---|
| `users_by_type` | Object | 按 `teacher/admin/auditor` 等用户类型统计 |
| `resources_by_type` | Object | 按个人资源 `file_type` 和平台资源 `resource_type` 合并统计 |
| `materials_by_ai_index_status` | Object | 个人资源 AI 索引状态分布 |
| `ai_tasks_by_status` | Object | AI 任务状态分布 |
| `export_tasks_by_status` | Object | 导出任务状态分布 |
| `moderation_by_type_status` | Object | 审核/举报按 `audit_type:status` 组合统计 |
| `community_by_status` | Object | 社区内容状态分布 |
| `logs_by_type` | Object | 日志类型分布 |

**quality 字段**:
| 字段 | 类型 | 说明 |
|---|---|---|
| `ai_task_success_rate` | double | AI 任务完成率，百分比，保留两位 |
| `export_success_rate` | double | 导出成功率，百分比，保留两位 |
| `export_failed_count` | long | 导出失败数 |
| `ai_task_failed_count` | long | AI 任务失败数 |
| `avg_export_duration_ms` | long | 有开始/完成时间的导出任务平均耗时 |

**recent_activities 每项字段**:
| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | long | 日志ID |
| `user_id` | Integer | 操作者ID |
| `log_type` | String | 日志类型 |
| `module` | String | 模块 |
| `action` | String | 动作 |
| `target_type` | String | 目标类型 |
| `target_id` | Integer | 目标ID |
| `status` | String | 日志状态 |
| `created_at` | LocalDateTime | 日志创建时间 |

---

## API-129 GET /api/v1/admin/alerts
**功能**: 分页查询告警
**查询参数**: level(否), source(否), status(否), page(默认1), size(默认10)
**响应 VO**: `Result<PageResult<{id, level, source, title, status, created_at, resolved_at}>>`

---

## API-130 GET /api/v1/admin/alerts/{id}
**功能**: 获取告警详情
**路径参数**: `id` — 告警ID
**响应 VO**: `Result<{id, level, source, title, detail, status, acknowledged_by, resolved_by, created_at, acknowledged_at, resolved_at}>`

---

## API-131 POST /api/v1/admin/alerts/{id}/acknowledge
**功能**: 确认告警
**路径参数**: `id` — 告警ID
**响应 VO**: `Result<Void>`

---

## API-132 POST /api/v1/admin/alerts/{id}/resolve
**功能**: 解决告警
**路径参数**: `id` — 告警ID
**请求体**: resolution(String **是**)
**响应 VO**: `Result<Void>`

---

# 附录: 统一响应结构

### Result（通用响应）
```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```
| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | int | 200成功，其他为错误码 |
| `message` | String | 描述信息 |
| `data` | T | 数据体（类型见各API说明） |

### PageResult（分页响应）
```json
{
  "total": 100,
  "page": 1,
  "size": 10,
  "records": [ ... ]
}
```
| 字段 | 类型 | 说明 |
|---|---|---|
| `total` | long | 总记录数 |
| `page` | int | 当前页码 |
| `size` | int | 每页条数 |
| `records` | List<T> | 当前页数据列表 |

---

# 附录: 常见 HTTP 状态码

| 状态码 | 说明 |
|---|---|
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 / Token 无效 |
| 403 | 无权限访问 |
| 404 | 资源不存在 |
| 409 | 版本冲突（乐观锁） |
| 422 | 业务校验不通过 |
| 429 | 请求频率限制 |
| 500 | 服务器内部错误 |

---

# 附录: 全局请求头

| 请求头 | 必填 | 说明 |
|---|---|---|
| `Authorization` | 需认证的接口必填 | `Bearer <token>` |
| `Content-Type` | POST/PATCH/PUT 必填 | `application/json` |
| `Idempotent-Key` | 幂等敏感操作可选 | 防重复提交 |

---

# Java AI 引擎网关（2026-09-12）

浏览器所有 AI 请求统一发送到 Java（开发默认 `http://localhost:8088`），由 Java JWT 过滤器认证后转发 Python。Python 地址仅配置在 Java `a12.python.base-url` 中；Python 默认监听 `127.0.0.1:8001`。分机部署时将 Python 放在私有网络，仅允许 Java 访问，不将 Python 端口或 `/api/v1/python` 配置为公网直通代理。

复用已有 `PythonProxyController`、`PythonPptClient`，新增 Java 前缀 `/api/v1/ai/engine`，旧 Java `/api/v1/python` 入口继续兼容。前端已迁移至新前缀，Vite 删除独立 Python 代理；原有 Java 业务 API 不变。

| 前端使用的 Java API | Python 内部 API / 说明 |
|---|---|
| `POST /api/v1/ai/intent/recognize`、`recognize-audio` | 复用 API-13B/13C，文本/语音意图识别 |
| `/api/v1/ai/sessions/**` | 复用会话、消息和 `messages/stream`，保留 Java 会话、任务落库 |
| `/api/v1/admin/export-templates/**` | 复用已有管理员模板增删改和下载 |
| `GET /api/v1/ai/engine/health` | `GET /api/v1/python/health` |
| `POST /api/v1/ai/engine/audio/asr` | `POST /api/v1/python/audio/asr`，multipart |
| `GET /api/v1/ai/engine/templates` | `GET /api/v1/python/templates` |
| `POST /api/v1/ai/engine/resources/upload` | `POST /api/v1/python/resources/upload`，multipart；常规资源上传仍复用 Java 上传凭证和入库 API |
| `/api/v1/ai/engine/resources/index/**` | 与 Python 同后缀、同 HTTP 方法，包含 sync、bootstrap、metadata、overview、resources、logs、search、删除 |
| `POST /api/v1/ai/engine/outlines/generate`、`outlines/update` | Python 同后缀 JSON 接口 |
| `POST /api/v1/ai/engine/intent/recognize` | 兼容原生 JSON 请求体；业务前端优先使用 API-13B |
| `POST /api/v1/ai/engine/outlines/chat/stream` | Python 同后缀 SSE，保留节点和逐页事件 |
| `/api/v1/ai/engine/outlines/chat/sessions`、`/{sessionId}` | 与 Python 同方法的 GET/POST/PATCH/DELETE；用于原生大纲会话 |
| `GET /api/v1/ai/engine/teacher-style/profile` | Python 同后缀教师画像查询 |
| `POST /api/v1/ai/engine/presentations/generate`、`presentations/modify`、`presentations/slides/modify`、`presentations/html/validate` | Python 同后缀 JSON 接口 |
| `POST /api/v1/ai/engine/presentations/export/pptx` | Python 同后缀二进制导出，保留文件名、类型 |
| `POST /api/v1/ai/engine/lesson-plans/generate`、`interactive-modules/generate` | Python 同后缀 JSON 接口 |
| `POST /api/v1/ai/engine/lesson-plans/export/docx` | Python 同后缀 DOCX 二进制导出 |
| `POST /api/v1/ai/engine/workspace/chat/stream` | 转发到 Python `/api/v1/python/workspace/chat/stream`；支持通用讨论、工作台动作分类和大纲修复，使用 OpenAI 兼容 SSE 增量格式 |

请求须带 `Authorization: Bearer <token>`。原生会话、意图、画像接口的 `user_id` 从 Java 登录态取得，客户端传入其他用户 ID 不生效。JSON 和文件载荷继续参见下方保留的 Python API 章节。SSE 超时 620 秒；上游连接失败或非 2xx 返回 `error` 事件并结束，不伪造生成成功。

注意：这次路由调整不代表完成所有资源级授权。现有原生索引管理/检索接口仍需进一步按资源归属和管理员权限限制，不能仅因经过 JWT 过滤器就宣称具备完整租户隔离。

# 十五、Python PPT 生成服务

> 说明: Python 服务主要承接 AI 大纲生成、整套 PPT 制作、整套课件迭代修改和单页 PPT 修改。返回的 PPT 页面内容均为 HTML 字符串。以下 Python API 保留作为内部协议文档，前端统一使用上方 Java 网关，禁止直连 Python。
> 建议基础路径: `/api/v1/python`
> 当前 A12-PY 已实现接口: 健康检查、语音输入 ASR、资料上传、模板列表、大纲生成、对话式 SSE 大纲生成、对话会话查询、教师画像查询、大纲修改/重生成、整套 PPT 生成、整套课件迭代修改、单页 PPT 修改、HTML 校验、高保真 PPTX 导出、Word 教案生成、DOCX 导出、动画/小游戏 HTML5 互动模块生成。
> 质量策略: 整套 PPT 生成采用 LandPPT 标准高质量链路，包括模板风格基因提取、全局视觉宪法、每页创意 brief、单页 HTML 生成、HTML 清理校验和多轮修复重试。未配置 `OPENAI_API_KEY` 时仅使用本地 fallback 模板，质量不能等同 AI 生成效果。

**调用顺序建议**
1. 先调用 API-134 获取模板列表，前端让用户选择 `templates[n].theme`
2. 如果用户使用语音输入，先调用 API-134A 得到转写文本，再作为对话 `message` 或普通大纲要求提交
3. 如果用户上传 PDF/Word/PPT/图片/视频/音频/TXT，先调用 API-135，保存返回的 `resource_id`
4. 推荐调用 API-137A 进行对话式 SSE 大纲生成；如果前端不需要多轮澄清，也可以调用 API-136 一次性生成
5. 用户修改大纲后可直接传给下一步；如果要让 AI 按新要求重生成/修订大纲，调用 API-137
6. 调用 API-142 生成配套 Word 教案 JSON，前端可预览和编辑；确认后调用 API-143 导出 DOCX
7. 如果用户要求动画/小游戏，调用 API-144 生成 HTML5 互动模块，再作为新增页或某页素材插入课件
8. 然后调用 API-138，把 API-136、API-137 或 API-137A 返回的 `data.outline` 原样放入 `outline`，并传入前端选中的 `theme`
9. 如果用户要整体修改课件，调用 API-139A，把当前整套 `slides` 和修改要求传入
10. 如果用户只要改某一页，调用 API-139，把该页 `html` 放入 `current_html`
11. 用户在线编辑完成后，调用 API-141 导出 PPTX 下载文件，默认 `dom_editable`

**主题 theme 可填值**
`theme` 应从 API-134 返回的模板列表中选择，建议直接使用 `theme` 字段（即模板 JSON 文件名，不含 `.json`）。不传默认使用 `素白风`。

当前模板库包含: `Toy风`、`中国风`、`中式书卷风`、`五彩斑斓的黑`、`吉卜力风`、`商务`、`大气红`、`宣纸风`、`拟态风`、`日落大道`、`星月夜风`、`星月蓝`、`森林绿`、`模糊玻璃`、`清新笔记`、`清新风`、`科技风`、`竹简风`、`简约答辩风`、`素白风`、`终端风`、`莫奈风`、`赛博朋克风`、`速度黄`、`饺子风`。

## API-133 GET /api/v1/python/health

**功能**: Python 服务健康检查，用于前端或 Java 后端确认 AI/PPT 服务是否可用

**后端参数**: 无请求体

**响应 VO**: `Result<PythonHealthVO>`

| PythonHealthVO 字段 | 类型 | 说明 |
|---|---|---|
| `status` | String | 服务状态: `ok` / `degraded` |
| `service` | String | 服务名称，固定建议为 `a12-python-ppt-service` |
| `version` | String | Python 服务版本号 |
| `model_ready` | Boolean | AI 模型或外部模型网关是否可用 |
| `asr_model` | String | 语音转写模型，默认 `whisper-1` |
| `quality_pipeline` | Boolean | 是否启用 LandPPT 高质量生成流水线 |
| `max_html_retries` | int | 单页 HTML 最大修复重试次数 |

---

## API-134A POST /api/v1/python/audio/asr

**功能**: 语音输入 ASR。前端上传教师语音，Python 调用 Whisper 兼容接口转写为文本，前端可把返回文本填入对话框或直接作为 API-137A 的 `message`。

**请求类型**: `multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `file` | File | **是** | 音频文件，建议 `wav/mp3/m4a/webm` |
| `language` | String | 否 | 语音语言，例如 `zh`；不传则模型自动识别 |

**响应 VO**: `Result<AsrVO>`

| AsrVO 字段 | 类型 | 说明 |
|---|---|---|
| `text` | String | 转写文本 |
| `language` | String | 请求指定的语言 |
| `model` | String | ASR 模型，默认 `whisper-1`，可通过 Python `.env` 的 `ASR_MODEL` 调整 |
| `status` | String | `completed/unavailable/failed` |
| `error_message` | String | 失败原因 |
| `filename` | String | 原始文件名 |
| `content_type` | String | MIME 类型 |

**Java 编排说明**: 前端语音对话推荐调用 API-13A，由 Java 调用 `PythonPptClient.transcribeAudio(...)` 完成 ASR 后继续进入 AI 对话；本 Python 接口保留为细粒度能力接口和内部调试接口。

---

## API-134B POST /api/v1/python/intent/recognize

**功能**: Python 细粒度意图识别接口。接收文本输入、历史消息和已知上下文，返回结构化教学意图、缺失字段、澄清问题和置信度；不会创建 Java 会话，也不会生成大纲或 PPT。Java 业务接口 API-13B/API-13C 内部均会调用该接口。

**请求类型**: `application/json`

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `user_id` | String | 否 | 用户ID |
| `session_id` | String | 否 | Python 会话ID；首次不传且提供 `user_id` 时会自动创建 |
| `title` | String | 否 | 会话标题 |
| `message` | String | **是** | 教师自然语言输入 |
| `history` | List<Message> | 否 | 历史消息数组，元素字段为 `role/content` |
| `known_context` | Object(JSON) | 否 | 已知上下文，例如 `title/subject/grade` |
| `resource_ids` | List<String> | 否 | 上传参考资料ID列表；用于意图记录和后续 RAG query 融合，不代表向量库检索范围 |
| `enable_rag` | Boolean | 否 | 是否记录启用 RAG 意图；本接口不执行检索 |
| `enable_web` | Boolean | 否 | 是否记录启用联网意图；本接口不执行联网 |
| `slide_count` | int | 否 | 期望页数，默认 `8` |
| `language` | String | 否 | 输出语言，默认 `zh-CN` |
| `input_type` | String | 否 | `text` 或 `audio`，默认 `text` |

**响应 VO**: `Result<IntentRecognitionVO>`

| IntentRecognitionVO 字段 | 类型 | 说明 |
|---|---|---|
| `intent` | Object(JSON) | 结构化意图 |
| `need_clarification` | Boolean | 是否需要补充关键信息 |
| `missing_fields` | List<String> | 缺失字段，如 `title/grade/subject` |
| `clarification_question` | String | 澄清问题 |
| `confidence` | double | 置信度，范围 `0.1~0.95` |
| `input_type` | String | `text/audio` |
| `model_used` | Boolean | 是否使用大模型抽取 |
| `user_id` | String | 可选，保存会话时返回 |
| `session_id` | String | 可选，Python 长期会话ID |
| `postgres_available` | Boolean | 可选，是否成功接入 PostgreSQL |

**请求示例**
```json
{
  "user_id": "10001",
  "title": "光合作用备课",
  "message": "帮我做一个七年级生物光合作用8页PPT，加入一个课堂小游戏",
  "history": [],
  "known_context": {},
  "resource_ids": ["res_abcd1234"],
  "enable_rag": true,
  "enable_web": false,
  "slide_count": 8,
  "language": "zh-CN",
  "input_type": "text"
}
```

**响应示例**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "intent": {
      "title": "光合作用",
      "subject": "生物",
      "grade": "七年级",
      "requirements": "帮我做一个七年级生物光合作用8页PPT，加入一个课堂小游戏",
      "slide_count": 8,
      "language": "zh-CN",
      "enable_web": false,
      "enable_rag": true,
      "resource_ids": ["res_abcd1234"],
      "user_id": "10001"
    },
    "need_clarification": false,
    "missing_fields": [],
    "clarification_question": "",
    "confidence": 0.86,
    "input_type": "text",
    "model_used": true,
    "user_id": "10001",
    "session_id": "outline_chat_abcd1234",
    "postgres_available": true
  }
}
```

**长期存储说明**: 传入 `user_id` 时，接口会调用 `OutlineSessionStore.load_or_create(...)` 创建/复用会话，把用户输入保存为 `intent_recognition_input` 消息，把识别摘要保存为 `intent_recognition_result` 消息，并将合并后的 `intent` 写回 `a12_outline_chat_session.intent`。

---

## API-134 GET /api/v1/python/templates

**功能**: 获取 Python PPT 服务可用模板列表，前端主题下拉框应使用此接口返回值

**后端参数**: 无请求体

**响应 VO**: `Result<TemplateListVO>`

| TemplateListVO 字段 | 类型 | 说明 |
|---|---|---|
| `total` | int | 模板总数 |
| `default_theme` | String | 默认模板，当前为 `素白风` |
| `templates` | List<TemplateVO> | 模板列表 |

| TemplateVO 字段 | 类型 | 说明 |
|---|---|---|
| `theme` | String | 生成 PPT 时传入的主题值，直接放入 API-138 的 `theme` |
| `template_name` | String | 模板展示名称 |
| `description` | String | 模板描述 |
| `aliases` | List<String> | 可匹配别名 |
| `is_default` | Boolean | 是否默认模板 |
| `filename` | String | 模板文件名 |
| `size` | long | 模板文件字节数 |

**管理后台模板维护端点**（仅由 Java 后端内部调用，管理后台增删替换下载的数据来源）：

| 端点 | 说明 |
|---|---|
| `POST /api/v1/python/templates` | 创建模板，`{name, template_data, description?}`；`template_data` 为模板 JSON 文件文本，顶层对象且必须含 `html_template`；名称重复/非法、JSON 非法返回 `Result(code=400)` |
| `PATCH /api/v1/python/templates/{theme}` | 替换模板内容，覆盖 `{theme}.json`；默认模板「素白风」拒绝替换 |
| `DELETE /api/v1/python/templates/{theme}` | 删除模板；默认模板「素白风」拒绝删除 |
| `GET /api/v1/python/templates/{theme}/file` | 下载模板 JSON 文件（`application/json` + `Content-Disposition` attachment，`filename*=UTF-8''`）；不存在返回 HTTP 404 |

> 模板名称（theme）约束：中文/字母/数字/下划线/连字符，长度 ≤ 50；写入后清除模板列表缓存（lru_cache）。

---

## API-135 POST /api/v1/python/resources/upload

**功能**: 上传生成大纲前的参考资料，支持 PDF、Word、PPT、图片、视频、音频、TXT/Markdown 等文件。接口会保存文件并执行多模态解析，返回 `resource_id` 供大纲生成时使用。

**请求类型**: `multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `file` | File | **是** | 用户上传的 PDF/Word/PPT/图片/视频/音频/TXT 文件 |

**响应 VO**: `Result<ResourceUploadVO>`

| ResourceUploadVO 字段 | 类型 | 说明 |
|---|---|---|
| `resource_id` | String | 资料ID，大纲生成时放入 `resource_ids` |
| `filename` | String | 原始文件名 |
| `content_type` | String | 文件 MIME 类型 |
| `text_length` | int | 抽取出的文本长度 |
| `text_preview` | String | 文本预览 |

---

## API-135-1 POST /api/v1/python/resources/index/sync

**功能**: 从 Java 传入的 MySQL 资源 URL 解析文件并保存到 Python RAG 索引库。接口幂等：`source_type + resource_id` 组成唯一键；如果 `file_url/file_size` 未变化且已经解析完成，则不会重复解析，只更新 metadata。

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `source_type` | String | **是** | `public` 或 `personal` |
| `resource_id` | String | **是** | MySQL 资源 ID，例如 `12` |
| `title` | String | **是** | 资源标题 |
| `file_url` | String | **是** | MySQL 保存的文件 URL |
| `file_type` | String | 否 | `pdf/word/ppt/txt/image/audio/video`；不传或传业务类型时，Python 会根据 `file_url` 后缀兜底识别 |
| `file_size` | long | 否 | 文件大小，用于判断是否变化 |
| `uploaded_by` | String | 否 | 上传人 ID |
| `owner_user_id` | String | 否 | 个人资源所属用户 ID |
| `available` | Boolean | 否 | 是否可用 |
| `allow_ai` | Boolean | 否 | 是否允许 AI 检索 |
| `metadata` | Object | 否 | 学科、年级、标签、权限等扩展元数据 |
| `force_reparse` | Boolean | 否 | 是否强制重新解析 |

**metadata 固定包含**: `source/source_type/resource_id/resource_key/mysql_table/uploaded_by/owner_user_id/available/allow_ai/file_url/file_type/file_size/title`

**多模态解析能力**:
| 类型 | 解析方式 | 输出到 RAG 的内容 |
|---|---|---|
| `pdf` | PyPDF2 文本抽取；无文字层页面用 pypdfium2 渲染后执行 OCR + 视觉理解 | 按页文本、扫描页文字、图表和知识点摘要；单份文件最多处理 20 个扫描页 |
| `word` | python-docx | 段落、表格文本 |
| `ppt` | python-pptx + 视觉模型 | 每页文本、PPT 内嵌图片视觉摘要 |
| `image` | OCR + 视觉模型 | 图片文字、图表/场景/知识点摘要 |
| `video` | OpenCV/ffmpeg 抽关键帧 + 视觉模型 + FFmpeg 音轨提取 + 配置的 ASR | 关键帧画面文字、场景、知识点摘要和视频音轨转写；无 FFmpeg 时明确降级为仅画面分析 |
| `audio` | Whisper 兼容音频转写 | 音频转写文本 |
| `txt` | 文本读取 | 原始文本 |

**解析 metadata 额外包含**: `parse.modality`、`parse.parser`、`parse.normalized_file_type`、`parse.text_length`，PPT/视频还会包含 `slide_count/image_count/keyframe_count/vision_summary_count` 等统计字段。

**响应 VO**: `Result<{resource_key, status, text_length, chunk_count, error_message}>`

---

## API-135-2 POST /api/v1/python/resources/index/bootstrap

**功能**: 批量初始化资源索引库。由 Java 遍历 MySQL 公共资源和 AI 可用个人资源后调用。

**请求体 (JSON)**: `{ "resources": [API-135-1 的资源对象], "force_reparse": false }`

**响应 VO**: `Result<{total, indexed, skipped, failed, results}>`

---

## API-135-3 PATCH /api/v1/python/resources/index/metadata

**功能**: 更新资源索引 metadata，不重新解析文件。用于公共资源停用、个人资源关闭 `allow_ai` 等场景。

**请求体 (JSON)**: `source_type`、`resource_id` 必填，`available`、`allow_ai`、`metadata` 选填。

**响应 VO**: `Result<{resource_key, status, available, allow_ai}>`

---

## API-135-4 DELETE /api/v1/python/resources/index/{source_type}/{resource_id}

**功能**: 删除资源索引及其 chunks。用于个人资源删除、替换旧文件等场景。

**路径参数**: `source_type=public|personal`，`resource_id=MySQL资源ID`

**响应 VO**: `Result<{resource_key, status}>`

---

## API-135-5 GET /api/v1/python/resources/index/overview

**功能**: 查看 RAG 索引总览，用于后台管理和演示验收。

**响应字段**: `postgres_available`、`embedding_dimensions`、`resource_count`、`chunk_count`、`retrieval_log_count`、`groups`、`fallback_path`。

**Java 代理**: `GET /api/v1/python/resources/index/overview`

---

## API-135-6 GET /api/v1/python/resources/index/resources

**功能**: 分页查看已进入 RAG 索引库的资源。

**查询参数**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `source_type` | String | 否 | `public` 或 `personal` |
| `available` | Boolean | 否 | 是否可检索 |
| `limit` | int | 否 | 默认 50，最大 200 |
| `offset` | int | 否 | 默认 0 |
| `parse_status` | String | 否 | `completed` 或 `failed`（2026-09-15 新增，服务端状态过滤） |
| `keyword` | String | 否 | 按 `title` / `resource_id` 模糊匹配（ILIKE，`%_\` 已转义；2026-09-15 新增） |

**响应字段**: `total`、`limit`、`offset`、`items[]`。`items[]` 包含 `resource_key/source_type/resource_id/title/available/allow_ai/parse_status/text_length/chunk_count/metadata/indexed_at/updated_at`。

**Java 代理**: `GET /api/v1/python/resources/index/resources`

---

## API-135-7 GET /api/v1/python/resources/index/resources/{source_type}/{resource_id}

**功能**: 查看单个资源索引详情和前 N 个 chunk。

**查询参数**: `chunk_limit`，默认 20，最大 200。

**Java 代理**: `GET /api/v1/python/resources/index/resources/{sourceType}/{resourceId}`

---

## API-135-8 POST /api/v1/python/resources/index/search

**功能**: 直接测试 RAG 检索。检索流程为：query embedding -> pgvector candidate search -> keyword/metadata hybrid rerank -> context assembly -> retrieval log.

**请求体 (JSON)**
```json
{
  "query": "初中生物 光合作用 实验设计",
  "resource_ids": [],
  "limit": 12000,
  "top_k": 8,
  "source_type": null
}
```

**说明**: `resource_ids` 为空时搜索全部可用知识库资源；传 `public:12` / `personal:8` 时限定搜索范围。`source_type` 为可选域过滤（`public`/`personal`，在 pgvector SQL 追加 `AND source_type = %s`；2026-09-15 新增，管理端知识检索面板使用）。上传参考材料仍只用于 query enrichment，不作为 RAG 范围。

**响应字段**: `query`、`context`、`matches[]`、`search_mode`、`latency_ms`。`matches[]` 包含 `resource_id/chunk_id/content/metadata/base_score/rerank_score/score/rank/match_type`。

**Java 代理**: `POST /api/v1/python/resources/index/search`

---

## API-135-9 GET /api/v1/python/resources/index/logs

**功能**: 查看 Python RAG 检索日志。包括直接 search API 和大纲生成中的 RAG 调用。

**查询参数**: `limit` 默认 50，最大 200；`offset` 默认 0。

**响应字段**: `total`、`limit`、`offset`、`items[]`。`items[]` 包含 `query/resource_ids/match_count/top_score/search_mode/latency_ms/metadata/created_at`。

**Java 代理**: `GET /api/v1/python/resources/index/logs`

---

## API-135-10 GET /api/v1/kb/retrieval-logs

**功能**: 查看 Java/MySQL `kb_retrieval_log` 中的用户检索记录。大纲对话完成且调用 RAG 后，Java 会把 `rag_search` trace 写入该表。

**查询参数**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `type` | String | 否 | 例如 `retrieval` |
| `task_id` | int | 否 | 关联 `ai_task.id` |
| `page` | int | 否 | 默认 1 |
| `size` | int | 否 | 默认 20，最大 100 |

**响应 VO**: `Result<PageResult<Kb_Retrieval_Log>>`

---

## API-135-11 GET /api/v1/kb/retrieval-logs/{id}

**功能**: 查看单条 Java/MySQL 检索日志。只能查看当前登录用户自己的记录。

**响应 VO**: `Result<Kb_Retrieval_Log>`

---

## API-136 POST /api/v1/python/outlines/generate

**功能**: 根据课程信息、教学目标和用户补充要求生成 PPT/教学设计大纲

**最小可用请求**
```json
{
  "title": "光合作用",
  "subject": "生物",
  "grade": "七年级",
  "slide_count": 8
}
```

**完整请求示例**
```json
{
  "session_id": 101,
  "title": "光合作用",
  "subject": "生物",
  "grade": "七年级",
  "duration_minutes": 45,
  "teaching_goals": "理解光合作用的条件、过程和意义，能够解释植物制造有机物的基本过程。",
  "knowledge_points": ["叶绿体", "二氧化碳", "水", "光能", "氧气释放"],
  "requirements": "适合初中课堂，语言通俗，加入课堂提问和总结页。",
  "reference_text": "这里放教材、教案、上传文档解析后的参考文本，可为空。",
  "slide_count": 8,
  "resource_ids": ["res_xxxxxx"],
  "enable_rag": true,
  "enable_web": false,
  "language": "zh-CN"
}
```

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `session_id` | long | 否 | Java 后端已有会话ID，没有就不传 |
| `title` | String | **是** | PPT/课程标题，例如 `光合作用` |
| `subject` | String | **是** | 学科，例如 `语文` / `数学` / `英语` / `生物` |
| `grade` | String | **是** | 年级，例如 `七年级` / `高一` |
| `duration_minutes` | int | 否 | 课程时长，单位分钟，例如 `45` |
| `teaching_goals` | String | 否 | 教学目标，一段自然语言即可 |
| `knowledge_points` | List<String> | 否 | 知识点数组，例如 `["叶绿体", "光能", "氧气释放"]` |
| `requirements` | String | 否 | 用户额外要求，例如 `风格活泼，加入课堂互动` |
| `reference_text` | String | 否 | 教材、资料、上传文件解析后的纯文本；没有资料可不传 |
| `resource_ids` | List<String> | 否 | 上传参考资料ID列表。临时上传资料使用 API-135 返回的 `res_xxx`；用于提取格式、语气、案例、内容，并参与构造 RAG 检索 query，不作为向量库检索范围 |
| `enable_rag` | Boolean | 否 | 是否启用本地知识库 RAG；为 `true` 时，系统会用用户输入、已识别意图和上传参考资料内容构造查询，在全局可用知识库向量库中检索 |
| `enable_web` | Boolean | 否 | 是否启用联网增强开关；当前会传入模型提示词 |
| `slide_count` | int | 否 | 期望页数，建议 `6-15`，默认 `8` |
| `language` | String | 否 | 输出语言，默认 `zh-CN` |
| `regenerate_instruction` | String | 否 | 重生成大纲时的附加要求 |

**后端 DTO**: `OutlineGenerateDTO { session_id, title, subject, grade, duration_minutes, teaching_goals, knowledge_points, requirements, reference_text, resource_ids, enable_rag, enable_web, slide_count, language, regenerate_instruction }`

**响应 VO**: `Result<OutlineGenerateVO>`

| OutlineGenerateVO 字段 | 类型 | 说明 |
|---|---|---|
| `outline_id` | String | Python 服务生成的大纲ID |
| `title` | String | 大纲标题 |
| `summary` | String | 大纲摘要 |
| `slide_count` | int | 建议 PPT 页数 |
| `outline` | Object(JSON) | 结构化大纲内容；在原有 `slides` 基础上额外包含 `teaching_design_chain` 和 `quality_report` |
| `slides` | List<OutlineSlideVO> | 分页大纲 |
| `interactive_assets` | List<Object> | 动画、小游戏或仿真等互动资源设计 |
| `diagram_assets` | List<Object> | 绘图工具生成的 Mermaid 图，如流程图、概念图、时间线 |
| `teaching_design_chain` | Object(JSON) | 教学思维链，供前端独立展示 |
| `quality_report` | Object(JSON) | 大纲质量校验结果 |
| `tool_trace` | List<Object> | 本轮智能体工具调用轨迹，如 RAG、联网搜索、绘图工具 |
| `reflection` | Object(JSON) | 生成后反思结果；若质量检查失败，后端会自动尝试修正一次 |

| teaching_design_chain 字段 | 类型 | 说明 |
|---|---|---|
| `teaching_goals` | List<String> | 教学目标 |
| `learner_analysis` | String | 学情分析 |
| `key_points` | List<String> | 教学重点 |
| `difficult_points` | List<String> | 教学难点 |
| `teaching_sequence` | List<String> | 教学逻辑顺序 |
| `activity_design` | List<String> | 课堂活动设计 |
| `assessment_design` | List<String> | 课堂评价/检测设计 |
| `differentiated_support` | List<String> | 面向基础薄弱与进阶学生的分层支架 |
| `engagement_strategy` | List<String> | 学习行为切换、先学后教和课堂参与策略 |
| `learning_science_strategy` | Object(JSON) | ARCS、BOPPPS、ICAP、认知负荷、样例学习和提取练习的整课落地策略 |
| `homework` | List<String> | 课后作业或迁移任务 |

| quality_report 字段 | 类型 | 说明 |
|---|---|---|
| `passed` | Boolean | 是否通过后端自动质量检查 |
| `checks` | Object(JSON) | 是否包含教学设计链、封面、目录、活动、总结页、前测、分步样例、建构/互动任务、提取迁移、单页密度控制和知识点覆盖等检查项 |
| `expected_slide_count` | int | 期望页数 |
| `actual_slide_count` | int | 实际页数 |
| `missing_knowledge_points` | List<String> | 未在大纲页内容中显式覆盖的知识点 |

| diagram_assets 字段 | 类型 | 说明 |
|---|---|---|
| `asset_id` | String | 图资源ID，例如 `diagram_1` |
| `title` | String | 图标题 |
| `type` | String | 图类型：`flowchart` / `concept_map` / `timeline` / `comparison` |
| `format` | String | 当前为 `mermaid` |
| `mermaid` | String | Mermaid 源码，前端可直接渲染为 SVG |
| `usage` | String | 在 PPT 或前端中的使用建议 |

| reflection 字段 | 类型 | 说明 |
|---|---|---|
| `status` | String | `passed` / `needs_revision` / `skipped` |
| `quality_passed` | Boolean | 大纲质量检查是否通过 |
| `issues` | List<String> | 发现的问题 |
| `fixes` | List<String> | 自动修正指令或修正结果 |
| `retry_count` | int | 自动重试次数，当前最多 1 次 |
| `tool_trace` | List<Object> | 本轮工具调用轨迹 |

| OutlineSlideVO 字段 | 类型 | 说明 |
|---|---|---|
| `slide_no` | int | 页码，从 1 开始 |
| `title` | String | 单页标题 |
| `content_points` | List<String> | 页面核心要点 |
| `teaching_intent` | String | 教学意图 |
| `visual_suggestion` | String | 版式或配图建议 |
| `engagement_hook` | String | 本页吸引注意、制造认知冲突或连接经验的设计 |
| `student_task` | String | 学生需要完成的可观察任务、产出和限时 |
| `teacher_prompt` | String | 教师提问、追问或纠偏提示 |
| `understanding_check` | String | 当场判断是否理解及决定继续/补救的方法 |
| `estimated_minutes` | int | 本页建议课堂用时（分钟） |
| `learning_phase` | String | BOPPPS/学习路径阶段，如 `bridge_in`、`objective`、`pre_assessment`、`participatory_learning`、`worked_example`、`post_assessment`、`summary` |
| `learning_theories` | List<String> | 本页采用的学习科学依据，如 ARCS、ICAP、认知负荷、多媒体信号或提取练习 |
| `student_action_mode` | String | ICAP 参与层级：`passive`、`active`、`constructive`、`interactive` |
| `learner_question` | String | 从学生视角提出的本页核心问题 |
| `cognitive_load` | String | 本页认知负荷等级：`low`、`medium`、`high` |
| `scaffolding` | String | 面向当前学情的提示、步骤卡、半成品样例或分层支持 |
| `feedback_strategy` | String | 学生作答后的即时反馈、错误解释和补救/进阶分流方式 |

---

## API-137 POST /api/v1/python/outlines/update

**功能**: 用户在已有大纲基础上修改或重生成大纲，可附带新要求、资料ID、RAG/联网开关。

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `outline` | Object(JSON) | **是** | 当前大纲对象 |
| `instruction` | String | **是** | 修改/重生成要求 |
| `resource_ids` | List<String> | 否 | 上传参考资料ID列表；用于提取格式、语气、案例、内容，并参与构造 RAG 检索 query |
| `enable_rag` | Boolean | 否 | 是否启用本地知识库 RAG 检索 |
| `enable_web` | Boolean | 否 | 是否开启联网增强开关 |

**响应 VO**: `Result<OutlineGenerateVO>`

---

## API-137A POST /api/v1/python/outlines/chat/stream

**功能**: ChatGPT 式对话生成大纲。后端先解析用户手动输入、历史对话和上传资料内容；如果缺少关键信息，通过 SSE 返回澄清问题；用户回复后带同一个 `session_id` 再次调用，后端会合并原始数据和新回复，构造更贴近用户意图的最终 prompt，再生成结构化大纲并流式返回。

**请求类型**: `application/json`

**响应类型**: `text/event-stream`

**最小请求**
```json
{
  "user_id": "10001",
  "message": "帮我做一个七年级生物光合作用8页PPT，加入课堂互动"
}
```

**完整请求示例**
```json
{
  "user_id": "10001",
  "session_id": "outline_chat_xxxxxx",
  "message": "用户本轮输入或对澄清问题的回复",
  "history": [
    {"role": "user", "content": "帮我做一个光合作用PPT"},
    {"role": "assistant", "content": "请补充年级和学科。"}
  ],
  "known_context": {
    "title": "光合作用",
    "subject": "生物"
  },
  "resource_ids": ["res_xxxxxx"],
  "enable_rag": true,
  "enable_web": false,
  "slide_count": 8,
  "language": "zh-CN"
}
```

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `user_id` | String | **是** | 当前用户ID，用于 PostgreSQL 长期记忆、会话归属和教师画像关联 |
| `session_id` | String | 否 | 对话会话ID；首次不传，后端通过 `session` 事件返回 |
| `message` | String | **是** | 用户本轮自然语言输入，也可以是对后端澄清问题的回复 |
| `history` | List<Message> | 否 | 前端已有对话历史；后端也会维护进程内会话状态 |
| `known_context` | Object(JSON) | 否 | 前端已知或用户已编辑确认的信息，例如 `title`、`subject`、`grade` |
| `resource_ids` | List<String> | 否 | 上传参考资料ID列表。临时上传资料使用 API-135 返回的 `res_xxx`；用于提取格式、语气、案例、内容，并参与构造 RAG 检索 query，不作为向量库检索范围 |
| `enable_rag` | Boolean | 否 | 是否调用本地知识库 RAG 检索工具 |
| `enable_web` | Boolean | 否 | 是否调用联网搜索工具 |
| `slide_count` | int | 否 | 期望页数，默认 `8` |
| `language` | String | 否 | 输出语言，默认 `zh-CN` |

**RAG 范围说明**: `resource_ids` 不是向量库过滤条件。上传资料会先解析为 `reference_context`，用于提取格式、语气、案例和用户特定内容；系统再把用户输入、已识别意图和 `reference_context` 融合成 `enriched_query`，用这个融合查询到本地知识库向量库中检索最匹配资料。RAG 工具返回的 `tool_result.rag` 中包含 `enriched_query`、`search_scope=global_knowledge_base`、`reference_context`、`knowledge_context` 和 `matches`。

**SSE 事件**
| event | data 说明 |
|---|---|
| `session` | 返回 `user_id` 和 `session_id` |
| `stage` | 当前节点进度，如 `parse_input`、`tools`、`build_prompt`、`generate_outline` |
| `question` | 信息不足时返回澄清问题；前端展示给用户并等待下一轮回复 |
| `tool_result` | RAG/联网工具返回摘要 |
| `prompt` | 合并多轮上下文和工具结果后的最终大纲 prompt |
| `progress` | 模型生成期间的保活进度 |
| `outline_delta` | 单页大纲增量，前端可逐页追加显示 |
| `reflection` | 大纲生成后的质量反思、问题列表、修正记录、工具调用轨迹 |
| `final` | 完整 `OutlineGenerateVO`，包含 `outline_id`、`outline`、`slides`、`teaching_design_chain`、`quality_report`、`tool_trace`、`reflection`、`diagram_assets` |
| `error` | 节点异常 |
| `done` | 本轮完成 |

**前端 SSE 读取示例**
```javascript
const resp = await fetch("http://127.0.0.1:8001/api/v1/python/outlines/chat/stream", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    user_id,
    session_id,
    message: userInput,
    resource_ids: resourceIds,
    enable_rag: true,
    enable_web: false,
    slide_count: 8
  })
});

const reader = resp.body.getReader();
const decoder = new TextDecoder("utf-8");
let buffer = "";

while (true) {
  const { value, done } = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, { stream: true });
  const chunks = buffer.split("\n\n");
  buffer = chunks.pop() || "";
  for (const chunk of chunks) {
    const event = chunk.match(/^event: (.+)$/m)?.[1];
    const dataText = chunk.match(/^data: (.+)$/m)?.[1];
    const data = dataText ? JSON.parse(dataText) : {};
    if (event === "question") showQuestion(data.question);
    if (event === "outline_delta") appendOutlineSlide(data.slide);
    if (event === "final") saveOutline(data.outline);
  }
}
```

**后端实现说明**: 对话大纲工作流位于 `a12_ppt/outline_chat`，工具调用位于 `a12_ppt/tools`，当前工具包括 RAG 检索和联网搜索。依赖中已加入 `langgraph`，节点边界按 StateGraph 方式拆分。长期记忆、会话、教师画像使用 PostgreSQL，建表脚本位于 A12-PY 目录的 `postgresql_schema.sql`。

---

## API-137B GET /api/v1/python/outlines/chat/sessions

**功能**: 根据 `user_id` 查询该用户最近的大纲对话会话，用于前端后续继续对话。

**Query 参数**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `user_id` | String | **是** | 用户ID |
| `limit` | int | 否 | 返回数量，默认 `20`，最大 `100` |

**响应 VO**: `Result<OutlineChatSessionListVO>`

| 字段 | 类型 | 说明 |
|---|---|---|
| `user_id` | String | 用户ID |
| `sessions` | List<Object> | 会话列表，包含 `session_id`、`title`、`intent`、`status`、`updated_at` |

---

## API-137B-1 POST /api/v1/python/outlines/chat/sessions

**功能**: 通过 Java 代理创建 Python 大纲对话会话。适合不使用 Java `ai_conversation` 业务表、只需要 Python 历史会话的页面。

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `user_id` | String | **是** | 用户ID |
| `title` | String | 否 | 会话标题 |

**响应 VO**: `Result<OutlineChatSessionVO>` — 包含 `session_id`、`messages`、`intent`、`outline`、`created_at/updated_at` 等字段。

---

## API-137B-2 GET /api/v1/python/outlines/chat/sessions/{session_id}

**功能**: 通过 Java 代理读取 Python 单个会话详情和完整消息历史。前端点击历史会话时调用。

**Query 参数**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `user_id` | String | **是** | 用户ID |

**响应 VO**: `Result<OutlineChatSessionVO>`

| OutlineChatSessionVO 字段 | 类型 | 说明 |
|---|---|---|
| `session_id` | String | Python 会话ID |
| `title` | String | 会话标题 |
| `messages` | List<Object> | 完整历史消息，元素包含 `role/content/metadata/created_at` |
| `intent` | Object(JSON) | 当前合并后的用户意图 |
| `outline` | Object(JSON) | 最近一次生成的大纲 |
| `final_prompt` | String | 最近一次最终 prompt |
| `status` | String | 会话状态 |

---

## API-137B-3 PATCH /api/v1/python/outlines/chat/sessions/{session_id}

**功能**: 通过 Java 代理重命名 Python 会话。

**Query 参数**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `user_id` | String | **是** | 用户ID |

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `title` | String | **是** | 新会话标题 |

**响应 VO**: `Result<OutlineChatSessionVO>`

---

## API-137B-4 DELETE /api/v1/python/outlines/chat/sessions/{session_id}

**功能**: 通过 Java 代理删除 Python 会话及其消息历史。

**Query 参数**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `user_id` | String | **是** | 用户ID |

**响应 VO**: `Result<{user_id, session_id, deleted}>`

---

## API-137C GET /api/v1/python/teacher-style/profile

**功能**: 根据 `user_id` 查询教师长期教学风格画像。

**Query 参数**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `user_id` | String | **是** | 用户ID |

**响应 VO**: `Result<TeacherStyleProfileVO>`

| 字段 | 类型 | 说明 |
|---|---|---|
| `user_id` | String | 用户ID |
| `profile` | Object(JSON) | PostgreSQL 中存储的教师画像；没有则为 `null` |
| `postgres_available` | Boolean | 当前 PostgreSQL 是否可用 |

---

## API-138 POST /api/v1/python/presentations/generate

**功能**: 根据已确认的大纲生成整套 PPT，返回每页 PPT 的 HTML 字符串

**最小可用请求**
```json
{
  "title": "光合作用",
  "outline": {
    "title": "光合作用",
    "slides": [
      {
        "slide_no": 1,
        "title": "光合作用",
        "content_points": ["课程导入", "植物为什么需要阳光", "本节课学习目标"],
        "teaching_intent": "激发兴趣并建立问题情境",
        "visual_suggestion": "封面式大标题，配合重点关键词"
      }
    ]
  },
  "theme": "科技风"
}
```

**实际调用建议**
前端或 Java 后端通常不需要自己拼 `outline`，直接把 API-136 或 API-137 返回的 `data.outline` 原样传入即可:
```json
{
  "session_id": 101,
  "outline_id": "outline_xxxxxx",
  "title": "光合作用",
  "outline": "{这里放 API-136 或 API-137 返回的 data.outline 对象，不是字符串}",
  "theme": "科技风",
  "aspect_ratio": "16:9",
  "language": "zh-CN",
  "asset_policy": "auto"
}
```

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `session_id` | long | 否 | Java 后端已有会话ID，没有就不传 |
| `outline_id` | String | 否 | API-136/API-137 返回的 `data.outline_id` |
| `title` | String | **是** | PPT 标题，通常和大纲标题一致 |
| `outline` | Object(JSON) | **是** | API-136/API-137 返回的 `data.outline` 对象，注意不是 JSON 字符串 |
| `theme` | String | 否 | 模板主题，必须优先使用 API-134 返回的 `templates[n].theme`；不传默认 `素白风` |
| `aspect_ratio` | String | 否 | 页面比例: 当前建议固定填 `16:9` |
| `language` | String | 否 | 输出语言，默认 `zh-CN` |
| `asset_policy` | String | 否 | 素材策略：`auto` / `none` / `placeholder` / `generate`，默认并建议使用 `auto`。`auto` 会根据用户要求、学科和逐页内容自动选择；图片服务不可用时安全降级为占位，不中断课件生成 |

**后端 DTO**: `PresentationGenerateDTO { session_id, outline_id, title, outline, theme, aspect_ratio, language, asset_policy }`

**响应 VO**: `Result<PresentationGenerateVO>`

| PresentationGenerateVO 字段 | 类型 | 说明 |
|---|---|---|
| `presentation_id` | String | Python 服务生成的 PPT ID |
| `title` | String | PPT 标题 |
| `slide_count` | int | 实际生成页数 |
| `slides` | List<PptSlideHtmlVO> | 每页 PPT HTML |
| `html` | String | 可选，整套 PPT 合并后的 HTML 字符串 |
| `metadata.interactive_assets` | List<Object> | 可选，动画/小游戏等额外资源规划；前端导出时应保留在 slides metadata 中 |
| `metadata.requested_asset_policy` | String | 请求的素材策略 |
| `metadata.selected_asset_policy` | String | 自动判断后的整套课件素材策略 |
| `metadata.asset_policy_reason` | String | 自动判断原因，便于前端解释和排查 |
| `metadata.generated_image_count` | int | 实际成功生成并嵌入的图片数量 |

| PptSlideHtmlVO 字段 | 类型 | 说明 |
|---|---|---|
| `slide_no` | int | 页码，从 1 开始 |
| `title` | String | 单页标题 |
| `html` | String | 单页 PPT 的 HTML 字符串 |
| `notes` | String | 可选，讲稿或备注 |
| `interactive_assets` | List<Object> | 可选，本页关联的 HTML5/GIF/MP4 动画或小游戏资源 |
| `metadata` | Object(JSON) | 可选，版式、主题、生成参数等扩展信息 |

---

## API-139 POST /api/v1/python/presentations/slides/modify

**功能**: 根据修改指令重写或局部调整单页 PPT，返回修改后的单页 HTML 字符串

**最小可用请求**
```json
{
  "slide_no": 2,
  "current_html": "<!DOCTYPE html><html lang=\"zh-CN\">...</html>",
  "instruction": "把这一页改成左右对比布局，颜色更活泼一些"
}
```

**完整请求示例**
```json
{
  "presentation_id": "ppt_xxxxxx",
  "slide_no": 2,
  "current_html": "<!DOCTYPE html><html lang=\"zh-CN\">...</html>",
  "instruction": "增加一个课堂提问区，突出重点词“叶绿体”，整体保持科技风。",
  "outline_context": {
    "title": "光合作用",
    "current_slide_title": "光合作用的条件"
  },
  "theme": "科技风",
  "keep_style": true
}
```

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `presentation_id` | String | 否 | API-138 返回的 `data.presentation_id` |
| `slide_no` | int | **是** | 要修改的页码，例如 `2` |
| `current_html` | String | **是** | 当前页 HTML，取 API-138 返回的 `data.slides[n].html` |
| `instruction` | String | **是** | 用户修改要求，例如 `改成时间线布局，并压缩文字` |
| `outline_context` | Object(JSON) | 否 | PPT 或当前页上下文，用于让模型理解整体内容 |
| `theme` | String | 否 | 模板主题，例如 `科技风` |
| `keep_style` | Boolean | 否 | 是否尽量保持原有视觉风格，默认 `true` |

**后端 DTO**: `SlideModifyDTO { presentation_id, slide_no, current_html, instruction, outline_context, theme, keep_style }`

**响应 VO**: `Result<SlideModifyVO>`

| SlideModifyVO 字段 | 类型 | 说明 |
|---|---|---|
| `presentation_id` | String | PPT ID，透传请求值 |
| `slide_no` | int | 被修改页码 |
| `html` | String | 修改后的单页 PPT HTML 字符串 |
| `change_summary` | String | 修改摘要 |
| `metadata` | Object(JSON) | 可选，修改原因、版式信息、模型信息等 |

---

## API-139A POST /api/v1/python/presentations/modify

**功能**: 整套课件级别的迭代修改。用于教师提出“整套统一换风格”“整体减少文字”“增加一页案例”“删除第 3 页”“把活动页提前”“统一所有页字体和配色”等全局或跨页修改要求。Python 会先生成课件级修改计划，再并发修改受影响页面，返回新的整套 slides。

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `presentation_id` | String | 否 | 当前课件 ID |
| `title` | String | 否 | 课件标题，默认 `A12 PPT` |
| `slides` | List<Object> | **是** | 当前整套 PPT slides，每项至少包含 `slide_no/title/html` |
| `instruction` | String | **是** | 整套修改要求，例如 `整体减少文字，统一成素白风，并在第4页后增加一个生活案例页` |
| `outline` | Object(JSON) | 否 | 当前大纲，用于理解页面逻辑和新增页内容 |
| `theme` | String | 否 | 当前主题，建议传 API-134 返回的 `theme` |
| `keep_style` | Boolean | 否 | 是否尽量保持当前风格，默认 `true` |
| `max_modified_slides` | int | 否 | 限制最多重写多少页，适合快速预览；不传则由模型决定 |

**响应 VO**: `Result<PresentationModifyVO>`

| PresentationModifyVO 字段 | 类型 | 说明 |
|---|---|---|
| `presentation_id` | String | 课件 ID |
| `title` | String | 修改后的标题 |
| `slide_count` | int | 修改后页数 |
| `slides` | List<Object> | 修改后的整套 slides，可直接用于前端预览/在线编辑/导出 PPTX |
| `html` | String | 合并后的整套 HTML 播放容器 |
| `change_summary` | String | 整套修改摘要 |
| `operations` | List<Object> | 修改计划，包含 `modify/add/delete/reorder` 操作 |
| `modified_slide_nos` | List<int> | 实际重写 HTML 的页码 |
| `metadata` | Object(JSON) | 模型、主题、风格保持等信息 |

**Java 代理说明**: `PythonPptClient.modifyPresentation(...)` 已提供 JSON 调用方法。

---

## API-140 POST /api/v1/python/presentations/html/validate

**功能**: 校验 PPT HTML 字符串是否满足前端渲染要求

**最小可用请求**
```json
{
  "html": "<!DOCTYPE html><html lang=\"zh-CN\">...</html>"
}
```

**完整请求示例**
```json
{
  "html": "<!DOCTYPE html><html lang=\"zh-CN\">...</html>",
  "strict": false
}
```

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `html` | String | **是** | 待校验的 PPT HTML 字符串，通常取单页 `slides[n].html` |
| `strict` | Boolean | 否 | 是否启用严格校验，默认 `false`；前端一般不传 |

**后端 DTO**: `PptHtmlValidateDTO { html, strict }`

**响应 VO**: `Result<PptHtmlValidateVO>`

| PptHtmlValidateVO 字段 | 类型 | 说明 |
|---|---|---|
| `valid` | Boolean | 是否通过校验 |
| `errors` | List<String> | 错误列表 |
| `warnings` | List<String> | 警告列表 |

---

## API-141 POST /api/v1/python/presentations/export/pptx

**功能**: 将前端最终确认/编辑后的 HTML PPT slides 导出为 PPTX 或 ZIP 文件下载。默认通过 Playwright 渲染 HTML，并复用 LandPPT 的 `dom-to-pptx` 与 PptxGenJS，把浏览器 DOM 坐标、计算样式和图层转换为 PowerPoint 原生对象；PowerPoint 无法准确表达的复杂 CSS 装饰仅做局部栅格化，文字仍覆盖为可编辑文本框。若主转换器不可用，会依次降级为 A12 元素级导出和基础文本版。若 slides 中包含动画、小游戏、HTML5、GIF、MP4 等额外资源，服务会返回 ZIP：PPTX 放在压缩包根目录，额外资源放在 `static/` 目录。

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `title` | String | 否 | PPT 标题，默认 `A12 PPT` |
| `filename` | String | 否 | 下载文件名，例如 `光合作用.pptx` |
| `slides` | List<Object> | **是** | 最终 slides 列表，每项至少包含 `html`，建议包含 `title`；如含 `interactive_assets` 或 `metadata.interactive_assets`，导出会自动打包静态资源 |
| `fidelity` | String | 否 | `dom_editable`、`high_fidelity` 或兼容值 `editable_text`，默认 `dom_editable` |
| `package_static_assets` | Boolean | 否 | 是否打包 `interactive_assets/static_assets`，默认 `true` |

**响应**: 文件流。无额外资源时为 `application/vnd.openxmlformats-officedocument.presentationml.presentation`；有额外资源时为 `application/zip`。Java 代理会透传 Python 返回的 `Content-Type` 和下载文件名。

**导出模式说明**:
| fidelity | 说明 | 优点 | 限制 |
|---|---|---|---|
| `dom_editable` | 浏览器测量 DOM，通过 PptxGenJS 重建文字、基础形状、表格和媒体；复杂装饰局部栅格化 | 默认模式，版式接近 HTML，文字及多数元素可在 PowerPoint 中继续编辑 | 浏览器与 PowerPoint 字体度量可能略有差异；滤镜、复杂渐变等装饰是局部图片 |
| `high_fidelity` | Chromium 渲染 HTML 截图，每页作为整页图片写入 PPTX | 视觉最接近前端 HTML 预览，适合最终交付 | PPTX 内文字不可逐字编辑，动画/小游戏导出为静态首屏 |
| `editable_text` | 兼容旧调用，当前同样优先进入 `dom_editable` 管线 | 旧客户端无需立即修改 | 建议新调用显式使用 `dom_editable` |

**ZIP 结构**
```text
{filename}.zip
├── {filename}.pptx
└── static/
    ├── manifest.json
    ├── animation_1.html
    └── game_1.html
```

**互动资源说明**: MP4 资源有真实文件时会尽量作为视频放入 PPT；HTML5/GIF/小游戏不直接嵌入 PPT，而是在 PPT 中提供相对链接和文字说明，并把资源放入 ZIP 的 `static/` 目录。

**部署说明**: `dom_editable` 和 `high_fidelity` 均依赖 Python 包 `playwright` 与 Chromium 运行时。部署后需执行 `python -m playwright install chromium`。`dom-to-pptx.bundle.js` 已随服务本地部署，导出过程不依赖前端 CDN；许可证与来源说明位于 `a12_ppt/presentation/vendor/`。浏览器不可用时接口会退回基础文本版。

---

## API-142 POST /api/v1/python/lesson-plans/generate

**功能**: 根据已生成/已编辑的大纲和 PPT slides 生成配套 Word 教案 JSON。前端可先展示给教师在线修改，再调用 API-143 导出 `.docx`。

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `title` | String | **是** | 课程/教案标题 |
| `subject` | String | 否 | 学科 |
| `grade` | String | 否 | 年级 |
| `duration_minutes` | int | 否 | 课时分钟数 |
| `teaching_goals` | String | 否 | 教学目标 |
| `outline` | Object(JSON) | 否 | API-136/API-137A 返回的 `outline` |
| `slides` | List<Object> | 否 | API-136/API-137A 返回的 `slides` 或最终 PPT slides 摘要 |
| `requirements` | String | 否 | 对教案的额外要求，例如“增加课堂活动和分层作业” |
| `reference_text` | String | 否 | 参考资料文本或教师补充说明 |
| `language` | String | 否 | 默认 `zh-CN` |

**响应 VO**: `Result<LessonPlanGenerateVO>`

| LessonPlanGenerateVO 字段 | 类型 | 说明 |
|---|---|---|
| `lesson_plan_id` | String | Python 生成的教案 ID |
| `title` | String | 教案标题 |
| `lesson_plan` | Object(JSON) | 可编辑教案结构 |

**lesson_plan 推荐结构**: `title/subject/grade/duration_minutes/teaching_goals/key_points/difficult_points/teaching_methods/teaching_resources/lesson_process/classroom_activities/blackboard_design/homework/assessment/reflection`。

---

## API-143 POST /api/v1/python/lesson-plans/export/docx

**功能**: 将前端确认后的教案 JSON 导出为标准 `.docx` 文件下载。

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `title` | String | 否 | 文件标题，默认 `A12 教案` |
| `filename` | String | 否 | 下载文件名，例如 `光合作用教案.docx` |
| `lesson_plan` | Object(JSON) | **是** | API-142 返回或前端编辑后的教案 JSON |

**响应**: `application/vnd.openxmlformats-officedocument.wordprocessingml.document` 文件流

**Java 代理说明**：`PythonPptClient.generateLessonPlan(...)` 和 `PythonPptClient.exportLessonPlanDocx(...)` 已提供调用方法；Java 可在导出任务中保存返回的二进制文件，前端统一通过 Java 网关下载。

---

## API-144 POST /api/v1/python/interactive-modules/generate

**功能**: 专门生成动画/互动小游戏 HTML5 模块。用于满足“生成知识点相关动画创意、互动小游戏”等要求。返回的 `html` 可作为独立页面预览，也可以插入某一页 PPT HTML 中；导出 PPTX 时高保真模式会保留该模块静态首屏。

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `title` | String | **是** | 模块标题 |
| `topic` | String | **是** | 知识主题，例如 `光合作用过程` |
| `module_type` | String | 否 | `animation` / `quiz_game` / `matching_game` / `timeline_game` / `simulation`，默认 `animation` |
| `subject` | String | 否 | 学科 |
| `grade` | String | 否 | 年级 |
| `knowledge_points` | List<String> | 否 | 需要表现或考察的知识点 |
| `requirements` | String | 否 | 额外要求，例如 `适合小组抢答，带计分和重置按钮` |
| `theme` | String | 否 | 视觉主题，建议与 PPT 模板一致 |
| `embed_mode` | String | 否 | `standalone` 或 `slide_fragment`，默认 `standalone` |
| `language` | String | 否 | 默认 `zh-CN` |

**响应 VO**: `Result<InteractiveModuleVO>`

| InteractiveModuleVO 字段 | 类型 | 说明 |
|---|---|---|
| `module_id` | String | 互动模块 ID |
| `title` | String | 模块标题 |
| `module_type` | String | 模块类型 |
| `topic` | String | 知识主题 |
| `html` | String | 完整 HTML5 模块，含 CSS/JS，可直接预览或嵌入 PPT 页 |
| `embed_mode` | String | 嵌入模式 |
| `usage_suggestions` | List<String> | 课堂使用建议 |
| `metadata` | Object(JSON) | 模型、主题、是否独立页等信息 |

**Java 代理说明**: `PythonPptClient.generateInteractiveModule(...)` 已提供 JSON 调用方法。

---

## API-145 POST /api/v1/python/workspace/chat/stream

**功能**：工作台通用对话、动作分类与大纲修复的内部流式接口。此接口仅供 Java 网关调用，浏览器应调用 `/api/v1/ai/engine/workspace/chat/stream` 并携带 JWT。Python 默认只监听 `127.0.0.1:8001`，且不配置浏览器跨域访问。

**请求类型**：`application/json`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `user_id` | String | **是** | 用户 ID；Java 网关会覆盖客户端传入值，防止伪造身份 |
| `mode` | String | 否 | `chat`、`discussion`、`workbench-intent` 或 `outline-repair`，默认 `chat` |
| `messages` | List<Object> | **是** | 最近对话消息，1 至 60 条；每项包含 `role` 和 `content` |

`chat/discussion` 会结合教师长期风格画像给出简体中文教学建议；本轮明确要求优先于画像。`workbench-intent` 仅返回动作分类 JSON，不直接执行页面修改或导出。`outline-repair` 返回修订后的完整大纲 JSON。

**响应类型**：`text/event-stream`

正常增量：`data: {"choices":[{"delta":{"content":"..."}}]}`；结束标记：`data: [DONE]`；模型不可用或调用失败时返回 `event: error`，不会伪造成功结果。

---

## 五类教学能力的实现说明

1. **教学风格与特定需求**：`teacher-style/profile` 保存稳定偏好，本轮 `known_context.requirements/class_level` 始终具有更高优先级；大纲同时返回 `differentiated_support`。
2. **视频分析**：资源索引同时分析关键帧和音轨，画面走 OCR/视觉理解，音轨经 FFmpeg 提取后走配置的 ASR；两路文本合并进入 RAG。
3. **语音交互**：前端录音统一提交 Java `/api/v1/ai/engine/audio/asr` 或业务接口 `/api/v1/ai/sessions/{id}/audio-messages`，转写后继续意图识别和会话。
4. **移动端**：教师端使用响应式布局；窄屏下四个主功能变为带文字的底部导航，教学助手最近对话通过顶部按钮打开，聊天和录音入口保持可用。
5. **以学生为中心的课件内容**：课件按“真实问题与关联→预测前测→分段新知→带理由的分步样例→学生尝试→即时反馈→提取与迁移”组织，而不是照搬教材目录。每页除参与度字段外，还返回 `learning_phase/learning_theories/student_action_mode/learner_question/cognitive_load/scaffolding/feedback_strategy`；质量报告检查 ARCS 动机、BOPPPS 流程、ICAP 建构/互动、单页认知负荷、样例学习和提取练习是否真正落地。

---

### 前端一套完整调用示例

> 本节保留原始 Python 协议示例供后端联调。实际前端请求须将 `/api/v1/python` 换为 Java `/api/v1/ai/engine` 并携带 JWT；已有会话、意图识别、模板管理业务路由优先复用。

**1. 获取模板列表**
```javascript
const templateResp = await fetch("http://127.0.0.1:8001/api/v1/python/templates")
  .then(res => res.json());

const selectedTheme = templateResp.data.templates.find(t => t.theme === "素白风")?.theme
  || templateResp.data.default_theme;
```

**2. 可选上传资料**
```javascript
const formData = new FormData();
formData.append("file", fileInput.files[0]);

const uploadResp = await fetch("http://127.0.0.1:8001/api/v1/python/resources/upload", {
  method: "POST",
  body: formData
}).then(res => res.json());

const resourceIds = [uploadResp.data.resource_id];
```

**3. 生成大纲**
```javascript
const outlineResp = await fetch("http://127.0.0.1:8001/api/v1/python/outlines/generate", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    title: "光合作用",
    subject: "生物",
    grade: "七年级",
    slide_count: 8,
    teaching_goals: "理解光合作用的条件、过程和意义",
    resource_ids: resourceIds,
    enable_rag: true,
    enable_web: false
  })
}).then(res => res.json());
```

**4. 可选按用户新要求修订大纲**
```javascript
const updatedOutlineResp = await fetch("http://127.0.0.1:8001/api/v1/python/outlines/update", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    outline: outlineResp.data.outline,
    instruction: "第 3 页增加课堂互动，第 7 页增加总结练习",
    resource_ids: resourceIds,
    enable_rag: true,
    enable_web: false
  })
}).then(res => res.json());
```

**5. 用确认后的大纲生成 PPT**
```javascript
const finalOutline = updatedOutlineResp?.data?.outline || outlineResp.data.outline;

const pptResp = await fetch("http://127.0.0.1:8001/api/v1/python/presentations/generate", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    title: finalOutline.title,
    outline_id: outlineResp.data.outline_id,
    outline: finalOutline,
    theme: selectedTheme,
    aspect_ratio: "16:9",
    asset_policy: "auto"
  })
}).then(res => res.json());

const firstSlideHtml = pptResp.data.slides[0].html;
```

**6. 修改某一页**
```javascript
const editResp = await fetch("http://127.0.0.1:8001/api/v1/python/presentations/slides/modify", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    presentation_id: pptResp.data.presentation_id,
    slide_no: 1,
    current_html: pptResp.data.slides[0].html,
    instruction: "把封面标题放大，增加课堂导入问题，整体保持当前模板风格",
    theme: selectedTheme,
    keep_style: true
  })
}).then(res => res.json());
```

**7. 导出 PPTX**
```javascript
const finalSlides = pptResp.data.slides.map(slide =>
  slide.slide_no === editResp.data.slide_no
    ? { ...slide, html: editResp.data.html }
    : slide
);

const pptxBlob = await fetch("http://127.0.0.1:8001/api/v1/python/presentations/export/pptx", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    title: pptResp.data.title,
    filename: "光合作用.pptx",
    slides: finalSlides
  })
}).then(res => res.blob());
```

### Python 服务统一错误码建议

| code | message | 说明 |
|---|---|---|
| 40001 | `invalid_outline_input` | 大纲生成参数不完整或格式错误 |
| 40002 | `invalid_ppt_html` | PPT HTML 字符串格式不合法 |
| 50001 | `outline_generate_failed` | 大纲生成失败 |
| 50002 | `presentation_generate_failed` | PPT 生成失败 |
| 50003 | `slide_modify_failed` | 单页 PPT 修改失败 |
| 50301 | `model_unavailable` | 模型服务不可用或超时 |

## AI 教学能力增强接口

以下接口均应由前端调用 Java 网关（`http://127.0.0.1:8088/api/v1/python/...`），不要在浏览器中直接暴露 Python 服务地址。Java 会绑定当前登录用户，Python 原始接口仍保留用于内部联调和 API 文档展示。

| Java 网关接口 | 方法 | 简体中文说明 |
|---|---|---|
| `/api/v1/python/teacher-style/feedback` | POST | 记录教师对生成结果的采纳、拒绝或人工修改，用于更新教学风格记忆 |
| `/api/v1/python/ai/metrics` | GET | 查询模型调用次数、成功率、平均耗时、令牌用量和降级次数 |
| `/api/v1/python/classroom/events` | POST | 记录课堂正确率、参与度、困惑点等教学效果数据 |
| `/api/v1/python/classroom/insights/{projectId}` | GET | 汇总指定项目的课堂反馈，为下一次课件生成提供依据 |
| `/api/v1/python/audio/tts` | POST | 将课件讲解文本合成为语音，返回音频流 |

大纲与 PPT 生成请求支持 `model_profile=fast|standard|deep` 和 `reasoning_effort=low|medium|high`。这两个字段会实际影响后端模型路由和推理配置，而不是仅作为前端展示。生成结果中的 `generation_status` 会明确标识 `model` 或 `fallback`；RAG 结果包含 `citation_id`、`grounding_confidence` 和 `grounding_status`，用于逐页引用和低置信度提示。

知识库概览返回 `ready_for_rag` 与 `readiness_message`。为空时应先上传资料或执行资源索引同步，系统不会把“可调用检索接口”等同于“已经拥有真实教学语料”。
