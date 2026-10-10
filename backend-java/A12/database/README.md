# 已有数据库升级

新建数据库使用 `a12_schema.sql`。已有数据库不能用初始化脚本覆盖，必须先备份，再补齐相应迁移。

社区与资源库出现缺字段或缺表时，按以下顺序运行（均可重复执行）：

1. `20261009_community_schema_repair.sql`：补齐社区关键词与 AI 审核字段，不重写投稿内容。
2. `20261001_com_like_ranking_migration.sql`：点赞表、点赞/收藏计数、榜单索引及历史互动回填。
3. `20260810_res_metadata_dictionary_migration.sql`：分类/标签字典及已有资源标签回填。
4. `20261010_community_reuse_unique_fix.sql`：修复旧版 `uk_favorite_target` 限制同一教师重复复用的问题。唯一约束只作用于收藏，复用和浏览允许多条记录，不删除既有项目或互动记录。

上传流程为获取签名 → 浏览器 PUT 到 OSS → 确认入库。`NoSuchBucket` 表示需要检查 `application.yaml` 的 `aliyun.oss.bucket-name` 和 `endpoint` 是否对应真实存储桶及其地域。浏览器还需在 OSS 配置允许前端域名的 PUT 跨域请求和 Content-Type 请求头。数据库迁移不能解决 OSS 配置问题。
