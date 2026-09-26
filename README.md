# A12

智核是面向教师备课、授课与课后反馈的多模态 AI 教学智能体。系统支持自然语言/语音意图识别、教学资料解析、RAG 检索、大纲与 HTML 课件生成、教师风格记忆、课堂反馈闭环，以及可在 PowerPoint 中继续编辑的 PPTX 导出。

- 接口文档：`API_DOCUMENTATION.md`
- Python 服务说明：`backend-python/A12-PY/README.md`
- 可复现 AI 测试：`backend-python/A12-PY/evals/README.md`
- 最新量化结果：`AI_BENCHMARK_REPORT.md`

PPTX 导出复用 LandPPT 的浏览器 DOM 解析、`dom-to-pptx` 与 PptxGenJS，并对 PowerPoint 无法表达的复杂装饰局部栅格化；文字、图片、基础形状和表格尽量保留为可编辑对象。

## Kafka 事件总线（可选）

Kafka 用于可回放的长期业务事件，Redis 继续负责缓存、限流、任务状态和实时进度。启用后，资料解析/向量化、课堂事件和教师反馈改为异步事件链路；Kafka 关闭或发布失败时，Java 自动回退到原 Java→Python HTTP 调用。

1. 启动 Kafka，并确保 broker 地址可被 Java、Python 同时访问。
2. Java 和 Python 进程都设置 `KAFKA_ENABLED=true`、`KAFKA_BOOTSTRAP_SERVERS=127.0.0.1:9092`。
3. 重新安装 Python 依赖：`pip install -r backend-python/A12-PY/requirements.txt`。

默认主题：`a12.resource.index.requested`、`a12.resource.index.result`、`a12.classroom.events`、`a12.teacher.feedback`、`a12.dead-letter`。生产环境应按 `resource_id/project_id/user_id` 保持分区键顺序，并为 DLQ 配置监控告警。
