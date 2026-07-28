<!--
  [数据交互说明]
  - 导入:
    - ElementPlus 组件: ElCard, ElTable, ElTableColumn, ElTag, ElButton, ElInput, ElSelect, ElOption,
      ElPagination, ElDialog, ElDrawer, ElForm, ElFormItem, ElSkeleton, ElEmpty, ElMessageBox, ElMessage,
      ElTooltip, ElCheckbox, ElRadioGroup, ElRadio
    - ElementPlus Icons: Search, Plus, Edit, Delete, Refresh, Lock, UserFilled
    - `ref`, `reactive`, `computed`, `onMounted`, `onBeforeUnmount`, `nextTick` from Vue
  - 依赖:
    - 无外部 API 调用，当前使用静态示例数据（后续替换为后端 API）
  - 输入: 无 props，数据在组件内部 mock
  - 输出: 渲染角色管理视图（工具栏 + 数据表格 + 展开行 + 分页器 + 新增/编辑对话框 + 权限编辑抽屉）
  - 监听: `admin-refresh` 自定义事件（从 AdminHeader 刷新按钮发出），触发数据重新加载
  - 跳转: 成员数点击可跳转到用户管理页并预筛该角色（通过 query 参数传递）
-->

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import {
  Search,
  Plus,
  Edit,
  Delete,
  Refresh,
  Lock,
  UserFilled,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()

// ===================================================================
// 配置常量 — 所有下拉选项、表格列、分页参数、权限模块集中管理
// ===================================================================

/** 角色图标预设 — 6 种渐变色 + emoji 组合，便于快速区分角色 */
const ROLE_ICON_OPTIONS = [
  { key: 'shield', emoji: '🛡', gradient: 'linear-gradient(135deg, #4F46E5, #7C3AED)' },
  { key: 'edit',   emoji: '📝', gradient: 'linear-gradient(135deg, #2563EB, #29BECC)' },
  { key: 'book',   emoji: '📚', gradient: 'linear-gradient(135deg, #1F993F, #60A5FA)' },
  { key: 'gear',   emoji: '⚙',  gradient: 'linear-gradient(135deg, #6B7280, #9CA3AF)' },
  { key: 'search', emoji: '🔍', gradient: 'linear-gradient(135deg, #FF6B3F, #F59E0B)' },
  { key: 'user',   emoji: '👤', gradient: 'var(--zh-gradient-blue)' },
]

/** 状态筛选项 */
const STATUS_OPTIONS = [
  { label: '全部状态', value: '' },
  { label: '启用',     value: 'active' },
  { label: '停用',     value: 'disabled' },
]

/** 每页条数选项 */
const PAGE_SIZE_OPTIONS = [10, 20, 50, 100]

/**
 * 权限模块定义
 * 每个模块包含 key（标识）、label（中文名）、actions（操作权限项列表）
 */
const PERMISSION_MODULES = [
  {
    key: 'dashboard',
    label: '数据看板',
    actions: [
      { key: 'view',   label: '查看' },
      { key: 'export', label: '导出' },
      { key: 'stats',  label: '统计' },
    ],
  },
  {
    key: 'users',
    label: '用户管理',
    actions: [
      { key: 'view',          label: '查看' },
      { key: 'create',        label: '新增' },
      { key: 'edit',          label: '编辑' },
      { key: 'delete',        label: '删除' },
      { key: 'resetPassword', label: '重置密码' },
    ],
  },
  {
    key: 'roles',
    label: '角色管理',
    actions: [
      { key: 'view',          label: '查看' },
      { key: 'create',        label: '新增' },
      { key: 'edit',          label: '编辑' },
      { key: 'delete',        label: '删除' },
      { key: 'configPerm',    label: '配置权限' },
    ],
  },
  {
    key: 'audit',
    label: '内容审核与社区治理',
    actions: [
      { key: 'view',   label: '查看' },
      { key: 'audit',  label: '审核' },
      { key: 'delete', label: '删除' },
    ],
  },
  {
    key: 'resources',
    label: '公共资源与知识库',
    actions: [
      { key: 'view',   label: '查看' },
      { key: 'edit',   label: '编辑' },
      { key: 'delete', label: '删除' },
    ],
  },
  {
    key: 'settings',
    label: '系统配置',
    actions: [
      { key: 'view',     label: '查看' },
      { key: 'modify',   label: '修改' },
    ],
  },
]

// ===================================================================
// 响应式状态
// ===================================================================

/** 数据加载状态（首次加载全页骨架屏） */
const isLoading = ref(true)

/** 表格数据加载中（筛选/分页切换时的局部 loading） */
const isTableLoading = ref(false)

/** 角色列表数据 */
const roleList = ref([])

/** 筛选条件 */
const filters = reactive({
  status: '',
  keyword: '',
})

/** 分页参数 */
const pagination = reactive({
  currentPage: 1,
  pageSize: 20,
  total: 0,
})

/** 新增/编辑对话框可见性 */
const dialogVisible = ref(false)

/** 对话框模式：'create' | 'edit' */
const dialogMode = ref('create')

/** 对话框标题（计算属性） */
const dialogTitle = computed(() => {
  const name = dialogForm.name || ''
  return dialogMode.value === 'create' ? '新增角色' : `编辑角色 — ${name}`
})

/** 对话框加载态（提交中） */
const isSubmitting = ref(false)

/** 表单引用（用于校验） */
const formRef = ref(null)

/** 对话框表单数据 */
const dialogForm = reactive({
  id: null,
  name: '',
  description: '',
  icon: 'shield',
  status: 'active',
})

/** 表单校验规则 */
const formRules = {
  name: [
    { required: true, message: '请输入角色名称', trigger: 'blur' },
    { min: 2, max: 20, message: '角色名称长度须在 2 到 20 个字符之间', trigger: 'blur' },
  ],
  description: [
    { required: true, message: '请输入角色描述', trigger: 'blur' },
    { max: 100, message: '角色描述不能超过 100 个字符', trigger: 'blur' },
  ],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
}

/** 权限编辑抽屉可见性 */
const permDrawerVisible = ref(false)

/** 当前编辑权限的角色名称 */
const permEditingRoleName = ref('')

/** 当前编辑权限的角色 ID */
const permEditingRoleId = ref(null)

/**
 * 权限编辑状态 — 二维校验矩阵
 * 结构: { [moduleKey]: { [actionKey]: boolean } }
 */
const permCheckStates = reactive({})

/** 权限抽屉保存中 */
const isSavingPerm = ref(false)

/** 权限编辑是否有未保存更改（用于关闭确认） */
const hasPermChanges = ref(false)

// ===================================================================
// Mock 数据生成
// ===================================================================

/**
 * 生成模拟角色数据
 * 后续替换为后端 API 调用
 * @returns {Array} 角色对象数组
 */
const generateMockRoles = () => {
  // 定义所有角色模板
  const templates = [
    {
      id: '0001',
      name: '超级管理员',
      description: '拥有系统全部权限，可管理所有模块和用户',
      icon: 'shield',
      memberCount: 3,
      status: 'active',
      created_at: '2026-01-15 09:30',
      permissions: buildFullPermissions(true),
    },
    {
      id: '0002',
      name: '内容审核员',
      description: '负责内容审核与社区治理，可查看知识库但不可编辑',
      icon: 'search',
      memberCount: 23,
      status: 'active',
      created_at: '2026-01-20 14:00',
      permissions: buildPartialPermissions({
        dashboard: ['view'],
        audit: ['view', 'audit', 'delete'],
        resources: ['view'],
      }),
    },
    {
      id: '0003',
      name: '知识库维护员',
      description: '负责公共资源和知识库的内容维护与更新',
      icon: 'book',
      memberCount: 8,
      status: 'active',
      created_at: '2026-02-08 11:20',
      permissions: buildPartialPermissions({
        dashboard: ['view'],
        resources: ['view', 'edit', 'delete'],
      }),
    },
    {
      id: '0004',
      name: '系统配置管理员',
      description: '负责系统配置修改，可查看用户和角色但不可编辑',
      icon: 'gear',
      memberCount: 2,
      status: 'active',
      created_at: '2026-03-01 16:45',
      permissions: buildPartialPermissions({
        dashboard: ['view'],
        users: ['view'],
        roles: ['view'],
        settings: ['view', 'modify'],
      }),
    },
    {
      id: '0005',
      name: '普通教师',
      description: '基础角色，仅可查看数据看板和个人信息',
      icon: 'user',
      memberCount: 45,
      status: 'active',
      created_at: '2026-03-15 08:00',
      permissions: buildPartialPermissions({
        dashboard: ['view'],
      }),
    },
    {
      id: '0006',
      name: '访客',
      description: '受限角色，仅可查看数据看板概览，不可导出和统计',
      icon: 'edit',
      memberCount: 5,
      status: 'disabled',
      created_at: '2026-04-10 10:30',
      permissions: buildPartialPermissions({
        dashboard: ['view'],
      }),
    },
  ]
  return templates
}

/**
 * 根据模块-操作映射构建权限数据结构
 * @param {Object|boolean} spec — true 表示全选，或 { moduleKey: [actionKey, ...] } 映射
 * @returns {Array} 权限对象数组
 */
const buildPartialPermissions = (spec) => {
  return PERMISSION_MODULES.map((mod) => {
    const allowedActions = spec[mod.key] || []
    return {
      moduleKey: mod.key,
      moduleLabel: mod.label,
      actions: mod.actions.map((act) => ({
        key: act.key,
        label: act.label,
        granted: allowedActions.includes(act.key),
      })),
    }
  })
}

/**
 * 构建全选/全不选权限数据
 * @param {boolean} allGranted — true 全选，false 全不选
 * @returns {Array} 权限对象数组
 */
const buildFullPermissions = (allGranted) => {
  return PERMISSION_MODULES.map((mod) => ({
    moduleKey: mod.key,
    moduleLabel: mod.label,
    actions: mod.actions.map((act) => ({
      key: act.key,
      label: act.label,
      granted: allGranted,
    })),
  }))
}

/** 全部角色数据（模拟数据库） */
let allRoles = []

// ===================================================================
// 方法
// ===================================================================

/**
 * 发送筛选请求（模拟）
 * 将筛选条件 + 分页参数合并后过滤 mock 数据
 */
const fetchRoles = () => {
  isTableLoading.value = true

  // 模拟网络延迟
  setTimeout(() => {
    let filtered = [...allRoles]

    // 状态筛选
    if (filters.status) {
      filtered = filtered.filter((r) => r.status === filters.status)
    }
    // 关键词搜索（模糊匹配角色名称和描述）
    if (filters.keyword.trim()) {
      const kw = filters.keyword.trim().toLowerCase()
      filtered = filtered.filter(
        (r) =>
          r.name.toLowerCase().includes(kw) ||
          r.description.toLowerCase().includes(kw),
      )
    }

    // 分页切割
    pagination.total = filtered.length
    const start = (pagination.currentPage - 1) * pagination.pageSize
    const end = start + pagination.pageSize
    roleList.value = filtered.slice(start, end)

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
    allRoles = generateMockRoles()
    isLoading.value = false
    fetchRoles()
  }, 600)
}

/**
 * 处理刷新 — 由 Header 的刷新按钮触发
 */
const handleRefresh = () => {
  loadData()
}

/**
 * 状态筛选变更处理
 * 重置到第 1 页并重新请求数据
 */
const handleFilterChange = () => {
  pagination.currentPage = 1
  fetchRoles()
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
  fetchRoles()
}

/**
 * 分页每页条数变更
 * @param {number} size - 每页条数
 */
const handleSizeChange = (size) => {
  pagination.pageSize = size
  pagination.currentPage = 1
  fetchRoles()
}

/**
 * 获取图标预设对象
 * @param {string} key - 图标 key
 * @returns {Object} { key, emoji, gradient }
 */
const getIconOption = (key) => ROLE_ICON_OPTIONS.find((o) => o.key === key) || ROLE_ICON_OPTIONS[5]

/**
 * 打开新增角色对话框
 * 重置表单为空值
 */
const openCreateDialog = () => {
  dialogMode.value = 'create'
  dialogForm.id = null
  dialogForm.name = ''
  dialogForm.description = ''
  dialogForm.icon = 'user'
  dialogForm.status = 'active'
  dialogVisible.value = true
}

/**
 * 打开编辑角色对话框
 * 预填当前行数据到表单
 * @param {Object} row - 当前行角色数据
 */
const openEditDialog = (row) => {
  dialogMode.value = 'edit'
  dialogForm.id = row.id
  dialogForm.name = row.name
  dialogForm.description = row.description
  dialogForm.icon = row.icon
  dialogForm.status = row.status
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

  // 名称唯一性检查（模拟异步校验，新增模式且名称变更时触发）
  if (dialogMode.value === 'create') {
    const duplicate = allRoles.some(
      (r) => r.name === dialogForm.name,
    )
    if (duplicate) {
      ElMessage.warning(`角色名称「${dialogForm.name}」已存在，请更换名称`)
      return
    }
  } else {
    const duplicate = allRoles.some(
      (r) => r.name === dialogForm.name && r.id !== dialogForm.id,
    )
    if (duplicate) {
      ElMessage.warning(`角色名称「${dialogForm.name}」已被其他角色使用，请更换名称`)
      return
    }
  }

  isSubmitting.value = true

  // 模拟 API 请求
  setTimeout(() => {
    if (dialogMode.value === 'create') {
      // 新增：模拟插入数据（空权限集，提示用户去配置权限）
      const newId = String(allRoles.length + 1).padStart(4, '0')
      const iconOpt = getIconOption(dialogForm.icon)
      const newRole = {
        id: newId,
        name: dialogForm.name,
        description: dialogForm.description,
        icon: dialogForm.icon,
        memberCount: 0,
        status: dialogForm.status,
        created_at: new Date().toISOString().replace('T', ' ').slice(0, 16),
        permissions: buildFullPermissions(false),
      }
      allRoles.unshift(newRole)
      ElMessage.success(`已成功创建角色「${newRole.name}」`)
      // 新增成功后自动弹出权限配置抽屉
      isSubmitting.value = false
      dialogVisible.value = false
      fetchRoles()
      // 延迟打开权限抽屉，确保 DOM 更新完毕
      setTimeout(() => {
        openPermDrawer(newRole)
      }, 200)
    } else {
      // 编辑：更新现有数据
      const idx = allRoles.findIndex((r) => r.id === dialogForm.id)
      if (idx !== -1) {
        allRoles[idx].name = dialogForm.name
        allRoles[idx].description = dialogForm.description
        allRoles[idx].icon = dialogForm.icon
        allRoles[idx].status = dialogForm.status
      }
      // 同时更新当前页的表格显示
      const row = roleList.value.find((r) => r.id === dialogForm.id)
      if (row) {
        row.name = dialogForm.name
        row.description = dialogForm.description
        row.icon = dialogForm.icon
        row.status = dialogForm.status
      }
      ElMessage.success(`已成功更新角色「${dialogForm.name}」的信息`)
      isSubmitting.value = false
      dialogVisible.value = false
      fetchRoles()
    }
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
 * 删除角色 — 二次确认后执行
 * 根据成员数分级提示
 * @param {Object} row - 当前行角色数据
 */
const handleDeleteRole = (row) => {
  const memberWarning =
    row.memberCount > 0
      ? `角色「${row.name}」下有 ${row.memberCount} 名成员。删除角色后，这些成员将失去该角色的权限。确定删除吗？`
      : `确定要删除角色「${row.name}」吗？此操作不可撤销。`

  ElMessageBox.confirm(memberWarning, '确认删除', {
    confirmButtonText: '确认删除',
    cancelButtonText: '取消',
    type: 'warning',
    confirmButtonClass: 'el-button--danger',
  })
    .then(() => {
      // 模拟 API 删除
      allRoles = allRoles.filter((r) => r.id !== row.id)
      ElMessage.success(`已删除角色「${row.name}」`)
      // 如果当前页删空了且不是第一页，回到上一页
      if (roleList.value.length === 1 && pagination.currentPage > 1) {
        pagination.currentPage--
      }
      fetchRoles()
    })
    .catch(() => {
      // 用户取消删除，不做任何操作
    })
}

/**
 * 打开权限编辑抽屉
 * 将角色的权限数据映射到复选框状态
 * @param {Object} row - 当前行角色数据
 */
const openPermDrawer = (row) => {
  permEditingRoleId.value = row.id
  permEditingRoleName.value = row.name
  hasPermChanges.value = false

  // 重置权限校验状态
  Object.keys(permCheckStates).forEach((k) => delete permCheckStates[k])

  // 填充现有权限状态
  if (row.permissions && row.permissions.length > 0) {
    row.permissions.forEach((mod) => {
      if (!permCheckStates[mod.moduleKey]) {
        permCheckStates[mod.moduleKey] = {}
      }
      mod.actions.forEach((act) => {
        permCheckStates[mod.moduleKey][act.key] = act.granted
      })
    })
  } else {
    // 无权限数据时全部置为 false
    PERMISSION_MODULES.forEach((mod) => {
      if (!permCheckStates[mod.key]) {
        permCheckStates[mod.key] = {}
      }
      mod.actions.forEach((act) => {
        permCheckStates[mod.key][act.key] = false
      })
    })
  }

  permDrawerVisible.value = true
}

/**
 * 权限复选框变更处理
 * 标记为有未保存更改
 */
const handlePermChange = () => {
  hasPermChanges.value = true
}

/**
 * 模块全选
 * @param {string} moduleKey - 模块 key
 */
const handleModuleSelectAll = (moduleKey) => {
  const mod = PERMISSION_MODULES.find((m) => m.key === moduleKey)
  if (!mod) return
  mod.actions.forEach((act) => {
    permCheckStates[moduleKey][act.key] = true
  })
  hasPermChanges.value = true
}

/**
 * 模块取消全选
 * @param {string} moduleKey - 模块 key
 */
const handleModuleDeselectAll = (moduleKey) => {
  const mod = PERMISSION_MODULES.find((m) => m.key === moduleKey)
  if (!mod) return
  mod.actions.forEach((act) => {
    permCheckStates[moduleKey][act.key] = false
  })
  hasPermChanges.value = true
}

/**
 * 全局全选/取消全选所有权限
 * 由底部「全选所有权限」复选框驱动
 */
const isGlobalAllChecked = computed({
  get() {
    for (const mod of PERMISSION_MODULES) {
      for (const act of mod.actions) {
        if (!permCheckStates[mod.key]?.[act.key]) return false
      }
    }
    return true
  },
  set(val) {
    PERMISSION_MODULES.forEach((mod) => {
      if (!permCheckStates[mod.key]) permCheckStates[mod.key] = {}
      mod.actions.forEach((act) => {
        permCheckStates[mod.key][act.key] = val
      })
    })
    hasPermChanges.value = true
  },
})

/**
 * 保存权限配置
 * 将复选框状态写回角色数据
 */
const handleSavePermissions = () => {
  isSavingPerm.value = true

  setTimeout(() => {
    const idx = allRoles.findIndex((r) => r.id === permEditingRoleId.value)
    if (idx !== -1) {
      // 将校验状态转回权限数据结构
      allRoles[idx].permissions = PERMISSION_MODULES.map((mod) => ({
        moduleKey: mod.key,
        moduleLabel: mod.label,
        actions: mod.actions.map((act) => ({
          key: act.key,
          label: act.label,
          granted: !!permCheckStates[mod.key]?.[act.key],
        })),
      }))
    }
    // 更新当前页显示
    const row = roleList.value.find((r) => r.id === permEditingRoleId.value)
    if (row) {
      const src = allRoles.find((r) => r.id === permEditingRoleId.value)
      if (src) row.permissions = src.permissions
    }

    isSavingPerm.value = false
    hasPermChanges.value = false
    permDrawerVisible.value = false
    ElMessage.success(`角色「${permEditingRoleName.value}」的权限配置已保存`)
  }, 400)
}

/**
 * 权限抽屉关闭前确认
 * 有未保存更改时弹出二次确认
 */
const handlePermDrawerClose = () => {
  if (hasPermChanges.value) {
    ElMessageBox.confirm(
      '有未保存的权限更改，确定放弃吗？',
      '确认关闭',
      {
        confirmButtonText: '放弃更改',
        cancelButtonText: '继续编辑',
        type: 'warning',
      },
    )
      .then(() => {
        hasPermChanges.value = false
        permDrawerVisible.value = false
      })
      .catch(() => {
        // 用户取消关闭，不做任何操作
      })
  } else {
    permDrawerVisible.value = false
  }
}

/**
 * 点击成员数 — 跳转到用户管理页并预筛该角色
 * @param {Object} row - 当前行角色数据
 */
const handleMemberClick = (row) => {
  if (row.memberCount === 0) return
  router.push({ path: '/main/users', query: { role: row.name } })
}

/**
 * 获取角色拥有的权限模块数量
 * @param {Array} permissions - 权限数组
 * @returns {number} 至少有一个操作的模块数
 */
const getGrantedModuleCount = (permissions) => {
  if (!permissions || permissions.length === 0) return 0
  return permissions.filter((mod) =>
    mod.actions.some((act) => act.granted),
  ).length
}

/**
 * 获取角色权限的标签摘要列表
 * 用于展开行渲染，每个模块生成一个摘要字符串
 * @param {Array} permissions - 权限数组
 * @returns {Array<{label: string, text: string}>} 模块权限摘要
 */
const getPermissionSummary = (permissions) => {
  if (!permissions || permissions.length === 0) return []
  return permissions
    .filter((mod) => mod.actions.some((act) => act.granted))
    .map((mod) => {
      const grantedActions = mod.actions.filter((a) => a.granted)
      const allModuleActions = PERMISSION_MODULES.find(
        (m) => m.key === mod.moduleKey,
      )?.actions
      const isFull =
        allModuleActions &&
        grantedActions.length === allModuleActions.length
      const actionText = isFull
        ? '全部'
        : grantedActions.map((a) => a.label).join('+')
      return {
        label: mod.moduleLabel,
        text: `${mod.moduleLabel}(${actionText})`,
      }
    })
}

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
        角色列表
      </h1>

      <!-- 右侧：筛选器组 + 操作按钮 -->
      <div class="flex items-center flex-wrap gap-3">
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
          placeholder="搜索角色名称 / 描述..."
          clearable
          size="default"
          :prefix-icon="Search"
          style="width: 240px;"
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

        <!-- 新增角色主按钮 -->
        <el-button
          type="primary"
          :icon="Plus"
          size="default"
          :style="{ borderRadius: 'var(--zh-radius8)' }"
          @click="openCreateDialog"
        >
          新增角色
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
          <div class="skeleton-loader w-8 h-8 rounded-lg shrink-0"></div>
          <div class="skeleton-loader w-24 h-4 rounded"></div>
          <div class="skeleton-loader flex-1 h-4 rounded"></div>
          <div class="skeleton-loader w-12 h-4 rounded"></div>
          <div class="skeleton-loader w-16 h-6 rounded-full"></div>
          <div class="skeleton-loader w-24 h-4 rounded"></div>
          <div class="skeleton-loader w-35 h-4 rounded"></div>
        </div>
      </template>

      <!-- 正式表格 -->
      <template v-else>
        <el-table
          :data="roleList"
          stripe
          highlight-current-row
          border
          v-loading="isTableLoading"
          row-class-name="role-table-row"
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
          <!-- 展开行 -->
          <el-table-column type="expand" width="44" align="center">
            <template #default="{ row }">
              <div
                class="py-3"
                style="padding-left: 48px; padding-right: 20px; background: var(--zh-background-weaken);"
              >
                <div class="flex items-start gap-2 flex-wrap">
                  <span
                    style="font-size: var(--zh-font-size13); color: var(--zh-text-caption); flex-shrink: 0; line-height: 24px;"
                  >
                    权限范围：
                  </span>
                  <template v-if="getGrantedModuleCount(row.permissions) === 0">
                    <span
                      style="font-size: var(--zh-font-size13); color: var(--zh-text-disabled); line-height: 24px;"
                    >
                      暂无权限配置
                    </span>
                  </template>
                  <template v-else>
                    <el-tag
                      v-for="item in getPermissionSummary(row.permissions)"
                      :key="item.label"
                      size="small"
                      type="info"
                      effect="plain"
                      class="perm-tag"
                    >
                      {{ item.text }}
                    </el-tag>
                  </template>
                </div>
                <div class="mt-2">
                  <el-button
                    type="primary"
                    link
                    size="small"
                    :style="{ fontSize: 'var(--zh-font-size12)' }"
                    @click="openPermDrawer(row)"
                  >
                    <el-icon class="mr-0.5"><Edit /></el-icon>
                    编辑权限
                  </el-button>
                </div>
              </div>
            </template>
          </el-table-column>

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

          <!-- 列：角色名称 -->
          <el-table-column
            prop="name"
            label="角色名称"
            min-width="160"
          >
            <template #default="{ row }">
              <div class="flex items-center gap-2.5">
                <!-- 角色图标色块 -->
                <div
                  class="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 text-base"
                  :style="{ background: getIconOption(row.icon).gradient }"
                >
                  {{ getIconOption(row.icon).emoji }}
                </div>
                <span
                  class="font-medium truncate"
                  style="
                    font-size: var(--zh-font-size14);
                    color: var(--zh-text-primary);
                  "
                >
                  {{ row.name }}
                </span>
              </div>
            </template>
          </el-table-column>

          <!-- 列：角色描述 -->
          <el-table-column
            prop="description"
            label="角色描述"
            min-width="200"
          >
            <template #default="{ row }">
              <el-tooltip
                :content="row.description"
                placement="top"
                effect="dark"
                :disabled="row.description.length <= 25"
              >
                <span
                  class="inline-block max-w-60 truncate"
                  style="
                    font-size: var(--zh-font-size14);
                    color: var(--zh-text-secondary);
                  "
                >
                  {{ row.description }}
                </span>
              </el-tooltip>
            </template>
          </el-table-column>

          <!-- 列：成员数 -->
          <el-table-column
            prop="memberCount"
            label="成员数"
            width="100"
            align="center"
            sortable
          >
            <template #default="{ row }">
              <span
                :class="row.memberCount > 0 ? 'cursor-pointer hover:underline' : ''"
                style="
                  font-family: var(--zh-font-number);
                  font-size: var(--zh-font-size14);
                  color: row.memberCount > 0
                    ? 'var(--zh-text-theme)'
                    : 'var(--zh-text-disabled)';
                "
                @click="handleMemberClick(row)"
              >
                {{ row.memberCount }}
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
                :type="row.status === 'active' ? 'success' : 'info'"
                size="small"
                effect="plain"
              >
                <span class="flex items-center gap-1.5">
                  <span
                    class="inline-block w-1.5 h-1.5 rounded-full shrink-0"
                    :style="{
                      background: row.status === 'active'
                        ? 'var(--zh-green)'
                        : 'var(--zh-text-disabled)',
                    }"
                  ></span>
                  {{ row.status === 'active' ? '启用' : '停用' }}
                </span>
              </el-tag>
            </template>
          </el-table-column>

          <!-- 列：创建时间 -->
          <el-table-column
            prop="created_at"
            label="创建时间"
            width="170"
            align="center"
            sortable
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

          <!-- 列：操作 -->
          <el-table-column
            label="操作"
            width="170"
            align="center"
            fixed="right"
          >
            <template #default="{ row }">
              <div class="flex items-center justify-center gap-1">
                <el-button
                  type="primary"
                  link
                  size="small"
                  :style="{ fontSize: 'var(--zh-font-size13)' }"
                  @click="openPermDrawer(row)"
                >
                  <el-icon class="mr-0.5"><Lock /></el-icon>
                  权限
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
                  @click="handleDeleteRole(row)"
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
              description="暂无角色数据"
              :image-size="80"
            >
              <template v-if="filters.status || filters.keyword">
                <span
                  style="font-size: var(--zh-font-size13); color: var(--zh-text-caption);"
                >
                  没有符合条件的角色，请调整筛选条件
                </span>
                <el-button
                  type="primary"
                  link
                  size="small"
                  class="mt-2"
                  @click="
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
                  新增第一个角色
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
         3. 新增/编辑角色对话框
         =================================================================== -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="480px"
      top="10vh"
      :close-on-click-modal="false"
      destroy-on-close
      @closed="handleDialogClose"
    >
      <el-form
        ref="formRef"
        :model="dialogForm"
        :rules="formRules"
        label-position="top"
        size="default"
      >
        <!-- 图标选择器 -->
        <el-form-item label="角色图标">
          <div class="flex gap-2">
            <div
              v-for="opt in ROLE_ICON_OPTIONS"
              :key="opt.key"
              class="w-9 h-9 rounded-lg flex items-center justify-center cursor-pointer text-lg shrink-0 icon-option"
              :class="{ 'icon-selected': dialogForm.icon === opt.key }"
              :style="{
                background: opt.gradient,
                border: dialogForm.icon === opt.key
                  ? '2px solid var(--zh-text-theme)'
                  : '2px solid transparent',
              }"
              @click="dialogForm.icon = opt.key"
            >
              {{ opt.emoji }}
            </div>
          </div>
        </el-form-item>

        <!-- 角色名称 -->
        <el-form-item label="角色名称" prop="name">
          <el-input
            v-model="dialogForm.name"
            placeholder="请输入角色名称（2-20 个字符，名称须全局唯一）"
            maxlength="20"
            :style="{ '--el-border-radius-base': 'var(--zh-radius8)' }"
          />
        </el-form-item>

        <!-- 角色描述 -->
        <el-form-item label="角色描述" prop="description">
          <el-input
            v-model="dialogForm.description"
            placeholder="请输入角色描述（不超过 100 个字符）"
            type="textarea"
            maxlength="100"
            rows="3"
            show-word-limit
            :style="{ '--el-border-radius-base': 'var(--zh-radius8)' }"
          />
        </el-form-item>

        <!-- 状态 -->
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="dialogForm.status">
            <el-radio value="active">启用</el-radio>
            <el-radio value="disabled">停用</el-radio>
          </el-radio-group>
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

    <!-- ===================================================================
         4. 权限编辑抽屉
         =================================================================== -->
    <el-drawer
      v-model="permDrawerVisible"
      direction="rtl"
      size="480px"
      :before-close="handlePermDrawerClose"
      destroy-on-close
      :style="{
        '--el-drawer-bg-color': 'var(--zh-background-primary)',
        '--el-drawer-padding-primary': '24px',
      }"
    >
      <template #header>
        <span
          style="font-size: var(--zh-font-size16); font-weight: 600; color: var(--zh-text-primary);"
        >
          权限配置 — {{ permEditingRoleName }}
        </span>
      </template>

      <div class="flex flex-col gap-5">
        <!-- 各模块权限卡片 -->
        <div
          v-for="mod in PERMISSION_MODULES"
          :key="mod.key"
          class="rounded-lg p-4"
          style="
            border: 1px solid var(--zh-line-border);
            background: var(--zh-background-light-gray);
          "
        >
          <!-- 模块标题行 -->
          <div class="flex items-center justify-between mb-3">
            <span
              style="font-size: var(--zh-font-size14); font-weight: 600; color: var(--zh-text-primary);"
            >
              {{ mod.label }}
            </span>
            <div class="flex gap-2">
              <el-button
                type="primary"
                link
                size="small"
                :style="{ fontSize: 'var(--zh-font-size12)' }"
                @click="handleModuleSelectAll(mod.key)"
              >
                全选
              </el-button>
              <el-button
                link
                size="small"
                :style="{ fontSize: 'var(--zh-font-size12)', color: 'var(--zh-text-caption)' }"
                @click="handleModuleDeselectAll(mod.key)"
              >
                取消全选
              </el-button>
            </div>
          </div>
          <!-- 操作权限复选框 -->
          <div class="flex flex-wrap gap-x-4 gap-y-2">
            <el-checkbox
              v-for="act in mod.actions"
              :key="act.key"
              :model-value="!!permCheckStates[mod.key]?.[act.key]"
              :label="act.label"
              size="default"
              @change="
                (val) => {
                  if (!permCheckStates[mod.key]) permCheckStates[mod.key] = {};
                  permCheckStates[mod.key][act.key] = val;
                  handlePermChange();
                }
              "
            />
          </div>
        </div>

        <!-- 全局全选 -->
        <div
          class="rounded-lg p-4"
          style="
            border: 1px solid var(--zh-line-border);
            background: var(--zh-background-weaken);
          "
        >
          <el-checkbox
            :model-value="isGlobalAllChecked"
            label="全选所有权限"
            size="default"
            @change="(val) => { isGlobalAllChecked = val; }"
          />
        </div>
      </div>

      <template #footer>
        <div class="flex justify-end gap-3">
          <el-button
            :style="{ borderRadius: 'var(--zh-radius8)' }"
            @click="handlePermDrawerClose"
          >
            取消
          </el-button>
          <el-button
            type="primary"
            :loading="isSavingPerm"
            :style="{ borderRadius: 'var(--zh-radius8)' }"
            @click="handleSavePermissions"
          >
            保存权限配置
          </el-button>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<style scoped>
/* ===== 表格行悬浮过渡 ===== */
:deep(.role-table-row) {
  transition: background-color 150ms cubic-bezier(0.4, 0, 0.2, 1);
}

/* ===== 表格加载遮罩样式 ===== */
:deep(.el-loading-mask) {
  background: var(--zh-background-mask10);
}

/* ===== 图标选择器悬浮效果 ===== */
.icon-option {
  transition: transform 150ms cubic-bezier(0.4, 0, 0.2, 1),
    border-color 150ms cubic-bezier(0.4, 0, 0.2, 1),
    box-shadow 150ms cubic-bezier(0.4, 0, 0.2, 1);
}
.icon-option:hover {
  transform: scale(1.1);
  box-shadow: var(--zh-shadow1);
}
.icon-selected {
  box-shadow: 0 0 0 3px var(--zh-background-option-on);
}

/* ===== 权限标签间距 ===== */
.perm-tag {
  margin-bottom: 4px;
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
