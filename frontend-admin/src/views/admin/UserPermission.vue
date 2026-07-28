<!--
  [数据交互说明]
  - 导入:
    - ElementPlus 组件: ElCard, ElTable, ElTableColumn, ElTag, ElButton, ElInput, ElSelect, ElOption,
      ElPagination, ElDialog, ElForm, ElFormItem, ElAvatar, ElSkeleton, ElEmpty, ElMessageBox, ElMessage,
      ElTooltip, ElRadioGroup, ElRadioButton
    - ElementPlus Icons: Search, Plus, Edit, Delete, Refresh, UserFilled
    - `ref`, `reactive`, `computed`, `onMounted` from Vue
  - 依赖:
    - 无外部 API 调用，当前使用静态示例数据（后续替换为后端 API）
  - 输入: 无 props，数据在组件内部 mock
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
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

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

/** 对话框表单数据 */
const dialogForm = reactive({
  id: null,
  username: '',
  email: '',
  role: 'teacher',
  status: 'active',
  password: '',
})

/** 新增模式下的表单校验规则 */
const createRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 20, message: '用户名长度须在 2 到 20 个字符之间', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
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
  role: createRules.role,
  status: createRules.status,
}

/** 当前校验规则（根据模式动态切换） */
const currentRules = computed(() => {
  return dialogMode.value === 'create' ? createRules : editRules
})

// ===================================================================
// Mock 数据生成
// ===================================================================

/**
 * 生成模拟用户数据
 * 后续替换为后端 API 调用
 * @returns {Array} 用户对象数组
 */
const generateMockUsers = () => {
  const roles = ['super_admin', 'content_auditor', 'knowledge_curator', 'teacher']
  const statuses = ['active', 'banned']
  const users = []

  for (let i = 1; i <= 86; i++) {
    const role = roles[i % roles.length]
    const id = String(i).padStart(4, '0')
    users.push({
      id,
      username: `教师${i}`,
      email: `teacher${i}@zhihu-edu.com`,
      avatar: '',
      role,
      status: statuses[i % 7 === 0 ? 1 : 0],
      created_at: `2026-${String((i % 6) + 1).padStart(2, '0')}-${String((i % 28) + 1).padStart(2, '0')} ${String(i % 24).padStart(2, '0')}:${String(i % 60).padStart(2, '0')}`,
    })
  }
  return users
}

/** 全部用户数据（模拟数据库） */
let allUsers = []

// ===================================================================
// 方法
// ===================================================================

/**
 * 发送筛选请求（模拟）
 * 将筛选条件 + 分页参数合并后过滤 mock 数据
 */
const fetchUsers = () => {
  isTableLoading.value = true

  // 模拟网络延迟
  setTimeout(() => {
    let filtered = [...allUsers]

    // 角色筛选
    if (filters.role) {
      filtered = filtered.filter((u) => u.role === filters.role)
    }
    // 状态筛选
    if (filters.status) {
      filtered = filtered.filter((u) => u.status === filters.status)
    }
    // 关键词搜索（模糊匹配用户名和邮箱）
    if (filters.keyword.trim()) {
      const kw = filters.keyword.trim().toLowerCase()
      filtered = filtered.filter(
        (u) =>
          u.username.toLowerCase().includes(kw) ||
          u.email.toLowerCase().includes(kw),
      )
    }

    // 分页切割
    pagination.total = filtered.length
    const start = (pagination.currentPage - 1) * pagination.pageSize
    const end = start + pagination.pageSize
    userList.value = filtered.slice(start, end)

    isTableLoading.value = false
  }, 300)
}

/**
 * 页面首次数据加载
 * 显示全页骨架屏，加载完成后渲染表格
 */
const loadData = () => {
  isLoading.value = true
  setTimeout(() => {
    allUsers = generateMockUsers()
    isLoading.value = false
    fetchUsers()
  }, 600)
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
  dialogForm.email = ''
  dialogForm.role = 'teacher'
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
  dialogForm.email = row.email
  dialogForm.role = row.role
  dialogForm.status = row.status
  dialogForm.password = ''
  dialogVisible.value = true
}

/**
 * 对话框确认提交
 * 根据模式执行新增或编辑逻辑
 */
const handleDialogConfirm = async () => {
  // 表单校验
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  isSubmitting.value = true

  // 模拟 API 请求
  setTimeout(() => {
    if (dialogMode.value === 'create') {
      // 新增：模拟插入数据
      const newId = String(allUsers.length + 1).padStart(4, '0')
      const newUser = {
        id: newId,
        username: dialogForm.username,
        email: dialogForm.email,
        avatar: '',
        role: dialogForm.role,
        status: dialogForm.status,
        created_at: new Date().toISOString().replace('T', ' ').slice(0, 16),
      }
      allUsers.unshift(newUser)
      ElMessage.success(`已成功创建用户「${newUser.username}」`)
    } else {
      // 编辑：更新现有数据
      const idx = allUsers.findIndex((u) => u.id === dialogForm.id)
      if (idx !== -1) {
        allUsers[idx].username = dialogForm.username
        allUsers[idx].email = dialogForm.email
        allUsers[idx].role = dialogForm.role
        allUsers[idx].status = dialogForm.status
      }
      // 同时更新当前页的表格显示
      const row = userList.value.find((u) => u.id === dialogForm.id)
      if (row) {
        row.username = dialogForm.username
        row.email = dialogForm.email
        row.role = dialogForm.role
        row.status = dialogForm.status
      }
      ElMessage.success(`已成功更新用户「${dialogForm.username}」的信息`)
    }

    isSubmitting.value = false
    dialogVisible.value = false
    fetchUsers()
  }, 400)
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
    .then(() => {
      // 模拟 API 删除
      allUsers = allUsers.filter((u) => u.id !== row.id)
      ElMessage.success(`已删除用户「${row.username}」`)
      // 如果当前页删空了且不是第一页，回到上一页
      if (userList.value.length === 1 && pagination.currentPage > 1) {
        pagination.currentPage--
      }
      fetchUsers()
    })
    .catch(() => {
      // 用户取消删除，不做任何操作
    })
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
            width="140"
            align="center"
            fixed="right"
          >
            <template #default="{ row }">
              <div class="flex items-center justify-center gap-2">
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

        <!-- 邮箱 -->
        <el-form-item label="邮箱" prop="email">
          <el-input
            v-model="dialogForm.email"
            placeholder="请输入邮箱地址"
            type="email"
            :style="{ '--el-border-radius-base': 'var(--zh-radius8)' }"
          />
        </el-form-item>

        <!-- 角色 -->
        <el-form-item label="角色" prop="role">
          <el-select
            v-model="dialogForm.role"
            placeholder="请选择角色"
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
