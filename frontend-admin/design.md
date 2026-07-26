# 智核（zh）Design System — 完整 Design Token 文档

---

## 目录

1. [Design Token 总览](#1-design-token-总览)
2. [色彩体系](#2-色彩体系)
3. [字体系统](#3-字体系统)
4. [间距系统](#4-间距系统)
5. [圆角系统](#5-圆角系统)
6. [阴影系统](#6-阴影系统)
7. [层级与遮罩](#7-层级与遮罩)
8. [组件规范](#8-组件规范)
9. [动效规范](#9-动效规范)

---

## 1. Design Token 总览

智核的设计系统基于 **TailwindCSS v4 + ElementPlus v2**，通过 CSS 自定义属性（Custom Properties）提供统一的设计 Token，命名空间为 `--zh-*`。整个 Token 系统分为以下层级：

```
基础 Token (Base Tokens)
├── 色彩 (Color)         — --zh-{color-name}
├── 字体 (Typography)    — --zh-font-*, --zh-font-size-*, --zh-line-height-*
├── 间距 (Spacing)       — --zh-spacing-*, --zh-base-spacing
├── 圆角 (Border Radius) — --zh-radius-*
├── 阴影 (Shadow)        — --zh-shadow*
├── 模糊 (Backdrop)      — --zh-backdrop-blur-*
│
语义 Token (Semantic Tokens)
├── 背景色               — --zh-background-{token}
├── 文字色               — --zh-text-{token}
├── 边框色               — --zh-line-{token}
├── 功能色               — --zh-{red|green|blue|orange|...}
│
主题 Token (Theme Tokens)
├── Light Mode (:root)
└── Dark Mode (data-theme=dark)
```

---

## 2. 色彩体系

> **色彩基准**：品牌色基于 TailwindCSS 内建 `blue` 色阶，确保与 `bg-blue-*`、`text-blue-*` 等工具类天然兼容。

### 2.1 品牌主色

| Token | Light | Dark | 用途 |
|-------|-------|------|------|
| `--zh-theme-primary` | `#2563EB` | `#60A5FA` | 品牌主色 |
| `--zh-color-primary` | `#2563EB` | `#60A5FA` | 全局主色标识 |
| `--zh-text-theme` | `#2563EB` | `#60A5FA` | 主题文字色 |
| `--zh-line-theme` | `#3B82F6` | `#60A5FA` | 主题边框色 |
| `--zh-line-theme50` | `#2563EB80` | `#60A5FA80` | 主题边框色(半透明) |
| `--zh-line-theme20` | `#2563EB33` | `#60A5FA33` | 主题边框色(弱) |
| `--zh-gradient-blue` | `linear-gradient(135deg, #2563EB 0%, #60A5FA 100%)` | — | 蓝色渐变 |
| `--zh-gradient-dblue` | `linear-gradient(135deg, #1D4ED8 0%, #3B82F6 100%)` | — | 深蓝渐变 |

#### Tailwind Blue 色阶参考

本设计系统中所有品牌蓝色均取自以下 Tailwind 内建色阶：

| 色阶 | 色值 | 设计系统中的角色 |
|------|------|-----------------|
| `blue-50` | `#EFF6FF` | 最浅蓝底（消息气泡、弱化区） |
| `blue-100` | `#DBEAFE` | 浅蓝底（选项选中态、悬浮态） |
| `blue-200` | `#BFDBFE` | 选中态背景 |
| `blue-400` | `#60A5FA` | Dark 模式主色 |
| `blue-500` | `#3B82F6` | 主题边框、交互态强调 |
| `blue-600` | `#2563EB` | Light 模式主色（品牌标识色） |
| `blue-700` | `#1D4ED8` | Light 模式 Hover / 链接文字 |

### 2.2 背景色

#### Light 模式

| Token | 色值 | 用途 |
|-------|------|------|
| `--zh-background-primary` | `#FFFFFF` | 主背景色（页面主体） |
| `--zh-background-base` | `#FFFFFF` | 基础背景色 |
| `--zh-background-pc-sidebar` | `#F7F7F9` | 侧边栏背景 |
| `--zh-background-pop` | `#FFFFFF` | 弹出层背景（Modal/Dropdown） |
| `--zh-background-capsule` | `#FFFFFF` | 胶囊/卡片背景 |
| `--zh-background-card` | `#2563EB1A` | 卡片背景（透明蓝） |
| `--zh-background-option` | `#22222208` | 选项背景（极浅灰） |
| `--zh-background-option-on` | `#DBEAFE` | 选项选中背景（浅蓝） |
| `--zh-background-tag` | `#2222220F` | 标签背景 |
| `--zh-background-hover` | — | 悬浮态背景 |
| `--zh-background-button` | `#2563EB` | 主按钮背景 |
| `--zh-background-button-hover` | `#1D4ED8` | 按钮悬浮背景 |
| `--zh-background-black-button` | `#222222` | 黑色按钮背景 |
| `--zh-background-gray-button-hover` | `#F8F8F8` | 灰色按钮悬浮态 |
| `--zh-background-light` | `#F7F8FC` | 浅色背景区 |
| `--zh-background-light-gray` | `#F5F6F7` | 浅灰背景 |
| `--zh-background-light-grey` | `#E7E7EA` | 中灰背景 |
| `--zh-background-menu` | `#F6F6F6` | 菜单背景 |
| `--zh-background-select` | `#DBEAFE` | 选中态背景 |
| `--zh-background-user-query` | `#EFF6FF` | 用户消息气泡背景 |
| `--zh-background-answer-card` | `#FFFFFF99` | 回答卡片背景 |
| `--zh-background-area` | `#2563EB1A` | 区域背景标记 |
| `--zh-background-weaken` | `#2563EB0D` | 弱化背景 |
| `--zh-background-toast` | `#000000` | Toast 背景（纯黑） |
| `--zh-background-floating` | `#0000004D` | 浮动层背景 |
| `--zh-background-overlay` | `#00000033` | 遮罩层背景 |
| `--zh-background-setting` | `#FFFFFF` | 设置面板背景 |
| `--zh-background-input` | `#FFFFFFCC` | 输入框背景 |

#### Dark 模式

| Token | 色值 | 用途 |
|-------|------|------|
| `--zh-background-primary` | `#222222` | 主背景色 |
| `--zh-background-base` | `#222222` | 基础背景色 |
| `--zh-background-pc-sidebar` | `#111112` | 侧边栏背景 |
| `--zh-background-pop` | `#222222` | 弹出层背景 |
| `--zh-background-capsule` | `#2C2C2C` | 卡片背景 |
| `--zh-background-option` | `#FAFBFF0D` | 选项背景 |
| `--zh-background-option-on` | `#1E3050` | 选项选中态 |
| `--zh-background-tag` | `#FAFBFF1F` | 标签背景 |
| `--zh-background-button` | `#60A5FA` | 主按钮背景 |
| `--zh-background-button-hover` | `#3B82F6` | 按钮悬浮背景 |
| `--zh-background-black-button` | `#FAFBFF` | 黑色按钮背景 |
| `--zh-background-gray-button-hover` | `#19191A` | 灰色按钮悬浮 |
| `--zh-background-light` | `#141420` | 浅色区 |
| `--zh-background-light-gray` | `#111112` | 浅灰背景 |
| `--zh-background-light-grey` | `#262626` | 中灰背景 |
| `--zh-background-menu` | `#1E1E1E` | 菜单背景 |
| `--zh-background-user-query` | `#1E3050` | 用户消息气泡背景 |
| `--zh-background-input` | `#212121` | 输入框背景 |

### 2.3 文字色

| Token | Light | Dark | 用途 |
|-------|-------|------|------|
| `--zh-text-primary` | `#222222` | `#FAFBFF` | 主要文字 |
| `--zh-text-secondary` | `#666666` | `#FAFBFFB3` | 次要文字 |
| `--zh-text-caption` | `#999999` | `#FAFBFF80` | 说明文字 |
| `--zh-text-disabled` | `#CCCCCC` | `#FAFBFF3D` | 禁用文字 |
| `--zh-text-white` | `#FFFFFF` | `#FFFFFF` | 白色文字（恒常） |
| `--zh-text-link` | `#1D4ED8` | `#60A5FA` | 链接文字 |
| `--zh-text-theme` | `#2563EB` | `#60A5FA` | 主题色文字 |
| `--zh-text-theme-disabled` | `#2563EB33` | `#60A5FA4D` | 主题色禁用 |
| `--zh-text-line-base` | `#222222` | `#FAFBFF` | 文字行底色 |

### 2.4 边框色（Line）

| Token | Light | Dark | 用途 |
|-------|-------|------|------|
| `--zh-line-border` | `#2222220F` | `#FAFBFF1F` | 通用边框/分割线 |
| `--zh-line-heavier` | `#2222221F` | `#FAFBFF33` | 加重视觉边框 |
| `--zh-line-parting` | `#22222208` | `#FAFBFF0D` | 弱分割线 |
| `--zh-line-capsule` | `#2563EB1A` | `#60A5FA1A` | 胶囊边框 |
| `--zh-line-circle` | `#FFFFFF` | `#222222` | 圆形元素边框 |
| `--zh-line-tag` | `#2563EB0D` | `#60A5FA14` | 标签边框 |

### 2.5 功能色

| Token | Light | Dark | 用途 |
|-------|-------|------|------|
| `--zh-red` | `#FF4040` | `#FF4040` | 危险/错误 |
| `--zh-danger-clicked` | `#DB2323` | `#DB2323` | 危险点击态 |
| `--zh-danger-disabled` | `#FF404080` | `#FF404080` | 危险禁用态 |
| `--zh-danger-background` | `#FF40401A` | `#FF40401A` | 危险背景 |
| `--zh-orange` | `#FF6B3F` | `#FF6B3F` | 警告/橙色 |
| `--zh-yellow` | `#FFD575` | `#FFD575` | 黄色高亮 |
| `--zh-yellow-light` | `#FFFBE5` | `#FFFBE51A` | 浅黄色背景 |
| `--zh-green` | `#1F993F` | `#1F993F` | 成功/绿色 |
| `--zh-cyan` | `#29BECC` | `#91EAF2` | 青色/信息 |
| `--zh-earth` | `#B37536` | `#E7A462` | 大地色/褐色 |

### 2.6 遮罩层

| Token | 色值 | 用途 |
|-------|------|------|
| `--zh-background-mask70` | `#000000B3` (70%) | 强遮罩 |
| `--zh-background-mask50` | `#00000080` (50%) | 中遮罩 |
| `--zh-background-mask10` | `#0000001A` (10%) | 弱遮罩 |
| `--zh-background-mask5` | `#0000000D` (5%) | 最弱遮罩 |

### 2.7 Gradient 渐变

| Token | 值 |
|-------|----|
| `--zh-gradient-blue` | `linear-gradient(135deg, #2563EB 0%, #60A5FA 100%)` |
| `--zh-gradient-dblue` | `linear-gradient(135deg, #1D4ED8 0%, #3B82F6 100%)` |

---

## 3. 字体系统

### 3.1 字体族（Font Family）

#### 多平台适配字体系列

```css
/* 基础字体栈 */
--zh-font-text: /* 根据平台自动切换 */;

/* macOS - 拉丁文字 */
--zh-font-text-mac-latin: -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui,
  "Helvetica Neue", Helvetica, Arial, sans-serif;

/* macOS - 中文 */
--zh-font-text-mac-zh: "PingFang SC", -apple-system, BlinkMacSystemFont, "Hiragino Sans GB",
  "Hiragino Sans", "SF Pro Text", system-ui, "Noto Sans SC", "Helvetica Neue", Helvetica, Arial, sans-serif;

/* macOS - 日文 */
--zh-font-text-mac-ja: "Hiragino Sans", "Hiragino Kaku Gothic ProN", -apple-system,
  BlinkMacSystemFont, "PingFang SC", "SF Pro Text", system-ui, "Noto Sans JP",
  "Helvetica Neue", Helvetica, Arial, sans-serif;

/* Windows - 拉丁文字 */
--zh-font-text-windows-latin: "Segoe UI", system-ui, Roboto, "Noto Sans", "Helvetica Neue",
  Arial, sans-serif;

/* Windows - 中文 */
--zh-font-text-windows-zh: "Microsoft YaHei", "Segoe UI", system-ui, Roboto, "Noto Sans SC",
  "Helvetica Neue", Arial, sans-serif;

/* Windows - 日文 */
--zh-font-text-windows-ja: Meiryo, "Yu Gothic UI", "Segoe UI", system-ui, Roboto,
  "Noto Sans JP", "Helvetica Neue", Arial, sans-serif;

/* 数字字体 */
--zh-font-number: "PlusJakartaSans", system-ui, "Segoe UI", Roboto,
  "Helvetica Neue", Arial, sans-serif;

/* 等宽字体 */
--zh-font-code: ui-monospace, "SFMono-Regular", "SF Mono", Menlo, Consolas,
  "Liberation Mono", monospace;
```

#### 预加载字体

| 字体 | 字重 | 格式 |
|------|------|------|
| PlusJakartaSans | Medium（500） | TTF |
| PlusJakartaSans | SemiBold（600） | TTF |
| PlusJakartaSans | Bold（700） | TTF |

### 3.2 字号系统

| Token | 值 (px) | 语义用途 |
|-------|---------|---------|
| `--zh-font-size8` | 8px | 极小标注 |
| `--zh-font-size9` | 9px | — |
| `--zh-font-size10` | 10px | 极小文字 |
| `--zh-font-size11` | 11px | — |
| `--zh-font-size12` | 12px | 辅助说明/标签 |
| `--zh-font-size13` | 13px | — |
| `--zh-font-size14` | 14px | 正文/按钮 |
| `--zh-font-size15` | 15px | — |
| `--zh-font-size16` | 16px | 大号正文 |
| `--zh-font-size17` | 17px | — |
| `--zh-font-size18` | 18px | 小标题 |
| `--zh-font-size20` | 20px | 标题/面板标题 |
| `--zh-font-size24` | 24px | 大标题 |
| `--zh-font-size30` | 30px | 页面标题 |
| `--zh-font-size32` | 32px | 大标题(强调) |
| `--zh-font-size36` | 36px | 超大标题 |
| `--zh-font-size48` | 48px | Hero 标题 |
| `--zh-font-size60` | 60px | — |
| `--zh-font-size72` | 72px | — |
| `--zh-font-size96` | 96px | — |
| `--zh-font-size128` | 128px | — |

**语义化字号映射**:

| Token | 值 | 用途 |
|-------|-----|------|
| `--zh-text-xs` | 12px | 极小 |
| `--zh-text-sm` | 14px | 小号 |
| `--zh-text-base` | 16px | 基础 |
| `--zh-text-lg` | 18px | 大号 |
| `--zh-text-xl` | 20px | 标题 |

### 3.3 字重

| 值 | 语义 |
|----|------|
| 300 | Light |
| 400 | Regular（标准） |
| 500 | Medium |
| 510 | Medium+（半粗） |
| 600 | SemiBold |
| 700 | Bold |

**基础映射**:
- `--zh-base-weight: 400`
- `--base-text-font-weight: 600`
- `--base-title-font-weight: 600`

### 3.4 行高系统

`--zh-line-height-{N}px` 支持从 1px 到 50px 的完整阶梯。

**常用语义行高**:

| Token | 值 | 用途 |
|-------|-----|------|
| `--font-base-line-height` | 26px | 基础正文行高 |
| `--zh-base-line-height` | 1.5 | 基础相对行高 |
| `--zh-base-line-height-rem` | 1.5rem | 基础行高(rem) |
| `body line-height` | 1.5715 | 全局默认行高 |

### 3.5 字间距

| Token | 值 |
|-------|-----|
| `--zh-tracking-normal` | 1px |
| `--zh-tracking-tight` | -0.025em |
| `--zh-tracking-tighter` | -0.05em |
| `--zh-tracking-wide` | +0.025em |
| `--zh-tracking-wider` | +0.05em |
| `--zh-tracking-widest` | +0.1em |

---

## 4. 间距系统

### 4.1 基础间距单位

- 基础单位（Base Size）: **16px** (`--zh-base-size`)
- 基础间距: **0.0625rem** = 1px (`--zh-base-spacing`)
- 间距体系基于 `rem` 和 `px` 混合使用

### 4.2 常用间距值

| 值 (px) | 值 (rem) | 使用场景 |
|---------|---------|---------|
| 2px | 0.125rem | 极紧凑，图标与文字间距 |
| 4px | 0.25rem | 紧凑间距，按钮内图标间距 |
| 6px | 0.375rem | 标签间距 |
| 8px | 0.5rem | 元素间小间距 |
| 10px | 0.625rem | 列表项间距 |
| 12px | 0.75rem | 组件内间距 |
| 16px | 1rem | 基准间距，卡片内边距 |
| 20px | 1.25rem | 区块间距 |
| 24px | 1.5rem | 区域间距 |
| 32px | 2rem | 大区块间距 |
| 40px | 2.5rem | 页面级间距 |

### 4.3 组件级间距 Token

| Token | 值 | 用途 |
|-------|-----|------|
| `--chat-margin` | 40px / 16px | 聊天消息间间距 |
| `--card-margin` | 16px | 卡片外边距 |
| `--chat-composer-horizontal-padding` | 40px | 输入区水平内边距 |
| `--chat-composer-horizontal-padding-total` | 80px | 输入区总水平内边距 |
| `--chat-input-visible-shell-side-gutter` | 24px / 8px | 输入框外壳间距 |
| `--chat-welcome-top-wrapper-normal-gap` | 40px | 欢迎区顶部间距 |
| `--chat-welcome-top-wrapper-temporary-gap` | 15px | 欢迎区临时间距 |
| `--chat-welcome-top-wrapper-temporary-height` | 104px | 欢迎区临时高度 |
| `--gap` | 8px | 通用栅格间距 |
| `--font-list-margin` | 8px | 列表字体间距 |
| `--font-markdown-margin` | 16px | Markdown 段落间距 |
| `--h-margin-bottom` | 8px | 标题下边距 |
| `--p-margin-bottom` | 16px | 段落下边距 |
| `--ol-li-margin` | 16px | 列表项外边距 |

---

## 5. 圆角系统

### 5.1 完整圆角阶梯

`--zh-radius-{N}` 支持 0–50px 的完整递增阶梯，步长 1px。

**常用圆角语义**:

| Token | 值 | 典型用途 |
|-------|-----|---------|
| `--zh-radius0` | 0px | 无圆角 |
| `--zh-radius2` | 2px | 极微圆角 |
| `--zh-radius4` | 4px | 微圆角，小标签 |
| `--zh-radius6` | 6px | 小输入框 |
| `--zh-radius8` | 8px | **通用圆角 — 按钮、输入框、小卡片** |
| `--zh-radius10` | 10px | 中等圆角 |
| `--zh-radius12` | 12px | 大圆角，卡片 |
| `--zh-radius13` | 13px | — |
| `--zh-radius14` | 14px | — |
| `--zh-radius16` | 16px | **超大圆角 — 主容器、对话框** |
| `--zh-radius18` | 18px | 消息气泡 |
| `--zh-radius20` | 20px | 胶囊形状 |
| `--zh-radius24` | 24px | 大胶囊 |
| `--zh-radius28` | 28px | 底部面板上圆角 |
| `--zh-radius32` | 32px | 特大圆角 |

**通用类映射**:
- `.rounded-8` → `--zh-radius8`（8px）
- `.rounded-12` → `--zh-radius12`（12px）
- `.rounded-16` → `--zh-radius16`（16px）
- `.rounded-20` → `--zh-radius20`（20px）
- `.rounded-full` → `9999px`（圆形）
- `.rounded-[50%]` → `50%`（圆形/椭圆）

---

## 6. 阴影系统

### 6.1 基础阴影层级

| Token | 值 | 层级语义 |
|-------|-----|---------|
| `--zh-shadow1` | `0px 8px 16px -4px rgba(0,0,0,0.05)` | **低层** — 卡片悬浮，轻微抬高 |
| `--zh-shadow2` | `0px 12px 24px -2px rgba(0,0,0,0.05)` | **中层** — 下拉菜单，弹出面板 |
| `--zh-shadow3` | `0px 12px 36px 0px rgba(0,0,0,0.10)` | **高层** — Modal 对话框，Drawer |

### 6.2 组件级阴影

| 阴影值 | 用途 |
|--------|------|
| `0 4px 12px rgba(33,32,35,0.20)` | Toast/通知（暗色） |
| `0 2px 8px rgba(0,0,0,0.08)` | 轻阴影 — 通用元素 |
| `0 6px 10px rgba(0,0,0,0.08)` | 悬浮按钮 |
| `0 8px 16px rgba(0,0,0,0.05)` | 卡片悬浮态 |
| `0 12px 32px rgba(0,0,0,0.28)` | 强阴影 — 大模态 |
| `0 4px 8px -6px rgba(0,0,0,0.06)` | 卡片内凹阴影 |
| `4px 4px 20px 2px rgba(33,32,35,0.08)` | 特殊装饰阴影 |

### 6.3 暗色模式阴影

| 阴影值 | 用途 |
|--------|------|
| `0 12px 24px -2px rgba(0,0,0,0.05)` | 中层阴影暗色版 |
| `0 10px 40px rgba(0,0,0,0.30), 0 2px 8px rgba(0,0,0,0.20)` | 深色模式强阴影 |

---

## 7. 层级与遮罩

### 7.1 Z-Index 系统

| 层级 | 值 | 用途 |
|------|-----|------|
| 基础内容 | 0–9 | 页面内容 |
| 浮动按钮 | 99 | FAB 悬浮按钮 |
| 粘性元素 | 100 | Sticky header |
| 工具提示 | 1000–1002 | Tooltip/Popover |
| 遮罩层 | 1030–1050 | Modal mask |
| 对话框 | 1060–1100 | Modal/Dialog |
| Toast | 2000 | 轻提示 |
| 最大 | 9998–9999 | 特殊覆盖层 |
| 极限值 | 99999999 | 全屏覆盖 |

### 7.2 模糊效果

`--zh-backdrop-blur-{N}` 系统，支持 0–50px 完整阶梯。

**常用值**:
- 2px — 轻微模糊
- 4px — 菜单背景
- 8px — Modal 背景
- 12px — 毛玻璃效果
- 20px — 强毛玻璃

---

## 8. 组件规范

> **核心原则**：本项目的 UI 组件库为 **ElementPlus v2**。所有通用组件（Button、Input、Card、Modal、Toast、Avatar 等）统一使用 ElementPlus，仅通过 CSS 变量覆盖品牌主题。仅当 ElementPlus 中确实不存在对应组件时，才定义自定义组件规范。

### 8.0 ElementPlus 全局主题覆盖

在 [src/style.css](src/style.css) 中通过覆盖 ElementPlus 的 `--el-*` CSS 变量，使所有 ElementPlus 组件自动继承 `--zh-*` 品牌 Token：

| ElementPlus 变量 | 映射到 | 说明 |
|------------------|--------|------|
| `--el-color-primary` | `--zh-theme-primary` | 主色 |
| `--el-color-primary-light-3` | `#DBEAFE` (blue-100) | 浅色变体（用于悬浮态背景） |
| `--el-color-primary-light-5` | `#EFF6FF` (blue-50) | 更浅变体 |
| `--el-color-primary-light-7` | `#BFDBFE` (blue-200) | 最浅变体 |
| `--el-color-primary-light-9` | `#EFF6FF` (blue-50) | 极浅变体 |
| `--el-color-primary-dark-2` | `#1D4ED8` (blue-700) | 深色变体（点击态） |
| `--el-color-success` | `--zh-green` | 成功色 |
| `--el-color-warning` | `--zh-orange` | 警告色 |
| `--el-color-danger` | `--zh-red` | 危险色 |
| `--el-color-info` | `--zh-cyan` | 信息色 |
| `--el-text-color-primary` | `--zh-text-primary` | 主文字色 |
| `--el-text-color-regular` | `--zh-text-secondary` | 常规文字色 |
| `--el-text-color-secondary` | `--zh-text-caption` | 次要文字色 |
| `--el-text-color-placeholder` | `--zh-text-disabled` | 占位符文字色 |
| `--el-border-color` | `--zh-line-border` | 边框色 |
| `--el-border-color-light` | `--zh-line-parting` | 浅边框色 |
| `--el-border-color-lighter` | `--zh-line-parting` | 更浅边框色 |
| `--el-border-color-dark` | `--zh-line-heavier` | 深边框色 |
| `--el-border-radius-base` | `--zh-radius8` | 基础圆角 |
| `--el-bg-color` | `--zh-background-primary` | 主背景色 |
| `--el-bg-color-page` | `--zh-background-light` | 页面背景色 |
| `--el-bg-color-overlay` | `--zh-background-pop` | 弹出层背景色 |

**实现示例**（在 `src/style.css` 中）：

```css
@import "tailwindcss";

/* ===== ElementPlus 主题覆盖 ===== */
:root {
  --el-color-primary: var(--zh-theme-primary);
  --el-color-primary-light-3: #DBEAFE;
  --el-color-primary-light-5: #EFF6FF;
  --el-color-primary-light-7: #DBEAFE;
  --el-color-primary-light-9: #EFF6FF;
  --el-color-primary-dark-2: #1D4ED8;
  --el-color-success: var(--zh-green);
  --el-color-warning: var(--zh-orange);
  --el-color-danger: var(--zh-red);
  --el-color-info: var(--zh-cyan);
  --el-text-color-primary: var(--zh-text-primary);
  --el-text-color-regular: var(--zh-text-secondary);
  --el-border-color: var(--zh-line-border);
  --el-border-radius-base: var(--zh-radius8);
  --el-bg-color: var(--zh-background-primary);
}

[data-theme="dark"] {
  --el-color-primary: var(--zh-theme-primary);
  --el-color-primary-light-3: #1E3050;
  --el-color-primary-light-5: #1A2740;
  --el-color-primary-dark-2: #3B82F6;
  --el-text-color-primary: var(--zh-text-primary);
  --el-bg-color: var(--zh-background-primary);
}
```

---

### 8.1 按钮 (Button) — 使用 ElButton

**ElementPlus 组件**：[`<el-button>`](https://element-plus.org/en-US/component/button.html)

**Props 对应关系**：

| 设计需求 | ElButton Prop |
|---------|---------------|
| 主按钮 | `type="primary"` |
| 次按钮 | 默认（不设 type） |
| 文字按钮 | `type="primary" link` |
| 危险按钮 | `type="danger"` |
| 尺寸 | `size="small" / "default" / "large"` |
| 圆角 | `round` |
| 圆形 | `circle` |
| 加载态 | `loading` |
| 禁用 | `disabled` |

**品牌色覆盖**：全局 `--el-color-primary` 已映射到 `--zh-theme-primary`，无需逐组件覆盖。

**自定义变体（ElementPlus 不提供的样式）**：

| 变体 | 说明 | 实现方式 |
|------|------|---------|
| 黑色按钮 | 深色背景按钮（如 Hero 区 CTA） | 自定义 CSS 类，背景 `#222` / `#FAFBFF`，通过 `--zh-background-black-button` 控制 |
| 灰色按钮 | 中性灰色调悬浮按钮 | `--zh-background-gray-button-hover`，ElementPlus 默认无此变体 |

---

### 8.2 输入框 (Input) — 使用 ElInput

**ElementPlus 组件**：[`<el-input>`](https://element-plus.org/en-US/component/input.html)

**Props 对应关系**：

| 设计需求 | ElInput 配置 |
|---------|-------------|
| 文本输入 | `<el-input>` |
| 多行文本 | `<el-input type="textarea">` |
| 尺寸 | `size="small" / "default" / "large"` |
| 可清除 | `clearable` |
| 密码 | `show-password` |
| 禁用 | `disabled` |

**状态样式**（由 ElementPlus 内置 + `--el-*` 变量自动处理）：

| 状态 | 效果 |
|------|------|
| Default | ElementPlus 默认样式 |
| Focus | 边框色自动使用 `--el-color-primary`（已映射到 `--zh-theme-primary`） |
| Hover | 边框色加深（ElementPlus 内置） |
| Disabled | ElementPlus 内置禁用态 |
| Error | 使用 `--el-color-danger`（已映射到 `--zh-red`） |

---

### 8.3 卡片 (Card) — 使用 ElCard

**ElementPlus 组件**：[`<el-card>`](https://element-plus.org/en-US/component/card.html)

**插槽对应**：

| 设计需求 | ElCard Slot |
|---------|------------|
| 卡片标题 | `header` |
| 卡片内容 | `default` |

**品牌色覆盖**：

| 属性 | 值 | 说明 |
|------|-----|------|
| 背景 | `--zh-background-capsule` | Light `#FFF` / Dark `#2C2C2C` |
| 圆角 | `--zh-radius12` | 12px |
| 阴影 | `--zh-shadow1` | 低层阴影 |

**Hover 态**（自定义增强，ElementPlus 默认无悬浮效果）：

- 背景色 → `--zh-background-option` / `--zh-background-tag`
- 阴影 → `--zh-shadow2`
- 边框 → `--zh-line-heavier`

---

### 8.4 消息气泡 (Chat Message) — 自定义组件

> **ElementPlus 无聊天消息气泡组件，使用自定义实现。**

| 属性 | 用户消息 | AI 消息 |
|------|---------|---------|
| 背景色 | `--zh-background-user-query` (`#EFF6FF`/`#1E3050`) | `--zh-background-answer-card` |
| 文字色 | `--zh-text-primary` | `--zh-text-primary` |
| 对齐 | 靠右 | 靠左 |
| 最大宽度 | 80%（消息内容），664–800px（列表） | 同左 |
| 圆角 | 8px–18px | 8px–18px |
| 间距 | `--chat-margin: 40px`（多轮对话） | 同左 |

---

### 8.5 侧边栏 (Sidebar) — 使用 ElMenu + 自定义容器

> **菜单项**使用 ElementPlus 的 `<el-menu>`，**整体布局容器**使用自定义实现。

**菜单部分 — 使用 ElMenu**：

| 设计需求 | ElMenu 配置 |
|---------|------------|
| 垂直菜单 | `<el-menu>` 默认模式 |
| 菜单项 | `<el-menu-item>` |
| 图标 | `<el-icon>` 嵌入 slot |
| 折叠 | `collapse` prop |
| 路由模式 | `router` prop |

**侧边栏容器 — 自定义**（ElementPlus 无此组件）：

| 属性 | 值 |
|------|-----|
| 背景 | `--zh-background-pc-sidebar` (`#F7F7F9`/`#111112`) |
| 内边距 | `16px 12px` |
| 滚动条 | 4px 宽，`--zh-line-border` 色 |

---

### 8.6 对话框 (Modal) — 使用 ElDialog / ElMessageBox

**ElementPlus 组件**：

| 场景 | ElementPlus 组件 |
|------|-----------------|
| 自定义内容对话框 | [`<el-dialog>`](https://element-plus.org/en-US/component/dialog.html) |
| 确认/提示/输入框 | [`<el-message-box>`](https://element-plus.org/en-US/component/message-box.html) |

**品牌色覆盖**：

| 属性 | 值 | 说明 |
|------|-----|------|
| 背景 | `--zh-background-pop` | Light `#FFF` / Dark `#222` |
| 遮罩 | `--zh-background-mask50` | 50% 黑色遮罩 |
| 圆角 | `--zh-radius16` | 16px |
| 阴影 | `--zh-shadow3` | 高层阴影 |

---

### 8.7 Toast / 通知 — 使用 ElMessage / ElNotification

**ElementPlus 组件**：

| 场景 | ElementPlus 组件 |
|------|-----------------|
| 轻量提示（自动消失） | [`<el-message>`](https://element-plus.org/en-US/component/message.html) |
| 通知卡片（带标题） | [`<el-notification>`](https://element-plus.org/en-US/component/notification.html) |

**ElMessage 主题覆盖**：

| 属性 | 映射 |
|------|------|
| 成功色 | `--el-color-success` → `--zh-green` |
| 警告色 | `--el-color-warning` → `--zh-orange` |
| 错误色 | `--el-color-danger` → `--zh-red` |

---

### 8.8 头像 (Avatar) — 使用 ElAvatar

**ElementPlus 组件**：[`<el-avatar>`](https://element-plus.org/en-US/component/avatar.html)

**Props 对应关系**：

| 设计需求 | ElAvatar Prop |
|---------|---------------|
| 尺寸 | `size="small" / "default" / "large"` 或直接传数字 |
| 形状 | `shape="circle" / "square"` |
| 图标 | `icon` slot |
| 图片 | `src` prop |
| 文字回退 | 默认 slot |

**自定义增强**：不同角色使用不同背景色：

| 角色 | 背景色 |
|------|--------|
| 用户 | `--zh-blue-500` (`#3B82F6`) |
| AI / 助手 | `--zh-theme-primary` (`#2563EB`) |

---

## 9. 动效规范

### 9.1 过渡动画

| 属性 | 值 | 用途 |
|------|-----|------|
| 持续时间 | 150ms / 200ms / 300ms / 500ms | 悬停、淡入、展开 |
| 缓动函数 | `cubic-bezier(0.4, 0, 0.2, 1)` | 标准缓动（ease-in-out） |
| 缓动函数 | `cubic-bezier(0, 0, 0.2, 1)` | 淡出（ease-out） |
| 缓动函数 | `cubic-bezier(0.34, 1.56, 0.64, 1)` | 弹性进入（pop） |

### 9.2 Keyframes 动画

| 动画名 | 用途 |
|--------|------|
| `fadeIn` | 消息淡入、元素出现 |
| `fade` | 淡入淡出通用 |
| `enter` / `exit` | Modal/Popover 进出 |
| `spin` | 加载旋转 |
| `pulse` | 脉冲高亮 0.2s（发送反馈） |
| `shimmer` | Skeleton 骨架屏闪烁 |
| `skeleton-loading` | 骨架屏加载 |
| `ping` | 通知红点 |
| `loadingSpin` | 加载器 |
| `slideInFromRight` | 登录面板滑入 |

---

## 附录 A: Light/Dark 模式快速对照

| Token | Light | Dark |
|-------|-------|------|
| `--zh-theme-primary` | `#2563EB` | `#60A5FA` |
| `--zh-background-primary` | `#FFFFFF` | `#222222` |
| `--zh-background-pc-sidebar` | `#F7F7F9` | `#111112` |
| `--zh-background-pop` | `#FFFFFF` | `#222222` |
| `--zh-background-capsule` | `#FFFFFF` | `#2C2C2C` |
| `--zh-background-option` | `#22222208` | `#FAFBFF0D` |
| `--zh-background-option-on` | `#DBEAFE` | `#1E3050` |
| `--zh-background-tag` | `#2222220F` | `#FAFBFF1F` |
| `--zh-text-primary` | `#222222` | `#FAFBFF` |
| `--zh-text-secondary` | `#666666` | `#FAFBFFB3` |
| `--zh-text-caption` | `#999999` | `#FAFBFF80` |
| `--zh-text-disabled` | `#CCCCCC` | `#FAFBFF3D` |
| `--zh-text-link` | `#1D4ED8` | `#60A5FA` |
| `--zh-text-theme` | `#2563EB` | `#60A5FA` |
| `--zh-line-border` | `#2222220F` | `#FAFBFF1F` |
| `--zh-line-heavier` | `#2222221F` | `#FAFBFF33` |
| `--zh-line-parting` | `#22222208` | `#FAFBFF0D` |
| `--zh-background-button` | `#2563EB` | `#60A5FA` |
| `--zh-background-button-hover` | `#1D4ED8` | `#3B82F6` |

主题切换方式: `data-theme="light"` / `data-theme="dark"`，HTML 根元素属性，Web 端默认为 `data-theme="light"`，也支持跟随系统 `data-theme="auto"`。

---

## 附录 B: 基础 Token 通用公式

```css
:root {
  --zh-base-size: 16px;
  --zh-base-spacing: 0.0625rem;   /* = 1px */
  --zh-base-radius: 0.0625rem;    /* = 1px */
  --zh-base-blur: 0.0625rem;      /* = 1px */
  --zh-base-weight: 400;
  --zh-base-line-height: 1.5;
  --zh-base-letter-spacing: 0em;
}
```

以此为基础，所有 radius/spacing/blur token 均可表示为 `N × --zh-base-*` 的整数倍。

---

## 附录 C: TailwindCSS v4 @theme 配置

TailwindCSS v4 使用 CSS-first 配置方式，通过 `@theme` 块将 `--zh-*` Token 注册为 Tailwind 工具类，实现 CSS 变量与工具类的双向互通。

**在 [src/style.css](src/style.css) 中配置**：

```css
@import "tailwindcss";

/* ===== 设计 Token ===== */
@theme {
  /* 品牌主色 */
  --color-primary: var(--zh-theme-primary);
  --color-primary-hover: var(--zh-background-button-hover);

  /* Tailwind Blue 色阶（品牌扩展）*/
  --color-blue-50: #EFF6FF;
  --color-blue-100: #DBEAFE;
  --color-blue-200: #BFDBFE;
  --color-blue-400: #60A5FA;
  --color-blue-500: #3B82F6;
  --color-blue-600: #2563EB;
  --color-blue-700: #1D4ED8;

  /* 圆角阶梯 */
  --radius-8: var(--zh-radius8);
  --radius-12: var(--zh-radius12);
  --radius-16: var(--zh-radius16);
  --radius-20: var(--zh-radius20);

  /* 阴影层级 */
  --shadow-1: var(--zh-shadow1);
  --shadow-2: var(--zh-shadow2);
  --shadow-3: var(--zh-shadow3);
}
```

**使用效果**：

| 设计需求 | Tailwind 工具类 | 等效 CSS 变量 |
|---------|----------------|--------------|
| 主色按钮背景 | `bg-primary` | `background: var(--zh-theme-primary)` |
| 浅蓝背景 | `bg-blue-50` | `background: #EFF6FF` |
| 选中态 | `bg-blue-100` | `background: #DBEAFE` |
| 主按钮 Hover | `bg-primary-hover` | `background: var(--zh-background-button-hover)` |
| 通用圆角 | `rounded-8` | `border-radius: var(--zh-radius8)` |
| 卡片阴影 | `shadow-1` | `box-shadow: var(--zh-shadow1)` |

---

> **技术栈**：基于 TailwindCSS v4.3.3 + ElementPlus v2.14.3，CSS 变量体系以 `--zh-*` 为命名空间。品牌蓝色来自 Tailwind 内建 `blue` 色阶。组件优先使用 ElementPlus，仅在其无对应组件时自定义。
