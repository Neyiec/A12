# PPT 生成耗时排查

重启 Python 并刷新前端后，再生成一次课件。Python 控制台搜索 `AI耗时`，浏览器控制台选择 Info 并搜索 `PPT耗时`。

日志格式示例（数字为示意值）：

```text
[INFO] timing.py: AI耗时 run_id=run_xxx stage=presentation.total/slide.total/slide.html/html.generate/llm.total/llm.request status=success elapsed_ms=18260 elapsed_s=18.260 index=0 slide_no=1 attempt=1 model=模型名称 reasoning=low
```

`status=start` 表示刚开始，success/failed/cancelled 表示结束。耗时是墙钟时间，包含该阶段内的等待；嵌套阶段和并发页面不能相加作为整套耗时。看 `presentation.total` 获取 Python 总耗时，看 `browser.total` 获取工作台请求开始至保存完成的耗时。前端 `python.completed` 中的 `backend_run_id` 对应 Python 的 `run_id`。

| 阶段 | 含义 | 慢时优先检查 |
| --- | --- | --- |
| graph.* / graphs.generate | 教师画像、意图理解、策略、双图谱、提示词、大纲、反思与长期记忆 | 是否重复识别、重复检索、反思重生成 |
| workspace.editor_import | 浏览器加载编辑器依赖 | Vite 缓存、网络、依赖体积 |
| plan.fetch | Java 读取并核验已确认大纲 | Java 请求、数据库 |
| template.load / teacher_profile.load | 模板与教师画像 | 模板读取、数据库连接 |
| interactive.generate | 互动素材生成 | 是否确有必要等待全部互动完成 |
| references.rag / assets.plan | RAG 与配图策略规划，两者当前并行 | 检索、Embedding、配图规划的模型请求 |
| design.plan | 全套视觉规划 | fast 为本地规则；balanced 合并为一次模型请求；精细模式分三次串行请求 |
| slide.queue | 页面等待并发槽位 | 并发数及服务商限流，排队本身并非模型耗时 |
| image.queue / image.* | 配图排队、缓存、生成轮询、下载、写缓存与编码 | 缓存是否命中，生图是否阻塞 HTML |
| html.generate / html.repair | 每页首次生成与修复 | 页码、attempt、模型、推理强度、重复生成 |
| auth.redis / llm.request / audit.write | Redis 令牌校验、模型请求、运行日志入库 | 区分模型慢与 Redis/数据库慢；模型请求包括 SDK 内部重试 |
| llm.first_token | 流式模型首个正文返回时间 | 长思考、排队、模型服务；不是完整结果耗时 |
| html.validate / slide.embed_assets | 单页校验及学科组件、配图嵌入 | HTML 体积、校验开销 |
| presentation.first_slide | Python 从请求开始到首个页面完成 | 首屏体验，包含前置准备 |
| deck.combine / deck.validate | 整套 HTML 合并与最终检查 | base64 图片导致的页面体积 |
| api.sse.serialize | SSE 结果转 JSON | 大图片与重复 HTML 使响应体膨胀 |
| html-validate / presentation-load / project-save | 浏览器校验、装载、Java 项目保存 | 前端重复校验、网络、分页写库 |

## 建议优先级

1. **模型配置保留。** 本轮按教师要求使用现有默认模型，不新增模型分工，不调整模型选择与推理强度。
2. **保留 AI 直接生成完整 HTML。** 本轮不引入结构化内容生成或固定组件渲染替代路径，继续保留自由版式和可编辑元素。
3. **减少提示词重复。** 每页只传当前页、必要的前后页、压缩的整套摘要及相关 RAG 片段，缓存主题与模板分析。不要去掉教师约束和引用来源。
4. **配图与页面生成解耦。** 现在选中配图的页面先等图片再生成 HTML，且等待图片期间占用页面并发槽位。可先确定图片位置生成页面，再异步替换独立图片元素；最终保存及导出前确认所有素材状态。
5. **按日志调整并发。** 页面已并发，不宜直接改成几十路。先比较排队和单次模型请求耗时，再小幅调整 MAX_SLIDE_CONCURRENCY，观察 429、失败率和总时长。增加并发不保证更快。
6. **约束重试总预算。** MAX_HTML_RETRIES 是业务层修复次数，SDK 还有内部重试。质量预设 fast 且模型档位 fast 时当前不做 HTML 自动修复；其他组合仍可能修复。可采用总期限、退避和只重做失败页，避免两层重试放大等待。
7. **避免整套重复劳动。** 缓存模板规划与已生成页面，以大纲、模板、教师要求、资料版本及访问权限组成缓存键。修改局部只生成受影响页面，失败时从已完成页继续。
8. **减少响应及保存体积。** 若 api.sse.serialize、前端装载或 project-save 慢，检查 base64 图片是否在逐页事件、整套 HTML 和最终结果重复传输。可改用有权限校验的静态资源地址、增量保存和批量写页。

## 本轮实现

- 第3项：逐页模板参考缩至5000字符，保留当前页完整数据、教师约束和相邻页摘要；较长RAG上下文按当前页选取片段。模板风格、全套视觉规划和素材规划可复用缓存。
- 第4、5项：图片与该页HTML同时开始，图片等待不会占用HTML并发槽位。HTML继续使用现有 MAX_SLIDE_CONCURRENCY，图片独立限制为2路。该页返回前完成素材合并，未完成素材不会被当作最终成果保存。
- 第7项：合格原始HTML按教师、模板、模型、推理配置、当前页提示词和资料内容缓存。缓存15分钟、进程内最多16MiB及256项，重启后清空；失败/不合格页面不进入缓存。重复或中断后重新请求可复用已完成页面，输入变化会使相关键失效。每次请求仍验证登录态并重新检索资料、校验资料权限。
- 第8项：流式客户端发送 stream_compact=true，最终事件只传页描述和校验摘要，客户端从本次已收页面重组完整HTML，缺页会报错。非流式及未开启精简传输的客户端保持原格式。字节摘要一致且服务器已校验的HTML免于重复校验请求，修改后恢复校验；其他校验和保存前组件准备限制为3路并发，数据库仍批量写页并保留初始快照。

第1项模型、第2项结构化渲染和第6项重试预算按要求不调整。实际提速幅度需要在同主题、同页数、同素材的课件上对比总时长、首屏时间、失败率和质量；缓存收益主要体现在重复生成及中断后重做，首次新课件仍需调用模型。
