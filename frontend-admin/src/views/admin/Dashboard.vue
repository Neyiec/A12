<!--
  [数据交互说明]
  - 导入:
    - ElementPlus 组件: ElCard、ElTag、ElButton、ElAvatar、ElRadioGroup、ElRadioButton
    - ElementPlus Icons: 用于 KPI 卡片图标和快捷操作按钮图标
  - 依赖:
    - 无外部 API 调用，当前使用静态示例数据（后续替换为后端 API）
  - 输入: 无 props，数据在组件内部 mock
  - 输出: 渲染系统配置与数据看板首页视图（KPI 指标区 + 审核队列 + 快捷操作 + 系统告警）
  - 监听: `admin-refresh` 自定义事件（从 AdminHeader 刷新按钮发出），触发数据重新加载
-->
<script setup>
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import {
  Checked,
  UserFilled,
  FolderOpened,
  Monitor,
  EditPen,
  Upload,
  Download,
  Setting,
  ArrowUp,
  ArrowDown,
} from '@element-plus/icons-vue'

// ========== 响应式数据 ==========

/** 数据加载状态 */
const isLoading = ref(true)

/** 当前时间筛选范围（审核队列） */
const timeRange = ref('today')

/** KPI 指标卡片数据 */
const kpiCards = reactive([
  {
    id: 1,
    title: '待审核内容',
    icon: Checked,
    mainValue: '1,284',
    trendLabel: '12.5%',
    trendUp: true,          // true=上升(红色，需关注积压), false=下降
    trendColor: 'var(--zh-red)',
    subText: '较昨日增长 128 条待审内容',
    breakdown: 'Skill 856 条 · 案例 428 条',
  },
  {
    id: 2,
    title: '活跃教师数',
    icon: UserFilled,
    mainValue: '3,842',
    trendLabel: '+3.2%',
    trendUp: true,
    trendColor: 'var(--zh-green)',
    subText: '较昨日 +3.2%',
    breakdown: '今日新增注册 +56',
    hasStatusDot: true,
    statusColor: 'var(--zh-green)',
    statusLabel: '128 实时在线',
  },
  {
    id: 3,
    title: '知识库条目',
    icon: FolderOpened,
    mainValue: '15,630',
    trendLabel: '+238',
    trendUp: true,
    trendColor: 'var(--zh-green)',
    subText: '本周新增 238 条',
    breakdown: '覆盖 12 学科 · 1,280 知识点',
  },
  {
    id: 4,
    title: '系统健康度',
    icon: Monitor,
    mainValue: '99.7%',
    trendLabel: '正常',
    trendUp: true,
    trendColor: 'var(--zh-green)',
    subText: 'CPU 42% / 内存 68%',
    breakdown: '磁盘使用 31%',
    hasStatusDot: true,
    statusColor: 'var(--zh-green)',
    statusLabel: '运行正常',
  },
])

/** 审核队列列表数据 */
const auditQueue = ref([
  {
    id: 1,
    thumbnail: '',
    thumbnailType: 'doc',
    title: '勾股定理互动教学案例',
    type: '教学案例',
    submitter: { name: '张老师', avatar: '' },
    time: '2 分钟前',
    status: 'warning',
    statusLabel: '待审',
  },
  {
    id: 2,
    thumbnail: '',
    thumbnailType: 'image',
    title: '细胞分裂动画课件',
    type: 'H5 课件',
    submitter: { name: '李老师', avatar: '' },
    time: '5 分钟前',
    status: 'danger',
    statusLabel: '违规',
  },
  {
    id: 3,
    thumbnail: '',
    thumbnailType: 'video',
    title: '串联电路实验案例',
    type: '教学案例',
    submitter: { name: '王老师', avatar: '' },
    time: '12 分钟前',
    status: 'warning',
    statusLabel: '待审',
  },
  {
    id: 4,
    thumbnail: '',
    thumbnailType: 'doc',
    title: '背影 - 公开课教案 Skill',
    type: 'Skill',
    submitter: { name: '赵老师', avatar: '' },
    time: '28 分钟前',
    status: 'warning',
    statusLabel: '待审',
  },
])

/** 总待审核数 */
const totalPending = ref(28)

/** 快捷操作按钮列表 */
const quickActions = [
  { label: '发布平台公告', icon: EditPen, action: 'announcement' },
  { label: '添加管理员', icon: UserFilled, action: 'addAdmin' },
  { label: '上传公共资源', icon: Upload, action: 'uploadResource' },
  { label: '导出运营报表', icon: Download, action: 'exportReport' },
  { label: '系统参数配置', icon: Setting, action: 'systemConfig' },
]

/** 系统告警列表 */
const alerts = ref([
  {
    id: 1,
    severity: 'danger',
    severityColor: 'var(--zh-red)',
    title: 'AI 服务调用异常',
    detail: '近 30 分钟失败 12 次，错误率 4.7%',
    time: '10 分钟前',
  },
  {
    id: 2,
    severity: 'warning',
    severityColor: 'var(--zh-orange)',
    title: '导出任务队列积压',
    detail: '等待处理导出任务 47 项，最长等待 28 分钟',
    time: '25 分钟前',
  },
  {
    id: 3,
    severity: 'info',
    severityColor: 'var(--zh-cyan)',
    title: '知识库向量化完成',
    detail: '「2026 版数学教材」解析完成，入库 2.3 万条',
    time: '1 小时前',
  },
  {
    id: 4,
    severity: 'warning',
    severityColor: 'var(--zh-orange)',
    title: '存储空间使用预警',
    detail: '已用 82%（2.1TB / 2.56TB），建议扩容',
    time: '3 小时前',
  },
])

// ========== 方法 ==========

/**
 * 模拟数据加载
 * 页面首次渲染时展示骨架屏 0.8s 后显示真实数据
 */
const loadData = () => {
  isLoading.value = true
  setTimeout(() => {
    isLoading.value = false
  }, 800)
}

/**
 * 处理刷新 — 由 Header 的刷新按钮触发
 */
const handleRefresh = () => {
  loadData()
}

/**
 * 获取缩略图类型对应的占位图标字符
 * @param {'doc' | 'image' | 'video'} type - 文件类型
 * @returns {string} emoji 占位字符
 */
const getThumbnailIcon = (type) => {
  const map = { doc: '📄', image: '🖼', video: '🎬' }
  return map[type] || '📄'
}

/**
 * 获取状态标签类型映射
 * @param {'warning' | 'danger' | 'success' | 'info'} status - 状态标识
 * @returns {string} ElementPlus Tag type
 */
const getTagType = (status) => {
  const map = { warning: 'warning', danger: 'danger', success: 'success', info: 'info' }
  return map[status] || 'info'
}

// ========== 生命周期 ==========

onMounted(() => {
  loadData()
  window.addEventListener('admin-refresh', handleRefresh)
})

onBeforeUnmount(() => {
  window.removeEventListener('admin-refresh', handleRefresh)
})
</script>

<template>
  <div>
    <!-- ===================================================================
         1. 核心指标区 (KPI Cards Row) — 4 列等宽
         =================================================================== -->
    <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-5">
      <!-- 单张 KPI 卡片 -->
      <el-card
        v-for="card in kpiCards"
        :key="card.id"
        shadow="never"
        class="kpi-card cursor-pointer"
        :class="{ 'skeleton-pulse': isLoading }"
        :style="{
          background: 'var(--zh-background-capsule)',
          borderRadius: 'var(--zh-radius12)',
          borderColor: 'var(--zh-line-border)',
        }"
      >
        <template v-if="isLoading">
          <!-- 骨架屏占位 -->
          <div class="flex flex-col gap-3">
            <div class="skeleton-loader h-4 w-2/3"></div>
            <div class="skeleton-loader h-8 w-1/2"></div>
            <div class="skeleton-loader h-3 w-3/4"></div>
          </div>
        </template>

        <template v-else>
          <!-- 标题行 + 右上角图标 -->
          <div class="flex items-center justify-between mb-3">
            <span
              class="text-[13px]"
              style="color: var(--zh-text-caption);"
            >
              {{ card.title }}
            </span>
            <component
              :is="card.icon"
              class="w-6 h-6"
              style="color: var(--zh-text-caption);"
            />
          </div>

          <!-- 主数据行 -->
          <div class="flex items-baseline gap-2 mb-2">
            <span
              class="text-[30px] font-bold leading-tight"
              style="
                font-family: var(--zh-font-number);
                color: var(--zh-text-primary);
              "
            >
              {{ card.mainValue }}
            </span>
            <span
              class="flex items-center gap-0.5 text-xs font-medium"
              :style="{ color: card.trendColor }"
            >
              <component :is="card.trendUp ? ArrowUp : ArrowDown" class="w-3.5 h-3.5" />
              {{ card.trendLabel }}
            </span>
          </div>

          <!-- 辅助说明行 -->
          <div class="flex items-center gap-2">
            <!-- 状态指示灯（卡片 2 和 4） -->
            <span
              v-if="card.hasStatusDot"
              class="inline-block w-2 h-2 rounded-full animate-pulse"
              :style="{ background: card.statusColor }"
            ></span>
            <span
              class="text-[11px]"
              style="color: var(--zh-text-disabled);"
            >
              {{ card.subText }}
            </span>
            <span
              v-if="card.hasStatusDot"
              class="text-[11px] font-medium"
              :style="{ color: card.statusColor }"
            >
              {{ card.statusLabel }}
            </span>
          </div>

          <!-- 详情说明行 -->
          <div class="mt-1">
            <span
              class="text-[11px]"
              style="color: var(--zh-text-disabled);"
            >
              {{ card.breakdown }}
            </span>
          </div>
        </template>
      </el-card>
    </div>

    <!-- ===================================================================
         2. 中部主要工作区 — 左侧 8 栏 + 右侧 4 栏
         =================================================================== -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-5">

      <!-- ===== 左侧 8 栏：近期内容审核队列 ===== -->
      <div class="lg:col-span-8">
        <el-card
          shadow="never"
          :style="{
            background: 'var(--zh-background-capsule)',
            borderRadius: 'var(--zh-radius12)',
            borderColor: 'var(--zh-line-border)',
          }"
        >
          <!-- 标题栏 -->
          <template #header>
            <div class="flex items-center justify-between">
              <span
                class="text-base font-semibold"
                style="color: var(--zh-text-primary);"
              >
                近期内容审核队列
              </span>
              <!-- 时间范围筛选 -->
              <el-radio-group
                v-model="timeRange"
                size="small"
              >
                <el-radio-button value="today">今日</el-radio-button>
                <el-radio-button value="week">本周</el-radio-button>
                <el-radio-button value="month">本月</el-radio-button>
              </el-radio-group>
            </div>
          </template>

          <!-- 列表区域 -->
          <template v-if="isLoading">
            <!-- 骨架屏 -->
            <div
              v-for="n in 4"
              :key="'skeleton-' + n"
              class="flex items-center gap-3 py-3 border-b"
              style="border-color: var(--zh-line-parting);"
            >
              <div class="skeleton-loader w-10 h-10 rounded-md flex-shrink-0"></div>
              <div class="flex-1 flex flex-col gap-2">
                <div class="skeleton-loader h-4 w-3/4"></div>
                <div class="skeleton-loader h-3 w-1/3"></div>
              </div>
              <div class="skeleton-loader h-6 w-14 rounded-full"></div>
            </div>
          </template>

          <template v-else>
            <!-- 审核列表项 -->
            <div
              v-for="(item, index) in auditQueue"
              :key="item.id"
              class="flex items-center gap-3 py-3 transition-colors duration-150 audit-list-item"
              :class="{ 'border-b': index < auditQueue.length - 1 }"
              :style="{
                borderColor: 'var(--zh-line-parting)',
              }"
            >
              <!-- 内容缩略图 -->
              <div
                class="w-10 h-10 rounded-md flex items-center justify-center flex-shrink-0 text-lg"
                style="background: var(--zh-background-light-gray);"
              >
                {{ getThumbnailIcon(item.thumbnailType) }}
              </div>

              <!-- 标题 + 提交者信息 -->
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-1">
                  <span
                    class="text-sm font-medium truncate"
                    style="color: var(--zh-text-primary);"
                  >
                    {{ item.title }}
                  </span>
                  <span
                    class="text-[11px] px-1.5 py-0.5 rounded flex-shrink-0"
                    style="
                      background: var(--zh-background-tag);
                      color: var(--zh-text-caption);
                    "
                  >
                    {{ item.type }}
                  </span>
                </div>
                <div class="flex items-center gap-2">
                  <!-- 提交者头像 -->
                  <el-avatar
                    :size="20"
                    :style="{ background: 'var(--zh-gradient-blue)', fontSize: '10px' }"
                  >
                    {{ item.submitter.name.charAt(0) }}
                  </el-avatar>
                  <span
                    class="text-xs"
                    style="color: var(--zh-text-caption);"
                  >
                    {{ item.submitter.name }}
                  </span>
                  <span
                    class="text-[11px]"
                    style="color: var(--zh-text-disabled);"
                  >
                    · {{ item.time }}
                  </span>
                </div>
              </div>

              <!-- 状态标签 -->
              <el-tag
                :type="getTagType(item.status)"
                size="small"
                class="flex-shrink-0"
              >
                {{ item.statusLabel }}
              </el-tag>

              <!-- 操作按钮 -->
              <el-button
                type="primary"
                link
                size="small"
                class="flex-shrink-0"
              >
                审核
              </el-button>
            </div>
          </template>

          <!-- 底部状态栏 -->
          <div
            v-if="!isLoading"
            class="flex items-center justify-between mt-3 pt-3 border-t"
            style="border-color: var(--zh-line-parting);"
          >
            <span
              class="text-xs"
              style="color: var(--zh-text-caption);"
            >
              共 {{ totalPending }} 条待审核内容
            </span>
            <a
              href="javascript:void(0)"
              class="text-xs font-medium hover:underline"
              style="color: var(--zh-text-link);"
            >
              查看全部 →
            </a>
          </div>
        </el-card>
      </div>

      <!-- ===== 右侧 4 栏：快捷操作 + 系统告警 ===== -->
      <div class="lg:col-span-4 flex flex-col gap-5">

        <!-- 模块 1：快捷操作 -->
        <el-card
          shadow="never"
          :style="{
            background: 'var(--zh-background-capsule)',
            borderRadius: 'var(--zh-radius12)',
            borderColor: 'var(--zh-line-border)',
          }"
        >
          <template #header>
            <span
              class="text-[15px] font-semibold"
              style="color: var(--zh-text-primary);"
            >
              快捷操作
            </span>
          </template>

          <template v-if="isLoading">
            <div
              v-for="n in 5"
              :key="'action-skeleton-' + n"
              class="skeleton-loader h-10 w-full rounded-lg mb-2.5"
            ></div>
          </template>

          <template v-else>
            <div class="flex flex-col gap-2.5">
              <el-button
                v-for="action in quickActions"
                :key="action.action"
                size="default"
                class="quick-action-btn w-full !justify-start !h-10"
                :style="{
                  borderRadius: 'var(--zh-radius8)',
                }"
              >
                <component :is="action.icon" class="w-4 h-4 mr-2" />
                {{ action.label }}
              </el-button>
            </div>
          </template>
        </el-card>

        <!-- 模块 2：需要关注（系统告警） -->
        <el-card
          shadow="never"
          :style="{
            background: 'var(--zh-background-capsule)',
            borderRadius: 'var(--zh-radius12)',
            borderColor: 'var(--zh-line-border)',
          }"
        >
          <template #header>
            <div class="flex items-center gap-2">
              <span
                class="text-[15px] font-semibold"
                style="color: var(--zh-text-primary);"
              >
                需要关注
              </span>
              <!-- 未处理告警红点 -->
              <span
                class="inline-block w-2 h-2 rounded-full animate-pulse"
                style="background: var(--zh-red);"
              ></span>
            </div>
          </template>

          <template v-if="isLoading">
            <div
              v-for="n in 4"
              :key="'alert-skeleton-' + n"
              class="flex items-start gap-2 py-2 border-b last:border-0"
              style="border-color: var(--zh-line-parting);"
            >
              <div class="skeleton-loader w-2 h-2 rounded-full mt-1.5 flex-shrink-0"></div>
              <div class="flex-1 flex flex-col gap-1.5">
                <div class="skeleton-loader h-3.5 w-full"></div>
                <div class="skeleton-loader h-2.5 w-1/2"></div>
              </div>
            </div>
          </template>

          <template v-else>
            <div
              v-for="(alert, index) in alerts"
              :key="alert.id"
              class="flex items-start gap-2 py-2 cursor-pointer transition-colors duration-150 alert-item"
              :class="{ 'border-b': index < alerts.length - 1 }"
              :style="{ borderColor: 'var(--zh-line-parting)' }"
            >
              <!-- 严重度指示点 -->
              <span
                class="inline-block w-2 h-2 rounded-full mt-1.5 flex-shrink-0"
                :style="{ background: alert.severityColor }"
              ></span>

              <!-- 告警内容 -->
              <div class="flex-1 min-w-0">
                <p
                  class="text-[13px] font-medium leading-5 truncate"
                  style="color: var(--zh-text-primary);"
                >
                  {{ alert.title }}
                </p>
                <p
                  class="text-[11px] leading-4 truncate mt-0.5"
                  style="color: var(--zh-text-caption);"
                >
                  {{ alert.detail }}
                </p>
                <span
                  class="text-[11px]"
                  style="color: var(--zh-text-disabled);"
                >
                  {{ alert.time }}
                </span>
              </div>
            </div>
          </template>
        </el-card>

      </div>
    </div>
  </div>
</template>

<style scoped>
/* ===== KPI 卡片悬浮态 ===== */
.kpi-card {
  transition: box-shadow 200ms cubic-bezier(0.4, 0, 0.2, 1),
              transform 200ms cubic-bezier(0.4, 0, 0.2, 1),
              border-color 200ms cubic-bezier(0.4, 0, 0.2, 1);
}
.kpi-card:hover {
  box-shadow: var(--zh-shadow2) !important;
  transform: translateY(-2px);
  border-color: var(--zh-line-heavier) !important;
}

/* ===== 审核队列列表项悬浮态 ===== */
.audit-list-item:hover {
  background: var(--zh-background-option);
}

/* ===== 快捷操作按钮悬浮态 ===== */
.quick-action-btn:hover {
  background: var(--zh-background-option) !important;
  color: var(--zh-text-theme) !important;
  border-color: var(--zh-line-heavier) !important;
}
.quick-action-btn:hover :deep(svg) {
  color: var(--zh-text-theme);
}

/* ===== 告警条目悬浮态 ===== */
.alert-item:hover {
  background: var(--zh-background-option);
  border-radius: var(--zh-radius6);
}

/* ===== 骨架屏脉冲 ===== */
.skeleton-pulse .skeleton-loader {
  animation: shimmer 1.5s infinite;
}
</style>
