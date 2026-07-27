## 项目架构

全局：Vue + Vue-Router
API接口工具：axios （封装成了utils/api）
全局样式：tailwindcss + ElementPlus + @element-plus/icons-vue
全局状态管理：pinia
持久化插件（存储在localStorage）：pinia-plugin-persistedstate
本项目的设计规范资产位于：./design.md

## 常用命令

```bash
npm run dev # 调试运行软件
npm run build # 进行打包
```

## 编码约定

### 通用

#### 注释相关

- 代码中的函数名、变量名保持英文，但每个函数必须用中文编写文档注释（Docstring），复杂的函数内部逻辑也必须用中文添加行内注释。
- 领域类上加字段及其解释
- 每个文件与其他文件的数据交互在文件开头进行注释，增加代码可读性。例子：[数据交互说明] - 导出:   - `UserService`: 用户业务处理类 - 依赖:   - `../models/user.py`: 导入 `UserModel` 数据结构  - `../utils/logger.py`: 导入 `log_error` 方法 - 输入: 接收来自 `auth_middleware` 的 `user_token` (str) - 输出: 返回 `UserProfile` 字典对象给 `user_controller.py`

#### 解耦相关

- 一个函数不能超过30行（不含注释和空行）。如果逻辑复杂，请主动将其拆分为多个具有单一职责的子函数。
- 多个文件中出现重复的函数时，必须提取到统一的工具类、公共模块或组件中复用，严禁复制粘贴。要根据类的作用放到具体的包中，工具放到工具包，组件放到组件包，服务放到服务包。
- **禁止硬编码**：所有常量、配置、文本标签等必须封装到配置模块中统一管理。

### 错误处理

- API 路由使用统一的错误响应格式：`{ error: string, code: int, data: T}`，data是泛型类
- 必须使用统一的输出日志，禁止直接使用 print。日志格式统一为：`[%(levelname)s] %(filename)s: %(message)s`，级别为 info / error / warning。

## 开发注意事项

- 不允许改动本文档