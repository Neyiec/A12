<!--
  [数据交互说明]
  - 导入:
    - ElementPlus 组件: ElCard、ElTag、ElButton、ElAvatar、ElRadioGroup、ElRadioButton、ElMessage、ElEmpty（全局注册）
    - ElementPlus Icons: 用于 KPI 卡片图标、趋势箭头和快捷操作按钮图标
    - `@/apis/config`: getDashboard（API-107 看板聚合）、listAlerts（API-108 派生式告警）
    - `@/apis/moderation`: getModerationTasks（API-90 审核队列，与 ContentAudit 同源封装）
    - `vue-router`: useRouter（快捷操作跳转 / 队列跳转审核页）
  - 依赖:
    - 三区数据并行拉取，Promise.allSettled 分区降级（看板跨 dashboard:view 与 audit:view 两个权限域）
    - （预留）acknowledgeAlert / resolveAlert 已在 apis/config.js 封装，供后续告警处置交互接入
  - 输入: 无 props；AdminHeader 刷新按钮广播的 admin-refresh 全局事件触发重拉
  - 输出: 四区视图（KPI 卡片 / 审核队列 / 快捷操作 / 需要关注）；
    快捷操作路由跳转（/main/users、/main/resources、/main/settings），队列跳转 /main/audit
  - 监听: `admin-refresh` 自定义事件（从 AdminHeader 刷新按钮发出），触发数据重新加载
-->
<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
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
import { getDashboard, listAlerts } from '@/apis/config'
import { getModerationTasks } from '@/apis/moderation'

// ========== 路由 ==========

const router = useRouter()

// ========== 配置常量 ==========

/** 内容类型 → 显示标签（com_content.content_type：skill/lesson_case，兼容历史 case 值） */
const CONTENT_TYPE_LABEL_MAP = { skill: 'Skill', lesson_case: '教学案例', case: '教学案例' }

/** 队列时间范围 → 向前追溯天数（前端本地过滤，API-90 无时间参数） */
const TIME_RANGE_DAYS = { today: 1, week: 7, month: 30 }

/** 告警 level → 颜色变量映射 */
const ALERT_COLOR_MAP = {
  danger: 'var(--zh-red)',
  warning: 'var(--zh-orange)',
  info: 'var(--zh-cyan)',
}

// ========== 响应式数据 ==========

/** 数据加载状态（骨架屏） */
const isLoading = ref(true)

/** 当前时间筛选范围（审核队列，前端本地过滤） */
const timeRange = ref('today')

/** 看板聚合 payload —— API-107（totals 字段平铺在 payload 根级） */
const dashboardTotals = ref({})
const dashboardToday = ref({})
const dashboardTrend = ref([])
const dashboardQuality = ref({})

/** 各分区加载成功标记（Promise.allSettled 分区降级：单区失败不影响其余区渲染） */
const dashboardLoaded = ref(false)
const queueLoaded = ref(false)
const alertsLoaded = ref(false)

/** 审核队列原始行（AuditVO 富化字段：content_title / submitter_name / created_at） */
const auditQueue = ref([])

/** 审核队列接口 total（看板聚合加载成功后被同源 moderation_pending_count 覆盖） */
const queueTotal = ref(0)

/** 系统告警列表（API-108 派生式告警，恒为 open 状态） */
const alerts = ref([])

/** 快捷操作按钮列表：三个可跳转页 + 两个占位（无端点/页面） */
const quickActions = [
  { label: '发布平台公告', icon: EditPen, action: 'announcement' },
  { label: '添加管理员', icon: UserFilled, action: 'addAdmin' },
  { label: '上传公共资源', icon: Upload, action: 'uploadResource' },
  { label: '导出运营报表', icon: Download, action: 'exportReport' },
  { label: '系统参数配置', icon: Setting, action: 'systemConfig' },
]

// ========== 计算属性 ==========

/**
 * KPI 四卡数据 —— 由看板聚合 payload 逐卡映射（每卡独立构建函数，见 3② 字段对照）
 */
const kpiCards = computed(() => {
  const totals = dashboardTotals.value
  return [
    buildModerationCard(totals),
    buildUserCard(totals, dashboardToday.value),
    buildResourceCard(totals, dashboardTrend.value),
    buildHealthCard(dashboardQuality.value),
  ]
})

/**
 * 总待审核数：优先取看板聚合的 moderation_pending_count（同源免二次请求），回退队列接口 total
 */
const totalPending = computed(() => {
  const count = dashboardTotals.value.moderation_pending_count
  if (dashboardLoaded.value && count != null) return count
  return queueTotal.value
})

/**
 * 审核队列按时间范围本地过滤
 * API-90 无时间参数（已知缺口）；pending 积压超过所选时段时滤空，展示空态提示
 */
const filteredAuditQueue = computed(() => {
  const days = TIME_RANGE_DAYS[timeRange.value] ?? 1
  const start = Date.now() - days * 24 * 60 * 60 * 1000
  return auditQueue.value.filter((item) => {
    const t = item.createdAt ? new Date(item.createdAt).getTime() : 0
    return t >= start
  })
})

// ========== 方法 ==========

/**
 * 卡 1 待审核内容：总量 = moderation_pending_count，明细 = 审核/举报 pending 拆分
 * 无昨日积压对比数据源（today 桶无 new_audit_count），趋势箭头隐藏
 */
const buildModerationCard = (totals) => ({
  id: 1,
  title: '待审核内容',
  icon: Checked,
  mainValue: String(totals.moderation_pending_count ?? 0),
  showArrow: false,
  trendLabel: '',
  trendColor: 'var(--zh-red)',
  subText: `内容审核 ${totals.review_pending_count ?? 0} 条 · 举报 ${totals.report_pending_count ?? 0} 条`,
  breakdown: '点击「查看全部」前往审核页处置',
})

/**
 * 卡 2 活跃教师数：总量 = user_count（有效用户），趋势 = 今日新增注册
 * mock 的「实时在线」无会话数据源，已按设计移除
 */
const buildUserCard = (totals, today) => ({
  id: 2,
  title: '活跃教师数',
  icon: UserFilled,
  mainValue: String(totals.user_count ?? 0),
  showArrow: true,
  trendUp: true,
  trendLabel: `+${today.new_user_count ?? 0}`,
  trendColor: 'var(--zh-green)',
  subText: '较昨日新增注册',
  breakdown: `有效用户共 ${totals.user_count ?? 0} 人`,
})

/**
 * 卡 3 知识库条目：总量 = resource_count（个人素材 + 平台资源），
 * 趋势 = 近 7 日末两天差值，明细 = 7 日累计新增
 */
const buildResourceCard = (totals, trend) => {
  const last = trend[trend.length - 1] || {}
  const prev = trend[trend.length - 2] || {}
  const delta = (last.new_resources ?? 0) - (prev.new_resources ?? 0)
  const weekNew = trend.reduce((sum, row) => sum + (row.new_resources ?? 0), 0)
  return {
    id: 3,
    title: '知识库条目',
    icon: FolderOpened,
    mainValue: String(totals.resource_count ?? 0),
    showArrow: true,
    trendUp: delta >= 0,
    trendLabel: delta > 0 ? `+${delta}` : delta < 0 ? String(delta) : '持平',
    trendColor: delta >= 0 ? 'var(--zh-green)' : 'var(--zh-red)',
    subText: `个人素材 ${totals.personal_resource_count ?? 0} · 平台资源 ${totals.platform_resource_count ?? 0}`,
    breakdown: `近 7 日新增 ${weekNew} 条`,
  }
}

/**
 * 卡 4 系统健康度：主值 = AI 任务成功率，状态灯由 AI/导出失败数推导
 * mock 的 CPU/内存/磁盘无采集端点，已按设计移除
 */
const buildHealthCard = (quality) => {
  const aiRate = Number(quality.ai_task_success_rate ?? 0)
  const exportRate = Number(quality.export_success_rate ?? 0)
  const aiFailed = Number(quality.ai_task_failed_count ?? 0)
  const exportFailed = Number(quality.export_failed_count ?? 0)
  const healthy = aiFailed === 0 && exportFailed === 0
  return {
    id: 4,
    title: '系统健康度',
    icon: Monitor,
    mainValue: `${aiRate}%`,
    showArrow: false,
    trendLabel: healthy ? '正常' : '存在失败',
    trendColor: healthy ? 'var(--zh-green)' : 'var(--zh-red)',
    subText: `AI 任务成功率 ${aiRate}% · 导出成功率 ${exportRate}%`,
    breakdown: `AI 失败 ${aiFailed} 项 · 导出失败 ${exportFailed} 项`,
    hasStatusDot: true,
    statusColor: healthy ? 'var(--zh-green)' : 'var(--zh-red)',
    statusLabel: healthy ? '运行正常' : '需要关注',
  }
}

/**
 * 拉取看板聚合数据（API-107）并拆分到各响应式状态
 */
const loadDashboard = async () => {
  const res = await getDashboard()
  const data = res?.data || {}
  dashboardTotals.value = data
  dashboardToday.value = data.today || {}
  dashboardTrend.value = data.trend_7d || []
  dashboardQuality.value = data.quality || {}
}

/**
 * 拉取近期审核队列（API-90 复用 moderation.js 封装）并映射为队列行
 * AuditVO 富化字段缺失（关联内容已删除）时回退显示裸 target_id
 */
const loadModerationQueue = async () => {
  const res = await getModerationTasks({ status: 'pending', page: 1, size: 5 })
  const records = res?.data?.records || []
  queueTotal.value = res?.data?.total ?? records.length
  auditQueue.value = records.map((row) => ({
    id: row.id,
    thumbnailType: 'doc',
    title: row.content_title || `待审内容 #${row.target_id}`,
    type: CONTENT_TYPE_LABEL_MAP[row.target_type] || row.target_type || '内容',
    submitter: { name: row.submitter_name || '未知用户', avatar: '' },
    time: formatRelativeTime(row.created_at),
    createdAt: row.created_at,
    status: 'warning',
    statusLabel: '待审',
  }))
}

/**
 * 拉取派生式告警（API-108，status 仅支持 open）
 */
const loadAlerts = async () => {
  const res = await listAlerts({ status: 'open', page: 1, size: 4 })
  const records = res?.data?.records || []
  alerts.value = records.map((row) => ({
    id: row.id,
    severity: row.level,
    severityColor: ALERT_COLOR_MAP[row.level] || 'var(--zh-cyan)',
    title: row.title,
    detail: row.detail,
    time: formatRelativeTime(row.created_at),
  }))
}

/**
 * 全量加载数据 —— 三区并行 + Promise.allSettled 分区降级
 * 看板横跨 dashboard:view 与 audit:view 两个权限域，单区 403/失败不影响其余区渲染
 */
const loadData = async () => {
  isLoading.value = true
  const [dashRes, queueRes, alertRes] = await Promise.allSettled([
    loadDashboard(),
    loadModerationQueue(),
    loadAlerts(),
  ])
  dashboardLoaded.value = dashRes.status === 'fulfilled'
  queueLoaded.value = queueRes.status === 'fulfilled'
  alertsLoaded.value = alertRes.status === 'fulfilled'
  if (!dashboardLoaded.value) ElMessage.error('看板数据加载失败，请稍后重试')
  if (!queueLoaded.value) ElMessage.warning('审核队列加载失败（可能缺少 audit:view 权限）')
  if (!alertsLoaded.value) ElMessage.warning('告警加载失败（可能缺少 dashboard:view 权限）')
  isLoading.value = false
}

/**
 * 处理刷新 — 由 Header 的刷新按钮触发（admin-refresh 全局事件）
 */
const handleRefresh = () => {
  loadData()
}

/**
 * 快捷操作分流：三个可跳转页 + 两个占位（提示文案明示，不静默失效）
 * 与用户端「生成 PPT」按钮同构：看板只做页面级跳转，不代目标页拉数据
 */
const handleQuickAction = (action) => {
  const routeTargets = {
    addAdmin: '/main/users',
    uploadResource: '/main/resources',
    systemConfig: '/main/settings',
  }
  const path = routeTargets[action]
  if (path) {
    router.push(path)
    return
  }
  ElMessage.info(action === 'exportReport' ? '「导出运营报表」功能建设中，敬请期待' : '「发布平台公告」功能建设中，敬请期待')
}

/**
 * 跳转内容审核页（队列行「审核」按钮 / 底部「查看全部」共用）
 */
const goAuditPage = () => {
  router.push('/main/audit')
}

/**
 * 相对时间格式化（created_at ISO 字符串 → 「N 分钟前」样式）
 */
const formatRelativeTime = (value) => {
  if (!value) return ''
  const diff = Date.now() - new Date(value).getTime()
  if (Number.isNaN(diff)) return ''
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes} 分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} 小时前`
  return `${Math.floor(hours / 24)} 天前`
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
        class="kpi-card"
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
            <!-- 趋势箭头（仅有方向数据源的卡片显示） -->
            <span
              v-if="card.showArrow"
              class="flex items-center gap-0.5 text-xs font-medium"
              :style="{ color: card.trendColor }"
            >
              <component :is="card.trendUp ? ArrowUp : ArrowDown" class="w-3.5 h-3.5" />
              {{ card.trendLabel }}
            </span>
            <!-- 无方向趋势时仅显示文字标签（如「正常」「持平」） -->
            <span
              v-else-if="card.trendLabel"
              class="text-xs font-medium"
              :style="{ color: card.trendColor }"
            >
              {{ card.trendLabel }}
            </span>
          </div>

          <!-- 辅助说明行 -->
          <div class="flex items-center gap-2">
            <!-- 状态指示灯（系统健康度卡） -->
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
              <!-- 时间范围筛选（前端本地过滤） -->
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
            <!-- 审核列表项（timeRange 本地过滤后） -->
            <div
              v-for="(item, index) in filteredAuditQueue"
              :key="item.id"
              class="flex items-center gap-3 py-3 transition-colors duration-150 audit-list-item"
              :class="{ 'border-b': index < filteredAuditQueue.length - 1 }"
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

              <!-- 状态标签（队列恒为 pending → 待审） -->
              <el-tag
                type="warning"
                size="small"
                class="flex-shrink-0"
              >
                {{ item.statusLabel }}
              </el-tag>

              <!-- 操作按钮：跳转审核页处置 -->
              <el-button
                type="primary"
                link
                size="small"
                class="flex-shrink-0"
                @click="goAuditPage"
              >
                审核
              </el-button>
            </div>

            <!-- 空态：时段内无待审内容，或队列分区加载失败（权限/网络） -->
            <el-empty
              v-if="filteredAuditQueue.length === 0"
              :description="queueLoaded ? '暂无该时段待审内容' : '审核队列加载失败（可能缺少 audit:view 权限）'"
              :image-size="60"
            />
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
              @click="goAuditPage"
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
                @click="handleQuickAction(action.action)"
              >
                <component :is="action.icon" class="w-4 h-4 mr-2" />
                {{ action.label }}
              </el-button>
            </div>
          </template>
        </el-card>

        <!-- 模块 2：需要关注（系统告警，派生式） -->
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
              class="flex items-start gap-2 py-2 transition-colors duration-150 alert-item"
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

            <!-- 空态：无待处理告警，或告警分区加载失败 -->
            <el-empty
              v-if="alerts.length === 0"
              :description="alertsLoaded ? '暂无待处理告警' : '告警加载失败（可能缺少 dashboard:view 权限）'"
              :image-size="60"
            />
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
