# MCP 接入文档 — 智核（zh）前端项目

> **接入方式**：通过 [CC-Switch](https://github.com/farion1231/cc-switch) 统一管理 MCP Server，无需手动编辑 JSON 配置文件。

---

## 目录

1. [什么是 MCP](#1-什么是-mcp)
2. [CC-Switch 简介](#2-cc-switch-简介)
3. [TailwindCSS MCP 接入方案](#3-tailwindcss-mcp-接入方案)
4. [ElementPlus MCP 替代方案](#4-elementplus-mcp-替代方案)
5. [通过 CC-Switch 安装 MCP](#5-通过-cc-switch-安装-mcp)
6. [验证与使用](#6-验证与使用)
7. [常见问题](#7-常见问题)

---

## 1. 什么是 MCP

**MCP（Model Context Protocol）** 是由 Anthropic 提出的开放协议，用于 AI 助手与外部工具/数据源之间的标准化通信。通过 MCP Server，Claude 等 LLM 可以在对话过程中实时查询组件文档、校验代码、获取设计 Token 等，显著提升前端开发的准确性。

在本项目（TailwindCSS v4 + ElementPlus v2 + Vue 3）中，接入 MCP 可以达到以下效果：

| 能力 | 说明 |
|------|------|
| Tailwind 类名智能提示 | AI 根据需求描述推荐正确的 Tailwind 工具类 |
| Tailwind 类名校验 | 检查代码中的类名是否有效，防止拼写错误 |
| 主题配置查询 | AI 能读取项目的 Tailwind `@theme` 配置，生成符合设计规范的代码 |
| ElementPlus 组件文档查询 | AI 实时查阅 ElementPlus API 文档，生成正确的 Props/Slots/Events |

---

## 2. CC-Switch 简介

**[CC-Switch](https://github.com/farion1231/cc-switch)** 是一个跨平台（Windows/macOS/Linux）的 AI CLI 一体化管理工具，通过图形界面或命令行统一管理 Claude Code、Codex、Gemini CLI 等工具的配置，**无需手动编辑 JSON 文件**。

与本项目相关的核心功能：

| 功能 | 说明 |
|------|------|
| **MCP Server 管理** | 可视化面板添加/编辑/删除 MCP Server，支持 stdio / http / sse 三种传输类型 |
| **内置模板** | 提供常用 MCP Server 模板（如 fetch、context7、sequential-thinking 等） |
| **一键同步** | MCP 配置自动同步到 Claude Code 的 `settings.json`，无需手动操作 |
| **Skills 管理** | 浏览 GitHub 仓库，一键安装/卸载 Skills |
| **提供商切换** | 50+ 内置 API 提供商预设，一键切换模型供应商 |
| **用量统计** | Token 消耗追踪、费用监控 |

### 安装 CC-Switch

```bash
# macOS
brew install --cask cc-switch

# Windows
# 下载 .msi 或 Portable 版本：https://github.com/farion1231/cc-switch/releases
winget install cc-switch

# Linux
# 下载 .deb 或 .AppImage：https://github.com/farion1231/cc-switch/releases
```

> CLI 用户也可使用 CLI 版本：`npm install -g cc-switch-cli`（[GitHub](https://github.com/SaladDay/cc-switch-cli)）

---

## 3. TailwindCSS MCP 接入方案

### 3.1 方案对比

社区目前有多个 TailwindCSS MCP Server，对比如下：

| MCP Server | 包名 | 语言 | 核心能力 | 推荐度 |
|------------|------|------|---------|--------|
| **tailwindcss-mcp** | `tailwindcss-mcp` | Node.js | 类名推荐、校验、主题查询 | ⭐⭐⭐⭐⭐ |
| **tailwind-mcp** | `dougjaworski/tailwind-mcp` | Python | 全文搜索官方文档、变体/示例查询 | ⭐⭐⭐⭐ |
| **@colorsandfonts/mcp** | `@colorsandfonts/mcp` | Node.js | 调色板生成、WCAG 对比度检查 | ⭐⭐⭐ |
| **mcp-vibe-ui** | `mcp-vibe-ui` | Node.js | 设计 Token 资源、15 种预置主题 | ⭐⭐⭐ |

### 3.2 首选方案：tailwindcss-mcp

**核心工具**：

| 工具名 | 功能 | 使用场景 |
|--------|------|---------|
| `suggest_classes` | 根据自然语言描述推荐 Tailwind 类名 | "我想要一个蓝色圆角按钮带阴影" → `bg-blue-600 rounded-lg shadow-md` |
| `validate_classes` | 校验类名列表的有效性 | 检查代码中是否存在拼写错误或不存在类名 |
| `get_theme` | 返回当前项目的 Tailwind 主题配置（JSON） | AI 了解项目的 colors/spacing/screens 等配置 |
| **Resource**: `tailwind://theme` | 以资源形式暴露主题 | AI 自动加载项目主题上下文 |

**v4 支持**：支持自动读取项目的 CSS 文件中的 `@theme` 块和 `@import "tailwindcss"` 指令。启动时指定环境变量 `TAILWIND_VERSION=4` 即可。

### 3.3 辅助方案：@colorsandfonts/mcp

适用场景：当需要**生成新的调色板**或**校验颜色对比度**时。

- 生成 Tailwind v4 格式的调色板
- WCAG 2.1 / APCA 对比度检查
- 单色/互补色方案自动生成

> **注意**：本项目品牌色已基于 Tailwind `blue` 色阶固化在 [design.md](design.md) 中，此方案仅在需要扩展新色系时使用。

---

## 4. ElementPlus MCP 替代方案

### 4.1 现状

**ElementPlus 目前没有公开可用的 MCP Server**。社区现有的 `@jd/find-plus-mcp` 是京东内部项目，无法公开安装。

### 4.2 替代方案

#### 方案 A：WebFetch 实时查文档（推荐）

在需要查询 ElementPlus 组件 API 时，Claude Code 内置的 `WebFetch` 工具可直接抓取官方文档：

```
# 使用方式：在对话中直接要求查询
"查询 ElementPlus el-dialog 的 Props 列表"
"检查 el-table 的 Events 有哪些"
```

**官方文档地址**：
- 组件列表：`https://element-plus.org/en-US/component/overview.html`
- 单个组件：`https://element-plus.org/en-US/component/{component-name}.html`

**优点**：无需安装，始终获取最新文档。
**缺点**：每次查询需要一次网络请求，有轻微延迟。

#### 方案 B：本地 TypeScript 类型推断（辅助）

ElementPlus v2 提供完整的 TypeScript 类型定义。Vue 3 + VSCode 环境下，编辑器自动提供组件 Props/Events 的智能提示，MCP 的查询需求相对较低：

```typescript
import type { ButtonProps, InputProps, DialogProps } from 'element-plus'

// VSCode 自动提供 Props 智能提示，无需 MCP 查询
const buttonProps: Partial<ButtonProps> = {
  type: 'primary',
  size: 'large',
}
```

#### 方案 C：自建简易 MCP Server（长期方案）

如果项目规模扩大，可基于 ElementPlus 官方文档构建 MCP Server，并通过 CC-Switch 注册：

1. 爬取 `element-plus.org` 组件文档页面
2. 提取每个组件的 Props / Slots / Events 定义
3. 封装为 MCP Tool，提供 `list-components` / `get-component-docs` 两个接口
4. 在 CC-Switch 中添加为自定义 MCP Server

> **预估工作量**：2-3 天。建议在项目中期（组件使用量大时）再投入。

---

## 5. 通过 CC-Switch 安装 MCP

### 5.1 添加 tailwindcss-mcp

**方式一：GUI 操作（推荐）**

1. 打开 CC-Switch 桌面应用
2. 进入 **MCP 管理** 面板
3. 点击 **添加 MCP Server**
4. 填写配置：

| 字段 | 值 |
|------|-----|
| 名称 | `tailwindcss` |
| 传输类型 | `stdio` |
| 命令 | `npx` |
| 参数 | `-y tailwindcss-mcp` |
| 环境变量 | `TAILWIND_VERSION=4` |

5. 确保 **启用** 开关打开
6. 点击 **同步** → MCP 配置自动写入 Claude Code 的 `settings.json`

**方式二：CC-Switch CLI**

```bash
# 添加 tailwindcss-mcp
cc-switch mcp add tailwindcss \
  --command npx \
  --args "-y tailwindcss-mcp" \
  --env "TAILWIND_VERSION=4"

# 同步到 Claude Code
cc-switch mcp sync --app claude
```

**方式三：Deep Link 一键导入**

在浏览器中点击以下链接，自动打开 CC-Switch 并填充 MCP 配置：

```
ccswitch://mcp/import?name=tailwindcss&command=npx&args=-y,tailwindcss-mcp&env=TAILWIND_VERSION=4
```

### 5.2 添加 @colorsandfonts/mcp（可选）

| 字段 | 值 |
|------|-----|
| 名称 | `colorsandfonts` |
| 传输类型 | `stdio` |
| 命令 | `npx` |
| 参数 | `-y @colorsandfonts/mcp` |

### 5.3 推荐配置组合

| MCP Server | 用途 | 优先级 |
|------------|------|--------|
| `tailwindcss-mcp` | Tailwind 类名推荐 + 校验 + 主题查询 | **必须** |
| WebFetch（Claude Code 内置） | ElementPlus 组件文档实时查询 | **按需** |
| `@colorsandfonts/mcp` | 调色板扩展 / 对比度校验 | **可选** |

### 5.4 CC-Switch 配置存储结构

配置完成后，CC-Switch 的 SSOT（单一数据源）存储如下：

```
~/.cc-switch/
├── config.json              ← CC-Switch 主配置（所有 MCP/Provider/Skills 定义）
└── backups/                 ← 自动备份（保留最近 10 个版本）
```

同步后的 Claude Code 配置：

```
~/.claude/
└── settings.json            ← CC-Switch 自动写入，无需手动编辑
```

**项目级配置**（团队共享）：如有项目专属 MCP，可在项目根目录创建 [.claude/mcp.json](.claude/mcp.json) 并提交 Git。

---

## 6. 验证与使用

### 6.1 验证 MCP 接入

在 Claude Code 中发送以下消息验证：

```
"列出当前项目 Tailwind 主题中定义的所有颜色"
"校验这组类名是否有效：bg-primary rounded-8 shadow-1"
"推荐一个蓝色按钮的 Tailwind 类名组合"
```

如果 MCP 正确接入，Claude 会调用 `get_theme` / `validate_classes` / `suggest_classes` 工具并返回结果。

### 6.2 检查 MCP 状态

```bash
# 通过 CC-Switch CLI 查看已安装的 MCP
cc-switch mcp list

# 查看同步状态
cc-switch mcp status
```

在 CC-Switch GUI 中，MCP 管理面板会显示每个 Server 的运行状态（绿色 = 正常，红色 = 异常）。

---

## 7. 常见问题

### Q1: tailwindcss-mcp 能读取项目自定义的 `@theme` 吗？

**能。** `tailwindcss-mcp` 在 v4 模式下会自动扫描项目中的 CSS 文件，解析 `@theme` 块中定义的自定义 Token，并将它们合并到 `get_theme` 的返回值中。这意味着通过 `@theme` 注册的 `--zh-*` Token（如 `--color-primary`、`--radius-8`）都可以被 AI 感知和使用。

### Q2: 为什么不直接用 ElementPlus 的类型定义，还需要 MCP？

两者互补：
- **TypeScript 类型**：编辑器端，提供代码编写时的 Props 校验和自动补全
- **MCP / WebFetch**：AI 对话端，让 Claude 在生成代码时直接引用最新的 API 文档，无需手动查文档

项目中两者**同时有效**，不冲突。

### Q3: CC-Switch 同步后 Claude Code 不生效？

1. 确保 CC-Switch 中 MCP Server 的 **启用** 开关已打开
2. 点击 **同步** 按钮手动触发一次同步
3. 完全退出 Claude Code 后重新启动（Claude Code 在启动时加载 `settings.json`）
4. 检查 `~/.claude/settings.json` 中是否已写入 MCP 配置

### Q4: 项目已经在 Vite 中配置了 `@tailwindcss/vite` 插件，还需要 MCP 吗？

**需要，它们是不同层面的工具：**

| 工具 | 作用层面 | 功能 |
|------|---------|------|
| `@tailwindcss/vite` | 构建时 | 编译 Tailwind CSS，生成最终的样式文件 |
| `tailwindcss-mcp` | 开发时（AI 对话） | 让 AI 理解和使用 Tailwind 类名，生成正确代码 |

两者互不干扰，可以同时使用。

### Q5: CC-Switch 与手动编辑 settings.json 冲突吗？

**不会冲突，但建议只用一种方式。** CC-Switch 采用 SSOT（单一数据源）设计，同步时会覆盖手动修改。推荐做法是**所有 MCP 管理统一通过 CC-Switch 操作**，不再手动编辑 `settings.json`，以 CC-Switch 的 `~/.cc-switch/config.json` 为唯一配置来源。

---

> **文档维护**：本文档随项目 MCP 配置变化更新。当前版本基于 2026-07-23 的 MCP 生态调研，接入方式为 CC-Switch。
