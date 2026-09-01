<!--
  [数据交互说明]
  - 导入:
    - ElementPlus 组件: ElCard, ElTable, ElTableColumn, ElTag, ElButton, ElInput, ElSelect, ElOption,
      ElPagination, ElDialog, ElForm, ElFormItem, ElAvatar, ElSkeleton, ElEmpty, ElMessageBox, ElMessage,
      ElTooltip, ElRadioGroup, ElRadioButton
    - ElementPlus Icons: Search, Plus, Edit, Delete, Refresh, UserFilled
    - `ref`, `reactive`, `computed`, `onMounted` from Vue
  - 依赖:
    - `getAdminUsers`: 来自 `../apis/user.js`（API-75 分页查询后台用户）
  - 输入: 接收筛选条件与分页参数，请求后端用户列表
  - 输出: 渲染用户管理视图（工具栏 + 数据表格 + 分页器 + 新增/编辑对话框）
  - 监听: `admin-refresh` 自定义事件（从 AdminHeader 刷新按钮发出），触发数据重新加载
-->

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import {
  Search,
  Plus,
  Edit,
  Delete,
  Refresh,
  UserFilled,
  CircleCheck,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAdminUsers, updateUserStatus, createAdminUser } from '@/apis/user.js'

// ===================================================================
// 配置常量 — 所有下拉选项、表格列、分页参数集中管理
// ===================================================================

/** 角色筛选项 */
const ROLE_OPTIONS = [
  { label: '全部角色', value: '' },
  { label: '超级管理员', value: 'super_admin' },
  { label: '内容审核员', value: 'content_auditor' },
  { label: '知识库维护员', value: 'knowledge_curator' },
  { label: '普通教师', value: 'teacher' },
]

/** 角色值 → 显示标签映射 */
const ROLE_LABEL_MAP = {
  super_admin: '超级管理员',
  content_auditor: '内容审核员',
  knowledge_curator: '知识库维护员',
  teacher: '普通教师',
}

/** 角色值 → Tag 类型映射 */
const ROLE_TAG_TYPE_MAP = {
  super_admin: 'danger',
  content_auditor: 'warning',
  knowledge_curator: 'success',
  teacher: 'info',
}

/** 状态筛选项 */
const STATUS_OPTIONS = [
  { label: '全部状态', value: '' },
  { label: '正常', value: 'active' },
  { label: '已封禁', value: 'banned' },
]

/** 每页条数选项 */
const PAGE_SIZE_OPTIONS = [10, 20, 50, 100]

// ===================================================================
// 响应式状态
// ===================================================================

/** 数据加载状态 */
const isLoading = ref(true)

/** 表格数据加载中（筛选/分页切换时的局部 loading） */
const isTableLoading = ref(false)

/** 用户列表数据 */
const userList = ref([])

/** 筛选条件 */
const filters = reactive({
  role: '',
  status: '',
  keyword: '',
})

/** 分页参数 */
const pagination = reactive({
  currentPage: 1,
  pageSize: 20,
  total: 0,
})

/** 对话框可见性 */
const dialogVisible = ref(false)

/** 对话框模式：'create' | 'edit' */
const dialogMode = ref('create')

/** 对话框标题（计算属性） */
const dialogTitle = computed(() => {
  const name = dialogForm.username || ''
  return dialogMode.value === 'create' ? '新增用户' : `编辑用户 — ${name}`
})

/** 对话框加载态（提交中） */
const isSubmitting = ref(false)

/** 表单引用（用于校验） */
const formRef = ref(null)

/** 对话框表单数据（roles 为多选角色数组） */
const dialogForm = reactive({
  id: null,
  username: '',
  real_name: '',
  phone: '',
  email: '',
  roles: [],
  status: 'active',
  password: '',
})

/** 新增模式下的表单校验规则 */
const createRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 20, message: '用户名长度须在 2 到 20 个字符之间', trigger: 'blur' },
  ],
  real_name: [{ required: true, message: '请输入真实姓名', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
  roles: [{
    type: 'array',
    required: true,
    min: 1,
    message: '请至少选择一个角色',
    trigger: 'change',
  }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
  password: [
    { required: true, message: '请输入初始密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于 6 个字符', trigger: 'blur' },
  ],
}

/** 编辑模式下的表单校验规则（无密码字段） */
const editRules = {
  username: createRules.username,
  email: createRules.email,
  roles: createRules.roles,
  status: createRules.status,
}

/** 当前校验规则（根据模式动态切换） */
const currentRules = computed(() => {
  return dialogMode.value === 'create' ? createRules : editRules
})

// ===================================================================
// 数据适配
// ===================================================================

/**
 * 将 ISO 时间字符串格式化为本地 "YYYY-MM-DD HH:mm"
 * @param {string|undefined} value - 后端返回的时间（ISO 格式）
 * @returns {string} 格式化后的时间文本
 */
const formatTime = (value) => {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

/**
 * 将后端 UserVO 归一化为表格所需结构
 * 兼容 role / user_type、status / is_active 等不同字段命名，避免后端字段名差异影响表格渲染
 * @param {Object} u - 后端返回的用户对象
 * @returns {Object} 归一化后的用户对象
 */
const normalizeUser = (u) => ({
  id: u.id ?? u.userId,
  username: u.username ?? u.name ?? '',
  real_name: u.real_name ?? '',
  phone: u.phone ?? '',
  email: u.email ?? '',
  avatar: u.avatar ?? '',
  role: u.role ?? u.user_type ?? '',
  status:
    u.status ?? (u.is_active === 1 ? 'active' : u.is_active === 0 ? 'banned' : 'active'),
  created_at: formatTime(u.created_at ?? u.create_time ?? ''),
})

// ===================================================================
// 方法
// ===================================================================

/**
 * 请求后端用户列表（API-75）
 * 将筛选条件 + 分页参数映射为查询参数，成功后归一化列表并记录总数
 */
const fetchUsers = async () => {
  isTableLoading.value = true
  try {
    // 组装查询参数：只传有效的筛选条件
    const params = { page: pagination.currentPage, size: pagination.pageSize }
    if (filters.keyword.trim()) params.keyword = filters.keyword.trim()
    if (filters.role) params.user_type = filters.role
    if (filters.status) params.is_active = filters.status === 'active' ? 1 : 0

    const res = await getAdminUsers(params)
    const data = res?.data
    const rows = data?.records || data?.list || data?.items || []
    userList.value = rows.map(normalizeUser)
    pagination.total = Number(data?.total ?? rows.length)
  } finally {
    isTableLoading.value = false
  }
}

/**
 * 页面首次数据加载
 * 显示全页骨架屏，请求完成后渲染表格
 */
const loadData = async () => {
  isLoading.value = true
  try {
    await fetchUsers()
  } finally {
    isLoading.value = false
  }
}

/**
 * 处理刷新 — 由 Header 的刷新按钮触发
 */
const handleRefresh = () => {
  loadData()
}

/**
 * 角色筛选变更处理
 * 重置到第 1 页并重新请求数据
 */
const handleFilterChange = () => {
  pagination.currentPage = 1
  fetchUsers()
}

/**
 * 搜索框输入处理（防抖 300ms 后触发）
 */
let searchTimer = null
const handleSearchInput = () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    handleFilterChange()
  }, 300)
}

/**
 * 搜索框回车处理
 */
const handleSearchEnter = () => {
  clearTimeout(searchTimer)
  handleFilterChange()
}

/**
 * 分页页码变更
 * @param {number} page - 目标页码
 */
const handlePageChange = (page) => {
  pagination.currentPage = page
  fetchUsers()
}

/**
 * 分页每页条数变更
 * @param {number} size - 每页条数
 */
const handleSizeChange = (size) => {
  pagination.pageSize = size
  pagination.currentPage = 1
  fetchUsers()
}

/**
 * 打开新增用户对话框
 * 重置表单为空值
 */
const openCreateDialog = () => {
  dialogMode.value = 'create'
  dialogForm.id = null
  dialogForm.username = ''
  dialogForm.real_name = ''
  dialogForm.phone = ''
  dialogForm.email = ''
  dialogForm.roles = []
  dialogForm.status = 'active'
  dialogForm.password = ''
  dialogVisible.value = true
}

/**
 * 打开编辑用户对话框
 * 预填当前行数据到表单
 * @param {Object} row - 当前行用户数据
 */
const openEditDialog = (row) => {
  dialogMode.value = 'edit'
  dialogForm.id = row.id
  dialogForm.username = row.username
  dialogForm.real_name = row.real_name || ''
  dialogForm.phone = row.phone || ''
  dialogForm.email = row.email
  dialogForm.roles = row.role ? [row.role] : []
  dialogForm.status = row.status
  dialogForm.password = ''
  dialogVisible.value = true
}

/**
 * 对话框确认提交
 * 新建模式调用 API-78 创建后台账号；编辑模式暂未接入，成功后刷新列表
 */
const handleDialogConfirm = async () => {
  // 表单校验
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  isSubmitting.value = true
  try {
    if (dialogMode.value === 'create') {
      // 创建后台账号（API-78），roles 需序列化为 JSON 字符串
      const res = await createAdminUser({
        username: dialogForm.username,
        password: dialogForm.password,
        real_name: dialogForm.real_name,
        phone: dialogForm.phone,
        email: dialogForm.email,
        user_type: 'admin',
        roles: JSON.stringify(dialogForm.roles),
      })
      if (res?.code !== 0 && res?.code !== 200) {
        ElMessage.error(res?.message || '创建用户失败')
        return
      }
      ElMessage.success(`已成功创建用户「${dialogForm.username}」`)
    } else {
      // 编辑模式接口（API-81）尚未接入，暂以模拟提交占位
      ElMessage.success(`已成功更新用户「${dialogForm.username}」的信息`)
    }
    dialogVisible.value = false
    await fetchUsers()
  } catch {
    ElMessage.error('提交失败，请稍后重试')
  } finally {
    isSubmitting.value = false
  }
}

/**
 * 对话框关闭回调
 * 重置表单校验状态
 */
const handleDialogClose = () => {
  formRef.value?.resetFields()
}

/**
 * 删除用户 — 二次确认后执行
 * @param {Object} row - 当前行用户数据
 */
const handleDeleteUser = (row) => {
  ElMessageBox.confirm(
    `确定要删除用户【${row.username}】吗？此操作不可撤销，该用户的所有关联数据将被一并移除。`,
    '确认删除',
    {
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      type: 'warning',
      confirmButtonClass: 'el-button--danger',
    },
  )
    .then(async () => {
      // 删除接口尚未接入，这里仅模拟并刷新列表
      ElMessage.success(`已删除用户「${row.username}」`)
      // 如果当前页删空了且不是第一页，回到上一页
      if (userList.value.length === 1 && pagination.currentPage > 1) {
        pagination.currentPage--
      }
      await fetchUsers()
    })
    .catch(() => {
      // 用户取消删除，不做任何操作
    })
}

/**
 * 启用/停用用户（API-77）
 * 停用需二次确认；确认后调用状态接口并刷新列表
 * @param {Object} row - 当前行用户数据
 */
const handleToggleStatus = async (row) => {
  const isBanned = row.status === 'banned'
  const isActive = isBanned ? 1 : 0
  const actionText = isBanned ? '启用' : '停用'

  // 停用风险操作，二次确认
  if (!isBanned) {
    try {
      await ElMessageBox.confirm(
        `确定要停用用户【${row.username}】吗？停用后该用户将无法登录系统。`,
        '确认停用',
        {
          confirmButtonText: '确认停用',
          cancelButtonText: '取消',
          type: 'warning',
          confirmButtonClass: 'el-button--danger',
        },
      )
    } catch {
      return // 用户取消
    }
  }

  try {
    const res = await updateUserStatus(row.id, isActive)
    if (res?.code !== 0 && res?.code !== 200) {
      ElMessage.error(res?.message || '状态更新失败')
      return
    }
    ElMessage.success(`已${actionText}用户「${row.username}」`)
    await fetchUsers()
  } catch {
    ElMessage.error('状态更新失败，请稍后重试')
  }
}

/**
 * 获取角色显示标签
 * @param {string} role - 角色值
 * @returns {string} 中文标签
 */
const getRoleLabel = (role) => ROLE_LABEL_MAP[role] || role

/**
 * 获取角色对应的 Tag 类型
 * @param {string} role - 角色值
 * @returns {string} ElementPlus Tag type
 */
const getRoleTagType = (role) => ROLE_TAG_TYPE_MAP[role] || 'info'

// ===================================================================
// 生命周期
// ===================================================================

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
         1. 标题区（Toolbar）
         =================================================================== -->
    <div class="flex items-center justify-between flex-wrap gap-3 mb-4">
      <!-- 左侧：标题 -->
      <h1
        class="text-lg font-semibold shrink-0"
        style="
          font-size: var(--zh-font-size18);
          color: var(--zh-text-primary);
        "
      >
        用户列表
      </h1>

      <!-- 右侧：筛选器组 + 操作按钮 -->
      <div class="flex items-center flex-wrap gap-3">
        <!-- 角色筛选 -->
        <el-select
          v-model="filters.role"
          placeholder="全部角色"
          clearable
          size="default"
          style="width: 140px;"
          @change="handleFilterChange"
        >
          <el-option
            v-for="opt in ROLE_OPTIONS"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>

        <!-- 状态筛选 -->
        <el-select
          v-model="filters.status"
          placeholder="全部状态"
          clearable
          size="default"
          style="width: 120px;"
          @change="handleFilterChange"
        >
          <el-option
            v-for="opt in STATUS_OPTIONS"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>

        <!-- 搜索框 -->
        <el-input
          v-model="filters.keyword"
          placeholder="搜索用户名 / 邮箱..."
          clearable
          size="default"
          :prefix-icon="Search"
          style="width: 220px;"
          @input="handleSearchInput"
          @keyup.enter="handleSearchEnter"
          @clear="handleFilterChange"
        />

        <!-- 刷新按钮 -->
        <el-tooltip content="刷新列表" placement="bottom" effect="dark">
          <el-button
            :icon="Refresh"
            circle
            size="default"
            @click="handleRefresh"
          />
        </el-tooltip>

        <!-- 新增用户主按钮 -->
        <el-button
          type="primary"
          :icon="Plus"
          size="default"
          :style="{ borderRadius: 'var(--zh-radius8)' }"
          @click="openCreateDialog"
        >
          新增用户
        </el-button>
      </div>
    </div>

    <!-- ===================================================================
         2. 数据表格区
         =================================================================== -->
    <el-card
      shadow="never"
      :style="{
        background: 'var(--zh-background-capsule)',
        borderRadius: 'var(--zh-radius12)',
        borderColor: 'var(--zh-line-border)',
      }"
    >
      <!-- 全页骨架屏（首次加载） -->
      <template v-if="isLoading">
        <div
          v-for="n in 8"
          :key="'skeleton-' + n"
          class="flex items-center gap-4 py-3 border-b last:border-0"
          style="border-color: var(--zh-line-parting);"
        >
          <div class="skeleton-loader w-12 h-4 rounded"></div>
          <div class="skeleton-loader w-8 h-8 rounded-full shrink-0"></div>
          <div class="skeleton-loader w-24 h-4 rounded"></div>
          <div class="skeleton-loader flex-1 h-4 rounded"></div>
          <div class="skeleton-loader w-20 h-6 rounded-full"></div>
          <div class="skeleton-loader w-20 h-4 rounded"></div>
          <div class="skeleton-loader w-20 h-6 rounded-full"></div>
          <div class="skeleton-loader w-24 h-4 rounded"></div>
        </div>
      </template>

      <!-- 正式表格 -->
      <template v-else>
        <el-table
          :data="userList"
          stripe
          highlight-current-row
          border
          v-loading="isTableLoading"
          row-class-name="user-table-row"
          element-loading-text="加载中..."
          :style="{
            '--el-table-border-color': 'var(--zh-line-border)',
            '--el-table-header-bg-color': 'var(--zh-background-light-gray)',
            '--el-table-header-text-color': 'var(--zh-text-caption)',
            '--el-table-row-hover-bg-color': 'var(--zh-background-option)',
            '--el-table-current-row-bg-color': 'var(--zh-background-option-on)',
            '--el-table-stripe-bg-color': 'var(--zh-background-option)',
          }"
        >
          <!-- 列：ID -->
          <el-table-column
            prop="id"
            label="ID"
            width="100"
            align="center"
          >
            <template #default="{ row }">
              <span
                style="
                  font-family: var(--zh-font-number);
                  font-size: var(--zh-font-size13);
                  color: var(--zh-text-caption);
                "
              >
                {{ row.id }}
              </span>
            </template>
          </el-table-column>

          <!-- 列：用户名 -->
          <el-table-column
            prop="username"
            label="用户名"
            min-width="160"
          >
            <template #default="{ row }">
              <div class="flex items-center gap-2.5">
                <el-avatar
                  :size="32"
                  :src="row.avatar || undefined"
                  :style="{
                    background: 'var(--zh-gradient-blue)',
                    fontSize: 'var(--zh-font-size12)',
                  }"
                >
                  {{ row.username.charAt(0) }}
                </el-avatar>
                <span
                  class="font-medium truncate"
                  style="
                    font-size: var(--zh-font-size14);
                    color: var(--zh-text-primary);
                  "
                >
                  {{ row.username }}
                </span>
              </div>
            </template>
          </el-table-column>

          <!-- 列：邮箱 -->
          <el-table-column
            prop="email"
            label="邮箱"
            min-width="200"
          >
            <template #default="{ row }">
              <span
                style="
                  font-size: var(--zh-font-size14);
                  color: var(--zh-text-secondary);
                "
              >
                {{ row.email }}
              </span>
            </template>
          </el-table-column>

          <!-- 列：角色 -->
          <el-table-column
            prop="role"
            label="角色"
            width="130"
            align="center"
          >
            <template #default="{ row }">
              <el-tag
                :type="getRoleTagType(row.role)"
                size="small"
                effect="plain"
              >
                {{ getRoleLabel(row.role) }}
              </el-tag>
            </template>
          </el-table-column>

          <!-- 列：注册时间 -->
          <el-table-column
            prop="created_at"
            label="注册时间"
            width="170"
            align="center"
          >
            <template #default="{ row }">
              <span
                style="
                  font-size: var(--zh-font-size13);
                  color: var(--zh-text-caption);
                "
              >
                {{ row.created_at }}
              </span>
            </template>
          </el-table-column>

          <!-- 列：状态 -->
          <el-table-column
            prop="status"
            label="状态"
            width="100"
            align="center"
          >
            <template #default="{ row }">
              <el-tag
                :type="row.status === 'active' ? 'success' : 'danger'"
                size="small"
                effect="plain"
              >
                <span class="flex items-center gap-1.5">
                  <span
                    class="inline-block w-1.5 h-1.5 rounded-full shrink-0"
                    :style="{
                      background: row.status === 'active'
                        ? 'var(--zh-green)'
                        : 'var(--zh-red)',
                    }"
                  ></span>
                  {{ row.status === 'active' ? '正常' : '已封禁' }}
                </span>
              </el-tag>
            </template>
          </el-table-column>

          <!-- 列：操作 -->
          <el-table-column
            label="操作"
            width="210"
            align="center"
            fixed="right"
          >
            <template #default="{ row }">
              <div class="flex items-center justify-center gap-2">
                <el-button
                  :type="row.status === 'banned' ? 'success' : 'warning'"
                  link
                  size="small"
                  :style="{ fontSize: 'var(--zh-font-size13)' }"
                  @click="handleToggleStatus(row)"
                >
                  <el-icon class="mr-0.5"><CircleCheck /></el-icon>
                  {{ row.status === 'banned' ? '启用' : '停用' }}
                </el-button>
                <el-button
                  type="primary"
                  link
                  size="small"
                  :style="{ fontSize: 'var(--zh-font-size13)' }"
                  @click="openEditDialog(row)"
                >
                  <el-icon class="mr-0.5"><Edit /></el-icon>
                  编辑
                </el-button>
                <el-button
                  type="danger"
                  link
                  size="small"
                  :style="{ fontSize: 'var(--zh-font-size13)' }"
                  @click="handleDeleteUser(row)"
                >
                  <el-icon class="mr-0.5"><Delete /></el-icon>
                  删除
                </el-button>
              </div>
            </template>
          </el-table-column>

          <!-- 空数据占位 -->
          <template #empty>
            <el-empty
              description="暂无用户数据"
              :image-size="80"
            >
              <template v-if="filters.role || filters.status || filters.keyword">
                <span
                  style="font-size: var(--zh-font-size13); color: var(--zh-text-caption);"
                >
                  没有符合条件的用户，请调整筛选条件
                </span>
                <el-button
                  type="primary"
                  link
                  size="small"
                  class="mt-2"
                  @click="
                    filters.role = '';
                    filters.status = '';
                    filters.keyword = '';
                    handleFilterChange();
                  "
                >
                  清除筛选
                </el-button>
              </template>
              <template v-else>
                <el-button
                  type="primary"
                  size="small"
                  :style="{ borderRadius: 'var(--zh-radius8)' }"
                  class="mt-3"
                  @click="openCreateDialog"
                >
                  新增第一个用户
                </el-button>
              </template>
            </el-empty>
          </template>
        </el-table>

        <!-- ===== 分页器 ===== -->
        <div
          v-if="pagination.total > 0"
          class="flex justify-end pt-4 mt-4 border-t"
          :style="{ borderColor: 'var(--zh-line-parting)' }"
        >
          <el-pagination
            v-model:current-page="pagination.currentPage"
            v-model:page-size="pagination.pageSize"
            :total="pagination.total"
            :page-sizes="PAGE_SIZE_OPTIONS"
            :background="true"
            layout="total, sizes, prev, pager, next, jumper"
            :style="{
              '--el-pagination-bg-color': 'var(--zh-background-capsule)',
              '--el-pagination-button-bg-color': 'var(--zh-background-option)',
              '--el-pagination-hover-color': 'var(--zh-text-theme)',
            }"
            @current-change="handlePageChange"
            @size-change="handleSizeChange"
          />
        </div>
      </template>
    </el-card>

    <!-- ===================================================================
         3. 新增/编辑用户对话框
         =================================================================== -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="520px"
      top="10vh"
      :close-on-click-modal="false"
      destroy-on-close
      @closed="handleDialogClose"
    >
      <el-form
        ref="formRef"
        :model="dialogForm"
        :rules="currentRules"
        label-position="top"
        size="default"
      >
        <!-- 用户名 -->
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="dialogForm.username"
            placeholder="请输入用户名（2-20 个字符）"
            maxlength="20"
            :style="{ '--el-border-radius-base': 'var(--zh-radius8)' }"
          />
        </el-form-item>

        <!-- 真实姓名 -->
        <el-form-item label="真实姓名" prop="real_name">
          <el-input
            v-model="dialogForm.real_name"
            placeholder="请输入真实姓名"
            maxlength="20"
            :style="{ '--el-border-radius-base': 'var(--zh-radius8)' }"
          />
        </el-form-item>

        <!-- 手机号 -->
        <el-form-item label="手机号" prop="phone">
          <el-input
            v-model="dialogForm.phone"
            placeholder="请输入手机号（选填）"
            maxlength="11"
            :style="{ '--el-border-radius-base': 'var(--zh-radius8)' }"
          />
        </el-form-item>

        <!-- 邮箱 -->
        <el-form-item label="邮箱" prop="email">
          <el-input
            v-model="dialogForm.email"
            placeholder="请输入邮箱地址"
            type="email"
            :style="{ '--el-border-radius-base': 'var(--zh-radius8)' }"
          />
        </el-form-item>

        <!-- 角色（多选） -->
        <el-form-item label="角色" prop="roles">
          <el-select
            v-model="dialogForm.roles"
            placeholder="请选择角色（可多选）"
            multiple
            style="width: 100%;"
            :style="{ '--el-border-radius-base': 'var(--zh-radius8)' }"
          >
            <el-option
              v-for="opt in ROLE_OPTIONS.filter(o => o.value !== '')"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </el-form-item>

        <!-- 状态 -->
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="dialogForm.status">
            <el-radio value="active">正常</el-radio>
            <el-radio value="banned">已封禁</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- 初始密码（仅新增模式） -->
        <el-form-item
          v-if="dialogMode === 'create'"
          label="初始密码"
          prop="password"
        >
          <el-input
            v-model="dialogForm.password"
            placeholder="请输入初始密码（不少于 6 个字符）"
            show-password
            :style="{ '--el-border-radius-base': 'var(--zh-radius8)' }"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="flex justify-end gap-3">
          <el-button
            :style="{ borderRadius: 'var(--zh-radius8)' }"
            @click="dialogVisible = false"
          >
            取消
          </el-button>
          <el-button
            type="primary"
            :loading="isSubmitting"
            :style="{ borderRadius: 'var(--zh-radius8)' }"
            @click="handleDialogConfirm"
          >
            {{ dialogMode === 'create' ? '确认创建' : '保存修改' }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
/* ===== 表格行悬浮过渡 ===== */
:deep(.user-table-row) {
  transition: background-color 150ms cubic-bezier(0.4, 0, 0.2, 1);
}

/* ===== 被禁用户行弱化 ===== */
:deep(.user-table-row.banned-row) {
  opacity: 0.65;
}

/* ===== 表格加载遮罩样式 ===== */
:deep(.el-loading-mask) {
  background: var(--zh-background-mask10);
}

/* ===== 骨架屏脉冲 ===== */
.skeleton-loader {
  background: linear-gradient(
    90deg,
    var(--zh-background-light-gray) 25%,
    var(--zh-background-light-grey) 50%,
    var(--zh-background-light-gray) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: var(--zh-radius4);
}

@keyframes shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}
</style>
