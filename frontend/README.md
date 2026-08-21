# 项目架构：
全局：Vue + Vue-Router
API接口工具：axios （封装成了utils/api）
全局样式：tailwindcss + ElementPlus + @element-plus/icons-vue
全局状态管理：pinia
持久化插件（存储在localStorage）：pinia-plugin-persistedstate
测试工具：msw
markdown文本显示：markstream-vue

## 全流程测试案例

开发模式访问 `http://127.0.0.1:5173/#/main/community?preview=1`，点击精选案例“勾股定理：从测量到证明”的“基于此创作”，在创作工作台修改任意页面内容后点击“导出”。系统会跳转到成果导出中心，并自动执行不可变项目快照、导出预检、异步任务创建、queued → generating → checking → success 状态轮询；无需再次点击“创建任务”。随后可查看质量报告、快照预览和下载链接交付。

该案例不依赖已部署的后端服务。导出类型严格限定为 PPTX、Word 与成果包；静态化互动内容的预检警告须由教师确认后才能创建任务。开发预览会自动使用 mock 教师账号 `teacher_zhang / 123456`，页面右上角的“开发预览 · mock API”标识表示当前数据来自本地 mock 服务。mock 的预览文件用于验证接口和快照链路，正式 Office 二进制转换仍由后端文件生成服务承担。
