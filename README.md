# A12

API_DOCUMENTATION.md 是接口文档
python的ppt制作是借鉴https://github.com/sligter/LandPPT这个项目完成的，生成的是html格式的
如果后期追求速度，并且需要质量的保证可以看看开源的https://github.com/presenton/presenton（python）或者https://github.com/allweonedev/presentation-ai（ts）这两个项目

## 部署工作流

整体拓扑：前端（5173 教师端 / 8888 管理端）→ Java 业务网关（8088）→ Python AI 服务（8001），中间件为 MySQL、Redis、PostgreSQL（pgvector）与阿里云 OSS。

> 注意：`application.yaml`、`.env` 等配置文件含真实密钥（OSS/SMTP/模型 Key），仅本地使用，不要提交到仓库。

### 1. 环境依赖

| 组件 | 版本要求 | 用途 |
| --- | --- | --- |
| JDK | 17+ | Java 业务网关（Spring Boot 3.4.5） |
| Maven | 3.6+ | Java 构建与启动 |
| Python | 3.12（项目自带 `.venv`） | AI 服务（FastAPI + LangChain/LangGraph） |
| Node.js | ≥ 20.19（Vite 8 要求） | 两个前端与移动端打包 |
| MySQL | 8.x | 业务库 `a12` |
| Redis | 6+ | 缓存/限流/资源索引事件流 |
| PostgreSQL | 15+（需 pgvector 扩展） | 会话记忆/向量索引/风格画像 |
| Android Studio（可选） | — | 打包移动端 App |

### 2. 中间件与数据库初始化

1. **MySQL**：创建数据库 `a12`（连接串见 `application.yaml`，默认 `localhost:3306`，账号 root）。表结构由 JPA `ddl-auto: update` 自动创建；`sql/` 目录提供 mock/种子数据（先删后插、可重复执行）。
2. **PostgreSQL**：同样自动建表，无需手工执行 DDL——Python 服务启动时由 `a12_ppt/database.py` 的 `ensure_ai_schema()` 创建 11 张表（会话/画像/运行日志类），`resources/index_store.py` 单例初始化时再创建 3 张向量索引表并自动安装 pgvector 扩展，合计 14 张（均为 `CREATE TABLE IF NOT EXISTS`，只增不改）；向量维度须与 `EMBEDDING_DIMENSIONS=1024` 一致。`postgresql_schema.sql` 仅作参考（落后于代码，缺 3 张图谱类表）；`community_index_migration.sql` 仅旧版存量库需执行一次；知识库测试数据可用 `sql/mock_knowledge_index_postgres.sql`。
3. **Redis**：默认 `127.0.0.1:6379`，无需初始化。
4. **阿里云 OSS / SMTP**：在 Java 端 `application.yaml` 配置（endpoint、AK/SK、bucket、邮箱账号授权码）。

### 3. 启动 Python AI 服务（:8001）

```powershell
cd backend-python/A12-PY
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env    # 填写模型与连接配置
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

`.env` 关键配置：`OPENAI_*`（主模型）、`EMBEDDING_*`（嵌入模型，1024 维）、`ASR_*`（语音转写，未设置回落 OPENAI_*）、`POSTGRES_DSN`、`JAVA_AUTH_BASE_URL`（Java 网关地址）、`A12_FRONTEND_ORIGINS`（允许的前端来源）、`A12_RESOURCE_REDIS_URL`（与 Java 共用同一 Redis）、`A12_PYTHON_INTERNAL_KEY`（内部密钥，**必须与 Java 端一致**，未配置时后台消费者不启动）。

### 4. 启动 Java 业务网关（:8088）

先确认 `application.yaml`：MySQL/Redis/OSS/SMTP 连接、`a12.python.base-url` 指向 Python 服务（默认 `http://127.0.0.1:8001`）、`a12.python.internal-key` 与 Python 端一致。

```powershell
cd backend-java/A12
mvn spring-boot:run
# 或打包后运行：
mvn package -DskipTests
java -jar target/A12-1.0-SNAPSHOT.jar
```

导出产物落盘 `data/exports`（相对启动目录，`a12.export.local-dir` 可改）。

### 5. 前端（教师端 :5173 / 管理端 :8888）

开发模式：

```powershell
cd frontend && npm install && npm run dev         # 教师端 http://localhost:5173
cd frontend-admin && npm install && npm run dev   # 管理端 http://localhost:8888
```

Vite dev 代理：教师端 `/api` → 8088、`/api/v1/python` → 8001（默认值可用 `VITE_API_PROXY_TARGET` / `VITE_PYTHON_API_PROXY_TARGET` 覆盖）；管理端代理目标由同名环境变量指定。

生产构建：

```powershell
cd frontend
npm run build    # 先在 .env.production 配置 VITE_API_BASE_URL / VITE_PYTHON_API_BASE_URL
```

生产环境用 Nginx 等托管 `dist` 静态资源，并将 `/api` 反代到 Java 网关（8088）、`/api/v1/python` 反代到 Python 服务（8001）；两个服务所在域名均建议启用 HTTPS。管理端（frontend-admin）构建方式相同。

### 6. 移动端 App（可选，Android）

```powershell
cd frontend-app
npm install
npm run sync:android   # 先构建 ../frontend/dist，再同步进 android 原生工程
npm run run:android    # 或 npm run open:android 用 Android Studio 打开
```

App 不走 Vite 代理，以 `VITE_API_BASE` 绝对地址直连网关；`androidScheme: http` + `cleartext: true` 允许真机明文联调（生产建议 HTTPS）。iOS 需在 macOS 上单独生成工程。

### 7. 启动顺序与健康检查

推荐顺序：**MySQL / Redis / PostgreSQL → Python(8001) → Java(8088) → 前端**（Java 启动即依赖 Python 转发与 Redis 事件流）。

验证服务可用：

```powershell
curl http://127.0.0.1:8001/api/v1/python/health   # Python AI 服务
curl http://localhost:8088/actuator/health        # Java 业务网关
```

前端验证：浏览器打开 `http://localhost:5173`（教师端）与 `http://localhost:8888`（管理端），能进入登录页并完成登录即部署成功。

