# 教学设计方案流式生成接口

## 概述

本接口用于 AI 流式生成完整的教学设计方案（教案），以 Markdown 格式渐进返回内容，前端通过 `markstream-vue` 渲染为富文本。

生成的教学设计方案结构参考"五段式教案"规范，包含：教材分析、学情分析、教学目标、教学重难点、教学过程、课堂小结、作业布置、板书设计、教学反思等完整段落。

---

## 接口信息

| 项目 | 内容 |
|------|------|
| **路径** | `POST /api/v1/python/designs/stream` |
| **协议** | SSE (Server-Sent Events)，通过 HTTP POST + ReadableStream 实现 |
| **Content-Type** | `text/event-stream` |
| **认证** | `Authorization: Bearer <token>` |

---

## 请求体 (Request Body)

```json
{
  "user_id": "string (必填) — 教师用户 ID",
  "session_id": "string (必填) — Java 侧会话 ID，关联资源与上下文",
  "message": "string (必填) — 上下文描述文本，包含学段/学科/年级/教材/课程名称/学情/个性化需求",
  "history": "Array<{role: 'user'|'assistant', content: string}> (可选) — 历史对话记录",
  "resource_ids": "string[] (可选) — 引用的教学资源 ID 列表",
  "enable_rag": "boolean (可选，默认 false) — 是否启用 RAG 检索增强",
  "enable_web": "boolean (可选，默认 false) — 是否启用联网搜索",
  "design_id": "string (可选) — 重新生成时传入已有的设计方案 ID，用于版本追踪"
}
```

### `message` 字段格式说明

前端将教师填写的补充信息拼接为一段连贯的文本，各信息项以中文逗号分隔：

```
<学段><学科><年级><教材>，课程名称：《<课程名称>》，班级学情：<学情等级>，个性化需求：<需求文本>
```

**示例**：
```
初中语文八年级人教版，课程名称：《春》，班级学情：良好，个性化需求：符合新课标教学要求；课件风格为自动匹配
```

重新生成（修改要求）时，`message` 直接携带修改说明文本：
```
希望在第二段加入互动讨论环节；整体难度适当降低；将课时从 1 课时改为 2 课时
```

---

## SSE 事件规范

### 事件一览

| 事件名 | 方向 | 触发时机 | 携带数据 |
|--------|------|---------|---------|
| `session` | S→C | 连接建立后首次推送 | `{ session_id: string }` |
| `stage` | S→C | 处理阶段切换时 | `{ stage: string, message?: string }` |
| `design_text_delta` | S→C | 每次 Markdown 文本增量 | `{ delta: string, index: number }` |
| `final` | S→C | 全部内容生成完毕 | 见下方 `final` 数据结构 |
| `error` | S→C | 发生错误时 | `{ message: string, code?: string }` |
| `done` | S→C | SSE 流正常结束 | 无数据 |

### `stage` 事件 — stage 取值

| stage 值 | 含义 |
|----------|------|
| `parse_input` | 正在解析输入需求 |
| `tools` | 正在检索相关资料（RAG / Web） |
| `build_prompt` | 正在构建生成提示词 |
| `generate_design` | 正在生成教学设计方案 |
| `generate_resource` | 正在生成教学资源 |

### `design_text_delta` 事件（核心）

流式推送 Markdown 文本增量片段。前端累积所有 `delta` 字段拼接为完整 Markdown 文档。

```json
{
  "delta": "## 教材分析\n\n《春》是朱自清先生...",
  "index": 0
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `delta` | `string` | 本次增量文本，为原始 Markdown 片段 |
| `index` | `number` | 增量序号，从 0 开始递增，用于前端检测丢包（可选校验） |

**拼接规则**：`fullMarkdown = delta[0] + delta[1] + ... + delta[N-1]`

### `final` 事件

```json
{
  "title": "《春》教学设计",
  "design_id": "d_abc123",
  "markdown": "# 《春》教案\n\n## 教材分析\n\n...",
  "slide_count": 12,
  "session_id": "s_xyz789"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | `string` | 教学设计方案标题 |
| `design_id` | `string` | 方案唯一标识，用于后续确认/修改操作 |
| `markdown` | `string` | 完整的 Markdown 文档（与累积的 delta 拼接结果一致） |
| `slide_count` | `number` | 预估课件页数，用于资源生成卡片展示 |
| `session_id` | `string` | Python 侧会话 ID（若首次创建） |

---

## Markdown 内容规范

生成的 Markdown 文档应遵循以下结构（参考 `设计.md`）：

```markdown
# 《<课题>》教案

## 教材分析
<段落文本>

## 学情分析
<段落文本>

## 教学目标
1. <目标1>
2. <目标2>
3. <目标3>

## 教学重难点
1. **重点**：<重点描述>
2. **难点**：<难点描述>

## 课时安排
<课时数>

## 教学过程

### 第X课时

#### 一、新课导入
<导入环节描述>
**设计意图**：<意图说明>

#### 二、初读感知，梳理脉络
<环节描述>
**设计意图**：<意图说明>

#### 三、精读品析
<环节描述>
**设计意图**：<意图说明>

#### 四、深读悟情
<环节描述>

## 课堂小结
<小结文本>

## 布置作业
1. <作业1>
2. <作业2>

## 板书设计
<板书内容>

## 教学反思
<反思文本>
```

**关键要求**：
- 每个教学环节末尾必须包含 `**设计意图**：` 段落，说明该环节的教学目的
- 教学过程按课时分组（`### 第X课时`），每课时内含多个教学环节（`#### 一、...`）
- 教学目标以编号列表形式呈现，每条目标明确、可衡量
- 全文使用标准 Markdown 语法，避免自定义 HTML 标签

---

## 前端交互流程

```
┌──────────┐    POST /designs/stream     ┌──────────┐
│  ChatView │ ─────────────────────────> │  Python   │
│ (前端)    │                             │  AI 服务  │
│           │ <─ session ────────────── │           │
│           │ <─ stage: parse_input ─── │           │
│           │ <─ stage: tools ────────── │           │
│           │ <─ stage: build_prompt ─── │           │
│           │ <─ stage: generate_design  │           │
│           │ <─ design_text_delta ───── │ (循环推送) │
│           │ <─ design_text_delta ───── │           │
│           │ <─ ... ───────────────── │           │
│           │ <─ final ──────────────── │           │
│           │ <─ done ───────────────── │           │
└──────────┘                             └──────────┘
```

### 前端状态机

```
info (补充信息卡片)
  │ 教师点击"确认"
  ▼
generating_outline (流式接收 design_text_delta)
  │ 收到 final 事件
  ▼
outline_ready (Markdown 完整展示 + 操作栏：修改/确认大纲)
  │ 教师点击"确认大纲"
  ▼
resource_ready (资源生成卡片)
  │ 教师点击"生成"
  ▼
generating_resource → 跳转工作台
```

---

## 错误处理

### 错误响应格式

```json
{
  "message": "生成失败：请求超时，请重试",
  "code": "TIMEOUT"
}
```

### 常见错误码

| code | 说明 | 前端处理 |
|------|------|---------|
| `INVALID_PARAMS` | 缺少必填参数（如 `session_id`） | `ElMessage.error` 提示 |
| `RATE_LIMITED` | 请求频率超限 | 提示用户稍后重试 |
| `TIMEOUT` | AI 生成超时 | 提示重试 |
| `UPSTREAM_ERROR` | 上游 AI 服务异常 | 提示服务暂时不可用 |
| `SESSION_NOT_FOUND` | 会话 ID 不存在 | 提示返回首页 |

---

## 与旧接口的对比

| 维度 | 旧 `/outlines/chat/stream` | 新 `/designs/stream` |
|------|--------------------------|---------------------|
| 增量事件 | `outline_delta` (slide 对象) | `design_text_delta` (Markdown 文本) |
| 生成内容 | 逐页大纲（slide_no / title / teaching_intent） | 完整教学设计方案（五段式教案 Markdown） |
| 前端渲染 | 自定义卡片 UI（`.outline-card`） | `markstream-vue` 流式 Markdown 渲染 |
| 展示形式 | 结构化卡片（非对话消息） | AI 文本对话消息 |
| stage 标识 | `generate_outline` | `generate_design` |
