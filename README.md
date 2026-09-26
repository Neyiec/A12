# A12

API_DOCUMENTATION.md 是接口文档
python的ppt制作是借鉴https://github.com/sligter/LandPPT这个项目完成的，生成的是html格式的
如果后期追求速度，并且需要质量的保证可以看看开源的https://github.com/presenton/presenton（python）或者https://github.com/allweonedev/presentation-ai（ts）这两个项目

## Redis 与 Kafka（可选增强）

- Redis 用于 PPT/教案生成队列、导出任务队列、SSE 进度流、Embedding/RAG 缓存、限流和并发控制；不可用时保留同步接口降级。
- Kafka 用于资源索引、课堂事件和教师反馈的异步解耦；默认关闭，设置 `KAFKA_ENABLED=true` 后启用，发布失败会回退原 Java→Python HTTP 调用。
- 前端始终只访问 Java 网关（默认 `8088`），Python 服务不直接暴露给浏览器。
