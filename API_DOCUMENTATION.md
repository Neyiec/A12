# API 接口文档

> 项目: A12 — 智能备课与教学成果管理平台  
> 基础路径: `/api/v1`  
> 统一响应格式: `Result<T>` (code=200 成功, message 描述, data 实际数据体)  
> 分页响应: `PageResult<T>` (total 总数, page 当前页, size 每页条数, records 列表)

---

# 一、认证模块

## API-01 POST /api/v1/auth/register

**功能**: 注册教师账号（服务端强制设置角色为教师，拒绝客户端指定角色）

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `username` | String | **是** | 登录用户名 |
| `password_hash` | String | **是** | 密码（前端加密后传输） |
| `real_name` | String | **是** | 真实姓名 |
| `phone` | String | **是** | 手机号 |
| `email` | String | **是** | 邮箱 |
| `avatar` | String | 否 | 头像 URL |

**后端 DTO**: 暂无独立 DTO（可复用 `UserDTO` 但不接收 user_type/roles）

**响应 VO**: `Result<UserVO>` — 注册成功返回用户信息

---

## API-02 POST /api/v1/auth/verification-codes

**功能**: 向绑定的手机号或邮箱发送验证码

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `username` | String | **是** | 账号（用于确认绑定手机/邮箱） |
| `scene` | String | **是** | 场景: `register` / `password_reset` |
| `channel` | String | **是** | 发送渠道: `phone` / `email` |

**后端 DTO**: 暂无独立 DTO

**响应 VO**: `Result<Void>` — 仅返回成功/失败状态

---

## API-03 POST /api/v1/auth/verify

**功能**: 校验验证码并将账号状态由待验证→正常

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `username` | String | **是** | 账号 |
| `code` | String | **是** | 验证码 |
| `scene` | String | **是** | 场景: `register` / `password_reset` |

**后端 DTO**: 暂无独立 DTO

**响应 VO**: `Result<Void>`

---

## API-04 POST /api/v1/auth/login

**功能**: 统一验证三类账号（教师/审核员/后台管理员）

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `username` | String | **是** | 账号 |
| `password_hash` | String | **是** | 密码（前端加密后传输） |

**后端 DTO**: `LoginDTO { username, password_hash }`

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
| `created_at` | LocalDateTime | 登录时间 |

## API-05 POST /api/v1/auth/initial-password-change

**功能**: 批量创建账号后首次登录需强制改密

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `username` | String | **是** | 账号 |
| `initial_password` | String | **是** | 初始密码 |
| `new_password_hash` | String | **是** | 新密码（前端加密） |

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
| `new_password_hash` | String | **是** | 新密码 |

**后端 DTO**: 暂无独立 DTO

**响应 VO**: `Result<Void>` — 成功后撤销所有已有会话

---

## API-07 POST /api/v1/users/me/password-change

**功能**: 已登录用户修改当前密码

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `current_password_hash` | String | **是** | 当前密码 |
| `new_password_hash` | String | **是** | 新密码 |

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
| `created_at` | LocalDateTime | 创建时间 |
| `updated_at` | LocalDateTime | 更新时间 |

---

# 三、AI 教学引擎

## API-10 POST /api/v1/ai/sessions

**功能**: 创建备课会话，提交文字、语音、参考资料、Skill和课程信息

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `title` | String | **是** | 会话标题 |
| `subject` | String | **是** | 学科 |
| `grade` | String | **是** | 年级 |
| `messages` | String(JSON) | 否 | 初始对话消息 |
| `uploaded_refs` | String(JSON) | 否 | 参考资料ID列表 |
| `status` | String | 否 | 默认 `active` |

**后端 DTO**: `TaskCreateDTO { title, subject, grade, status, uploaded_refs, plan_json }`

**响应 VO**: `Result<TaskVO>` — 含会话ID

---

## API-11 POST /api/v1/ai/sessions/{id}/messages

**功能**: 对话中补充需求、回答澄清问题或提交反馈

**路径参数**: `id` — 会话ID

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `messages` | String(JSON) | **是** | 消息内容（Array of {role, content}） |

**后端 DTO**: `ConversationDTO { title(选填), status(选填), messages, context_summary(选填) }`

**响应 VO**: `Result<ConversationVO>` — 更新后的会话信息

---

## API-12 GET /api/v1/ai/sessions/{id}/plan

**功能**: 获取当前教学设计大纲及版本

**路径参数**: `id` — 会话ID

**后端参数**: 无请求体

**响应 VO**: `Result<TaskVO>` — 其中的 `plan_json` 和 `plan_confirm_status` 字段包含大纲内容

---

## API-13 POST /api/v1/ai/sessions/{id}/plan-confirmations

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

## API-14 POST /api/v1/ai/sessions/{id}/runs

**功能**: 依据已确认计划创建执行任务

**路径参数**: `id` — 会话ID

**后端参数**: 无请求体

**响应 VO**: `Result<TaskVO>` — 含任务ID，status 转为 `running`

---

## API-15 GET /api/v1/ai/runs/{runId}

**功能**: 查询生成、反思及失败状态

**路径参数**: `runId` — 执行任务ID

**后端参数**: 无请求体

**响应 VO**: `Result<TaskVO>`

---

## API-16 GET /api/v1/ai/runs/{runId}/events

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

## API-17 POST /api/v1/projects

**功能**: 创建个人教学项目或社区派生项目

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `project_name` | String | **是** | 项目名称 |
| `project_type` | String | **是** | 类型: `ppt` / `word` / `h5` / `mixed` |
| `status` | String | 否 | 默认 `draft` |
| `snapshots` | String(JSON) | 否 | 版本快照列表 |
| `edit_history` | String(JSON) | 否 | 编辑历史 |

**后端 DTO**: `ProjectCreateDTO { project_name, project_type, status, snapshots, edit_history }`

**响应 VO**: `Result<ProjectVO>`

---

## API-18 GET /api/v1/projects

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

## API-19 GET /api/v1/projects/{id}

**功能**: 获取项目内容、元数据、当前版本和权限

**路径参数**: `id` — 项目ID

**响应 VO**: `Result<ProjectVO>`

---

## API-20 PATCH /api/v1/projects/{id}

**功能**: 修改项目名称、类型、状态等元数据，使用版本号防并发覆盖

**路径参数**: `id` — 项目ID

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `project_name` | String | 否 | 新名称 |
| `project_type` | String | 否 | 新类型 |
| `status` | String | 否 | 新状态 |
| `current_version` | int | **是** | 当前版本号（乐观锁，防止覆盖） |

**后端 DTO**: `ProjectCreateDTO`

**响应 VO**: `Result<ProjectVO>`

---

## API-21 POST /api/v1/projects/{id}/copies

**功能**: 复制有权访问的项目并创建新的私有项目

**路径参数**: `id` — 源项目ID

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `new_name` | String | 否 | 新项目名称（默认原名称+副本） |

**后端 DTO**: 暂无独立 DTO

**响应 VO**: `Result<ProjectVO>` — 新项目的完整信息

---

## API-22 POST /api/v1/projects/{id}/archive

**功能**: 归档项目，禁止继续编辑

**路径参数**: `id` — 项目ID

**后端参数**: 无请求体

**响应 VO**: `Result<ProjectVO>` — 状态更新为 `archived`

---

## API-23 POST /api/v1/projects/{id}/restore

**功能**: 将归档或可恢复删除状态的项目恢复为可用

**路径参数**: `id` — 项目ID

**后端参数**: 无请求体

**响应 VO**: `Result<ProjectVO>`

---

## API-24 DELETE /api/v1/projects/{id}

**功能**: 校验权限、保留期和关联导出任务后永久删除

**路径参数**: `id` — 项目ID

**后端参数**: 无请求体

**响应 VO**: `Result<Void>`

---

## API-25 POST /api/v1/projects/{id}/ai-revisions

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

## API-26 POST /api/v1/projects/{id}/components

**功能**: 插入文本、图片、音视频、表格、H5或学科工具组件

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

## API-27 PATCH /api/v1/projects/{id}/components/{componentId}

**功能**: 修改组件内容、位置和样式

**路径参数**: `id` — 项目ID, `componentId` — 组件ID

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `page_content` | String(JSON) | 否 | 更新的页面内容 |
| `components` | String(JSON) | 否 | 更新的组件列表 |

**后端 DTO**: `PageDTO`

**响应 VO**: `Result<PageVO>`

---

## API-28 POST /api/v1/projects/{id}/versions

**功能**: 保存不可变项目版本并返回版本编号

**路径参数**: `id` — 项目ID

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `description` | String | 否 | 版本说明 |

**后端 DTO**: 暂无独立 DTO

**响应 VO**: `Result<{version_id: int, version_number: int}>`

---

## API-29 GET /api/v1/projects/{id}/versions

**功能**: 分页查询项目历史版本、创建人、说明和创建时间

**路径参数**: `id` — 项目ID

**查询参数**:
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `page` | int | 否 | 默认1 |
| `size` | int | 否 | 默认10 |

**后端 DTO**: `PageQuery { page, size }`

**响应 VO**: `Result<PageResult<{version_id, version_number, description, created_at}>>`

---

## API-30 GET /api/v1/projects/{id}/versions/{versionId}/diff

**功能**: 将目标版本与指定版本或当前版本进行差异比较

**路径参数**: `id` — 项目ID, `versionId` — 目标版本ID

**查询参数**:
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `compare_version_id` | Integer | 否 | 对比版本ID（不传则比较当前版本） |

**响应 VO**: `Result<{differences: Array, summary: String}>`

---

## API-31 POST /api/v1/projects/{id}/versions/{versionId}/restore

**功能**: 基于历史版本创建新的当前版本，不修改原历史记录

**路径参数**: `id` — 项目ID, `versionId` — 源版本ID

**后端参数**: 无请求体

**响应 VO**: `Result<ProjectVO>` — 恢复后的项目（current_version 递增）

---

# 五、个人资源库

## API-32 POST /api/v1/resources/uploads

**功能**: 创建上传会话并取得短时签名地址

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `file_name` | String | **是** | 文件名（含扩展名） |
| `file_type` | String | **是** | 文件类型: `word`/`pdf`/`ppt`/`txt`/`image`/`audio`/`video` |
| `file_size` | Long | **是** | 文件大小（字节） |
| `replace_target_id` | Integer | 否 | 若替换已有资源，传原资源ID |

**后端 DTO**: `MaterialDTO { file_name, file_type, file_url(后端生成), file_size, ... }`

**响应 VO**: `Result<{upload_id: String, upload_url: String, expires_at: LocalDateTime}>`

---

## API-33 POST /api/v1/resources/uploads/{id}/complete

**功能**: 完成上传并校验文件，替换会话通过后原子更新资源，随后触发解析

**路径参数**: `id` — 上传会话ID

**后端参数**: 无请求体

**响应 VO**: `Result<MaterialVO>` — 完成后的资源元数据

---

## API-34 GET /api/v1/resources

**功能**: 按名称、课程、章节、知识点、标签、类型和时间分页检索资源

**查询参数**:
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `keyword` | String | 否 | 名称关键字 |
| `file_type` | String | 否 | 筛选文件类型 |
| `user_id` | Integer | 否 | 筛选用户（后端自动设为当前用户） |
| `page` | int | 否 | 默认1 |
| `size` | int | 否 | 默认10 |

**后端 DTO**: `MaterialQueryDTO extends PageQuery { user_id, file_type, keyword }`

**响应 VO**: `Result<PageResult<MaterialVO>>`

---

## API-35 GET /api/v1/resources/{id}

**功能**: 获取资源元数据、分类、解析状态和当前权限摘要

**路径参数**: `id` — 资源ID

**响应 VO**: `Result<MaterialVO>`

---

## API-36 PATCH /api/v1/resources/{id}

**功能**: 编辑资源名称、标签、课程、分类或所在目录

**路径参数**: `id` — 资源ID

**请求体 (JSON)** — 以下均为选填
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `file_name` | String | 否 | 新文件名 |
| `description` | String | 否 | 新描述 |
| `categories` | String(JSON) | 否 | 新分类 |
| `tags` | String(JSON) | 否 | 新标签 |

**后端 DTO**: `MaterialDTO`（仅传递更新的字段）

**响应 VO**: `Result<MaterialVO>`

---

## API-37 DELETE /api/v1/resources/{id}

**功能**: 删除资源并触发关联知识索引停用

**路径参数**: `id` — 资源ID

**后端参数**: 无请求体

**响应 VO**: `Result<Void>`

---

## API-38 POST /api/v1/resources/batch-actions

**功能**: 按幂等键批量移动、分类或删除资源

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `idempotent_key` | String | **是** | 幂等键 |
| `action` | String | **是** | 操作: `move` / `categorize` / `delete` |
| `resource_ids` | Array[int] | **是** | 资源ID列表 |
| `target` | String | 否 | 移动/分类的目标值 |

**后端 DTO**: 暂无独立 DTO

**响应 VO**: `Result<{results: Array<{id: int, success: boolean, error: String}>>}`

---

## API-39 GET /api/v1/resources/{id}/permission

**功能**: 获取资源私有/共享状态、共享对象及访问权限

**路径参数**: `id` — 资源ID

**响应 VO**: `Result<{access_type: String, authorized_users: String(JSON), allow_ai: int}>`

---

## API-40 PUT /api/v1/resources/{id}/permission

**功能**: 设置资源私有状态、共享对象及访问权限

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

## API-41 GET /api/v1/resources/{id}/audit-logs

**功能**: 查看权限和元数据修改记录

**路径参数**: `id` — 资源ID

**查询参数**:
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `page` | int | 否 | 默认1 |
| `size` | int | 否 | 默认10 |

**响应 VO**: `Result<PageResult<LogVO>>`

---

## API-42 POST /api/v1/resources/{id}/download-url

**功能**: 校验权限并生成短时下载地址

**路径参数**: `id` — 资源ID
**后端参数**: 无请求体
**响应 VO**: `Result<{download_url: String, expires_at: LocalDateTime}>`

---

# 六、成果导出中心

## API-43 POST /api/v1/projects/{id}/export-prechecks

**功能**: 检查项目快照、素材、字体、兼容性、版权和敏感信息

**路径参数**: `id` — 项目ID
**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `snapshot_version` | Integer | **是** | 绑定的快照版本号 |
| `export_type` | String | **是** | 导出类型: `pptx` / `word` / `package` |
**响应 VO**: `Result<{passed: boolean, warnings: Array, errors: Array}>`

---

## API-44 POST /api/v1/export-tasks

**功能**: 绑定项目快照、模板版本和导出参数，创建异步导出任务

**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `project_id` | int | **是** | 项目ID |
| `snapshot_version` | Integer | **是** | 快照版本 |
| `export_type` | String | **是** | 导出类型: `pptx` / `word` / `package` |
| `config` | String(JSON) | 否 | 导出配置参数 |

**后端 DTO**: `ExportTaskDTO { project_id, snapshot_version, export_type, config }`
**响应 VO**: `Result<ExportTaskVO>`

---

## API-45 GET /api/v1/export-tasks

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

## API-46 GET /api/v1/export-tasks/{id}

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
| `created_at` | LocalDateTime | 创建时间 |
| `completed_at` | LocalDateTime | 完成时间 |

---

## API-47 POST /api/v1/export-tasks/{id}/cancel
**功能**: 取消排队中或生成中的任务
**路径参数**: `id` — 导出任务ID
**响应 VO**: `Result<ExportTaskVO>`

---

## API-48 POST /api/v1/export-tasks/{id}/retry
**功能**: 按原快照和参数重新执行
**路径参数**: `id` — 导出任务ID
**响应 VO**: `Result<ExportTaskVO>`

---

## API-49 GET /api/v1/export-tasks/{id}/quality-report
**功能**: 获取导出质量报告、警告和降级项
**路径参数**: `id` — 导出任务ID
**响应 VO**: `Result<{quality_report: String(JSON)}>`

---

## API-50 GET /api/v1/export-artifacts/{id}
**功能**: 获取成果文件元数据、文件状态、缩略图清单和可预览类型
**路径参数**: `id` — 成果文件ID
**响应 VO**: `Result<ExportTaskVO>`

---

## API-51 POST /api/v1/export-artifacts/{id}/preview-url
**功能**: 生成成果缩略图或预览文件的短时访问地址
**路径参数**: `id` — 成果文件ID
**响应 VO**: `Result<{preview_url: String, expires_at: LocalDateTime}>`

---

## API-52 POST /api/v1/export-artifacts/{id}/download-url
**功能**: 生成成果文件的短时下载链接
**路径参数**: `id` — 成果文件ID
**响应 VO**: `Result<{download_url: String, expires_at: LocalDateTime}>`

---

# 七、社区模块

## API-53 GET /api/v1/community/items
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

## API-54 GET /api/v1/community/items/{id}
**功能**: 获取用途、变量、示例、作者、版本和授权信息
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

## API-55 PUT /api/v1/community/items/{id}/favorite
**功能**: 收藏指定社区内容
**路径参数**: `id` — 内容ID
**响应 VO**: `Result<Void>`

---

## API-56 DELETE /api/v1/community/items/{id}/favorite
**功能**: 取消收藏
**路径参数**: `id` — 内容ID
**响应 VO**: `Result<Void>`

---

## API-57 POST /api/v1/community/items/{id}/view-events
**功能**: 记录浏览事件（按用户和内容幂等更新）
**路径参数**: `id` — 内容ID
**响应 VO**: `Result<Void>`

---

## API-58 GET /api/v1/community/favorites
**功能**: 分页查询当前用户收藏的公开可用内容
**查询参数**: page(默认1), size(默认10)
**响应 VO**: `Result<PageResult<ContentVO>>`

---

## API-59 GET /api/v1/community/recent-views
**功能**: 分页查询当前用户最近浏览记录
**查询参数**: page(默认1), size(默认10)
**响应 VO**: `Result<PageResult<{item: ContentVO, viewed_at: LocalDateTime}>>`

---

## API-60 DELETE /api/v1/community/recent-views/{itemId}
**功能**: 移除指定最近浏览记录
**路径参数**: `itemId` — 内容ID
**响应 VO**: `Result<Void>`

---

## API-61 POST /api/v1/community/items/{id}/reuse
**功能**: 校验内容状态、版本和授权，复制到个人空间并返回派生项目
**路径参数**: `id` — 内容ID
**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `target_version` | Integer | 否 | 复用指定版本（默认最新） |
| `new_project_name` | String | 否 | 派生项目名称 |
**后端 DTO**: `InteractionDTO { action_type, target_type, target_id, target_version, bind_materials }`
**响应 VO**: `Result<ProjectVO>`

---

## API-62 POST /api/v1/community/submissions
**功能**: 创建投稿草稿
**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `content_type` | String | **是** | `skill` / `lesson_case` |
| `title` | String | **是** | 标题 |
| `description` | String | 否 | 描述 |
| `subject` | String | 否 | 学科 |
| `grade` | String | 否 | 年级 |
| `lesson_type` | String | 否 | 课型 |
| `content_data` | String(JSON) | 否 | 内容数据 |
| `input_variables` | String(JSON) | 否 | 输入变量 |
| `example_effect` | String | 否 | 示例效果 |
| `license` | String | **是** | 授权协议 |
**后端 DTO**: `ContentDTO { content_type, title, description, subject, grade, lesson_type, content_data, input_variables, example_effect, license }`
**响应 VO**: `Result<ContentVO>`

---

## API-63 GET /api/v1/community/submissions
**功能**: 分页查询当前教师的投稿及审核状态
**查询参数**: status(否), page(否), size(否)
**后端 DTO**: `ContentQueryDTO extends PageQuery { status }`
**响应 VO**: `Result<PageResult<ContentVO>>`

---

## API-64 GET /api/v1/community/submissions/{id}
**功能**: 获取投稿草稿、版本、审核状态和退回意见
**路径参数**: `id` — 投稿ID
**响应 VO**: `Result<ContentVO>`

---

## API-65 PATCH /api/v1/community/submissions/{id}
**功能**: 修改草稿或退回修改状态的投稿
**路径参数**: `id` — 投稿ID
**请求体**: 与 API-62 相同结构，全选填
**后端 DTO**: `ContentDTO`
**响应 VO**: `Result<ContentVO>`

---

## API-66 POST /api/v1/community/submissions/{id}/versions
**功能**: 保存投稿不可变版本
**路径参数**: `id` — 投稿ID
**请求体**: description(否)
**响应 VO**: `Result<{version_id, version_number}>`

---

## API-67 POST /api/v1/community/submissions/{id}/submit
**功能**: 提交审核（首期MVP由功能开关禁用）
**路径参数**: `id` — 投稿ID
**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `source_declaration` | String | **是** | 来源声明 |
| `notes` | String | 否 | 审核备注 |
**响应 VO**: `Result<Void>`

---

## API-68 POST /api/v1/community/reports
**功能**: 创建举报记录
**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `target_type` | String | **是** | 举报对象类型 |
| `target_id` | int | **是** | 举报对象ID |
| `reason` | String | **是** | 举报原因 |
| `description` | String | 否 | 详细描述 |
**后端 DTO**: `AuditDTO { audit_type, target_type, target_id, reason, action, comment }`
**响应 VO**: `Result<{report_id: int}>`

---

## API-69 GET /api/v1/community/reports
**功能**: 分页查询本人举报及处理状态
**查询参数**: status(否), page(否), size(否)
**响应 VO**: `Result<PageResult<AuditVO>>`

---

## API-70 GET /api/v1/community/reports/{id}
**功能**: 获取举报受理状态及处理结果
**路径参数**: `id` — 举报ID
**响应 VO**: `Result<AuditVO>`

---

# 八、后台 — 用户权限模块

## API-71 GET /api/v1/admin/users
**功能**: 按角色、账号状态和关键词分页查询用户
**查询参数**: keyword(否), user_type(否), is_active(否), page(默认1), size(默认10)
**后端 DTO**: `UserQueryDTO extends PageQuery { keyword, user_type, is_active }`
**响应 VO**: `Result<PageResult<UserVO>>`

---

## API-72 GET /api/v1/admin/users/{id}
**功能**: 获取用户状态、角色、权限摘要及安全状态
**路径参数**: `id` — 用户ID
**响应 VO**: `Result<UserVO>`

---

## API-73 PATCH /api/v1/admin/users/{id}/status
**功能**: 启用、停用或锁定用户账号
**路径参数**: `id` — 用户ID
**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `is_active` | int | **是** | 0=停用, 1=启用, -1=锁定 |
**响应 VO**: `Result<UserVO>`

---

## API-74 POST /api/v1/admin/users
**功能**: 创建单个后台账号
**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `username` | String | **是** | 用户名 |
| `password_hash` | String | **是** | 密码 |
| `real_name` | String | **是** | 真实姓名 |
| `phone` | String | 否 | 手机号 |
| `email` | String | 否 | 邮箱 |
| `user_type` | String | **是** | `admin` |
| `roles` | String(JSON) | **是** | 角色列表 |
**后端 DTO**: `UserDTO { username, password_hash, real_name, phone, email, avatar, user_type, roles, permissions, is_active }`
**响应 VO**: `Result<UserVO>`

---

## API-75 POST /api/v1/admin/users/batch
**功能**: 批量创建后台账号
**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `idempotent_key` | String | **是** | 幂等键 |
| `users` | Array | **是** | 用户列表（每个同API-74结构） |
**响应 VO**: `Result<{results: Array<{username, success, initial_credentials, error}>>}`

---

## API-76 GET /api/v1/admin/roles
**功能**: 查询后台角色、权限集合及审核范围
**响应 VO**: `Result<Array<{role_id, role_name, permissions, audit_scope}>>`

---

## API-77 PUT /api/v1/admin/users/{id}/roles
**功能**: 分配系统管理员或内容审核员角色
**路径参数**: `id` — 用户ID
**请求体 (JSON)**: `roles`(String JSON) **是**
**响应 VO**: `Result<UserVO>`

---

## API-78 PUT /api/v1/admin/roles/{id}/permissions
**功能**: 配置后台功能权限及审核范围
**路径参数**: `id` — 角色ID
**请求体 (JSON)**: `permissions`(String JSON) **是**
**响应 VO**: `Result<Void>`

---

# 九、后台 — 公共资源模块

## API-79 GET /api/v1/admin/public-resources
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
| `created_at` | LocalDateTime | 创建时间 |
| `updated_at` | LocalDateTime | 更新时间 |

---

## API-80 POST /api/v1/admin/public-resources/uploads
**功能**: 创建公共资源上传会话
**请求体 (JSON)**: resource_type(**是**), title(**是**), file_url(**是**), file_size(**是**)
**后端 DTO**: `ResourceDTO { resource_type, title, subject, grade, file_url, template_data, thumbnail, description, status }`
**响应 VO**: `Result<{upload_id, upload_url, expires_at}>`

---

## API-81 POST /api/v1/admin/public-resources/uploads/{id}/complete
**功能**: 完成上传并触发安全检测
**路径参数**: `id` — 上传会话ID
**响应 VO**: `Result<ResourceVO>`

---

## API-82 GET /api/v1/admin/public-resources/{id}
**功能**: 获取公共资源详情
**路径参数**: `id` — 资源ID
**响应 VO**: `Result<ResourceVO>`

---

## API-83 PATCH /api/v1/admin/public-resources/{id}
**功能**: 更新公共资源元数据
**路径参数**: `id` — 资源ID
**请求体**: title(否), subject(否), grade(否), description(否)
**后端 DTO**: `ResourceDTO`
**响应 VO**: `Result<ResourceVO>`

---

## API-84 PUT /api/v1/admin/public-resources/{id}/status
**功能**: 启用/停用公共资源
**路径参数**: `id` — 资源ID
**请求体**: status(int) **是** 0=停用 1=启用
**响应 VO**: `Result<ResourceVO>`

---

## API-85 GET /api/v1/admin/public-resources/{id}/processing-status
**功能**: 查询处理状态
**路径参数**: `id` — 资源ID
**响应 VO**: `Result<{security_check, parse_status, index_status, error_msg}>`

---

# 十、后台 — 内容审核与举报处理

## API-86 GET /api/v1/admin/moderation/tasks
**功能**: 按状态、对象类型和审核员查询审核任务
**查询参数**: status(否), target_type(否), handler_id(否), page(默认1), size(默认10)
**响应 VO**: `Result<PageResult<AuditVO>>`

---

## API-87 GET /api/v1/admin/moderation/tasks/{id}
**功能**: 获取待审内容、投稿人、来源版本、授权信息和检测结果
**路径参数**: `id` — 审核任务ID
**响应 VO**: `Result<AuditVO>`

---

## API-88 POST /api/v1/admin/moderation/tasks/{id}/decisions
**功能**: 提交审核决定
**路径参数**: `id` — 审核任务ID
**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `action` | String | **是** | `approve` / `reject` / `rework` |
| `comment` | String | 否 | 审核意见 |
**后端 DTO**: `AuditDTO { audit_type, target_type, target_id, reason, action, comment }`
**响应 VO**: `Result<Void>`

---

## API-89 PUT /api/v1/admin/community-items/{id}/status
**功能**: 上架/下架/停用社区内容
**路径参数**: `id` — 社区内容ID
**请求体**: status(String) **是** `published`/`unpublished`/`disabled`
**响应 VO**: `Result<ContentVO>`

---

## API-90 PUT /api/v1/admin/community-items/{id}/recommendation
**功能**: 设置推荐或置顶
**路径参数**: `id` — 社区内容ID
**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `is_top` | int | **是** | 0=取消, 1=推荐, 2=置顶 |
| `expires_at` | LocalDateTime | 否 | 到期时间 |
**响应 VO**: `Result<ContentVO>`

---

## API-91 GET /api/v1/admin/reports
**功能**: 分页查询举报
**查询参数**: status(否): `pending`/`processing`/`resolved`, page(否), size(否)
**响应 VO**: `Result<PageResult<AuditVO>>`

---

## API-92 GET /api/v1/admin/reports/{id}
**功能**: 查看举报详情
**路径参数**: `id` — 举报ID
**响应 VO**: `Result<AuditVO>`

---

## API-93 POST /api/v1/admin/reports/{id}/resolution
**功能**: 提交举报处理结论
**路径参数**: `id` — 举报ID
**请求体 (JSON)**
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `action` | String | **是** | `dismiss`/`warn`/`remove`/`ban` |
| `comment` | String | 否 | 处理说明 |
**后端 DTO**: `AuditDTO`
**响应 VO**: `Result<Void>`

---

# 十一、后台 — 导出模板模块

## API-94 GET /api/v1/admin/export-templates
**功能**: 分页查询导出模板
**查询参数**: export_type(否), status(否), page(否), size(否)
**响应 VO**: `Result<PageResult<{id, name, export_type, version, status, created_at, updated_at}>>`

---

## API-95 POST /api/v1/admin/export-templates
**功能**: 创建导出模板及首个版本
**请求体 (JSON)**: name(**是**), export_type(**是**), template_data(**是**), description(否)
**响应 VO**: `Result<{id, version}>`

---

## API-96 PATCH /api/v1/admin/export-templates/{id}
**功能**: 更新模板元数据或创建新版本
**路径参数**: `id` — 模板ID
**请求体**: name(否), template_data(否), description(否)
**响应 VO**: `Result<{id, version}>`

---

## API-97 PUT /api/v1/admin/export-templates/{id}/status
**功能**: 发布或停用模板版本
**路径参数**: `id` — 模板ID
**请求体**: status(String) **是** `published`/`unpublished`
**响应 VO**: `Result<Void>`

---

# 十二、后台 — AI配置模块

## API-98 GET /api/v1/admin/ai-configs
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

## API-99 POST /api/v1/admin/ai-configs
**功能**: 创建AI配置版本
**请求体 (JSON)**: config_group(**是**), config_key(**是**), config_value(**是**), description(否)
**后端 DTO**: `ConfigDTO { config_group, config_key, config_value, description }`
**响应 VO**: `Result<ConfigVO>`

---

## API-100 POST /api/v1/admin/ai-configs/{id}/publish
**功能**: 发布AI配置版本
**路径参数**: `id` — 配置ID
**响应 VO**: `Result<{node_status: Array<{node, status}>>}`

---

## API-101 POST /api/v1/admin/ai-configs/{id}/rollback
**功能**: 回滚到指定历史配置
**路径参数**: `id` — 配置ID
**请求体 (JSON)**: target_version(int **是**), reason(String **是**)
**响应 VO**: `Result<ConfigVO>`

---

# 十三、后台 — 安全策略

## API-102 GET /api/v1/admin/security-policies
**功能**: 获取安全策略及当前生效版本
**响应 VO**: `Result<Array<ConfigVO>>`

---

## API-103 PUT /api/v1/admin/security-policies/{id}
**功能**: 更新安全策略（版本号防并发覆盖）
**路径参数**: `id` — 策略ID
**请求体 (JSON)**: config_value(**是**), version(int **是**)
**后端 DTO**: `ConfigDTO`
**响应 VO**: `Result<ConfigVO>`

---

## API-104 POST /api/v1/admin/security-policies/{id}/publish
**功能**: 发布安全策略
**路径参数**: `id` — 策略ID
**响应 VO**: `Result<{published: boolean}>`

---

# 十四、后台 — 日志与看板

## API-105 GET /api/v1/admin/audit-logs
**功能**: 查询脱敏后的业务审计日志
**查询参数**: user_id(否), log_type(否), module(否), start_time(否), end_time(否), page(默认1), size(默认10)
**后端 DTO**: `LogQueryDTO extends PageQuery { user_id, log_type, module, start_time, end_time }`
**响应 VO**: `Result<PageResult<LogVO>>`

| LogVO 字段 | 类型 | 说明 |
|---|---|---|
| `id` | long | 日志ID |
| `user_id` | Integer | 操作者ID |
| `log_type` | String | 日志类型: `operation`/`download`/`browse`/`audit` |
| `module` | String | 所属模块 |
| `action` | String | 操作动作 |
| `target_type` | String | 目标类型 |
| `target_id` | Integer | 目标ID |
| `detail` | String(JSON) | 详细信息 |
| `ip` | String | IP地址 |
| `created_at` | LocalDateTime | 创建时间 |

---

## API-106 GET /api/v1/admin/system-logs
**功能**: 查询脱敏后的系统运行及异常日志
**查询参数**: log_type(否), module(否), start_time(否), end_time(否), page(默认1), size(默认10)
**后端 DTO**: `LogQueryDTO`
**响应 VO**: `Result<PageResult<LogVO>>`

---

## API-107 GET /api/v1/admin/dashboard
**功能**: 查询业务指标
**响应 VO**: `Result<{user_count, resource_count, ai_task_count, export_task_count, moderation_pending_count}>`

---

## API-108 GET /api/v1/admin/alerts
**功能**: 分页查询告警
**查询参数**: level(否), source(否), status(否), page(默认1), size(默认10)
**响应 VO**: `Result<PageResult<{id, level, source, title, status, created_at, resolved_at}>>`

---

## API-109 GET /api/v1/admin/alerts/{id}
**功能**: 获取告警详情
**路径参数**: `id` — 告警ID
**响应 VO**: `Result<{id, level, source, title, detail, status, acknowledged_by, resolved_by, created_at, acknowledged_at, resolved_at}>`

---

## API-110 POST /api/v1/admin/alerts/{id}/acknowledge
**功能**: 确认告警
**路径参数**: `id` — 告警ID
**响应 VO**: `Result<Void>`

---

## API-111 POST /api/v1/admin/alerts/{id}/resolve
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
