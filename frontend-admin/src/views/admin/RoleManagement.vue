<!--
  [数据交互说明]
  - 导入:
    - ElementPlus 组件: ElCard, ElTable, ElTableColumn, ElTag, ElButton, ElInput, ElSelect, ElOption,
      ElPagination, ElDialog, ElDrawer, ElForm, ElFormItem, ElSkeleton, ElEmpty, ElMessageBox, ElMessage,
      ElTooltip, ElCheckbox, ElRadioGroup, ElRadio
    - ElementPlus Icons: Search, Plus, Edit, Delete, Refresh, Lock, UserFilled
    - `ref`, `reactive`, `computed`, `onMounted`, `onBeforeUnmount`, `nextTick` from Vue
  - 依赖:
    - `getAdminRoles`: 来自 `../apis/user.js`（API-80 查询角色列表，含权限矩阵/描述/成员数/状态）
    - `createAdminRole`: 来自 `../apis/user.js`（API-80A 创建角色，创建成功后自动打开权限抽屉）
    - `updateAdminRole`: 来自 `../apis/user.js`（API-80B 更新角色信息，仅更新传入字段）
    - `deleteAdminRole`: 来自 `../apis/user.js`（API-80C 删除角色，硬删除并级联清理关联）
    - `updateRolePermissions`: 来自 `../apis/user.js`（API-82 配置角色权限，提交权限矩阵 JSON）
  - 输入: 无 props，角色数据来自后端 API-80
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
import { getAdminRoles, createAdminRole, updateAdminRole, deleteAdminRole, updateRolePermissions } from '@/apis/user.js'

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
  role_code: '',
  name: '',
  description: '',
  icon: 'shield',
  status: 'active',
})

/** 表单校验规则 */
const formRules = {
  role_code: [
    { required: true, message: '请输入角色编码', trigger: 'blur' },
    {
      pattern: /^[a-z][a-z0-9_]{1,49}$/,
      message: '小写字母开头，仅可包含小写字母/数字/下划线',
      trigger: 'blur',
    },
  ],
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
// 数据适配 — 后端 API-80 角色对象 → 页面行数据
// ===================================================================

/** 角色 role_code → 图标预设映射（后端不返回图标，按编码固定分配便于区分） */
const ROLE_ICON_BY_CODE = {
  super_admin: 'shield',
  admin: 'gear',
  content_auditor: 'search',
  knowledge_curator: 'book',
  teacher: 'user',
}

/**
 * ISO 时间字符串格式化为本地 "YYYY-MM-DD HH:mm"
 * @param {string|undefined} value - 后端返回的时间
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
 * 解析后端返回的权限矩阵（JSON 字符串 → 数组）
 * 解析失败时返回空数组，权限抽屉会回退为全未勾选
 * @param {string|Array} raw - 后端 permissions 字段
 * @returns {Array} [{moduleKey, moduleLabel, actions:[{key,label,granted}]}]
 */
const parsePermissions = (raw) => {
  if (Array.isArray(raw)) return raw
  if (typeof raw !== 'string' || !raw) return []
  try {
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

/**
 * 将后端 API-80 角色对象归一化为页面行数据
 * @param {Object} r - 后端角色对象 {role_id, role_code, role_name, description,
 *                     permissions, status, member_count, created_at}
 * @returns {Object} 页面行数据
 */
const normalizeRole = (r) => ({
  id: r.role_id,
  role_code: r.role_code,
  name: r.role_name,
  description: r.description || '',
  icon: ROLE_ICON_BY_CODE[r.role_code] || 'user',
  memberCount: r.member_count ?? 0,
  status: r.status === 1 ? 'active' : 'disabled',
  created_at: formatTime(r.created_at),
  permissions: parsePermissions(r.permissions),
})

/** 全部角色数据（API-80 拉取后缓存，筛选/分页在本页面内进行） */
let allRoles = []

// ===================================================================
// 方法
// ===================================================================

/**
 * 本地筛选 + 分页渲染
 * API-80 一次返回全量角色，状态/关键词筛选与分页在页面内完成
 */
const fetchRoles = () => {
  isTableLoading.value = true
  try {
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
  } finally {
    isTableLoading.value = false
  }
}

/**
 * 页面首次数据加载
 * 请求 API-80 获取真实角色列表，失败时提示并渲染空状态（不白屏）
 */
const loadData = async () => {
  isLoading.value = true
  try {
    const res = await getAdminRoles()
    if (res?.code !== 0 && res?.code !== 200) {
      ElMessage.error(res?.message || '角色列表加载失败')
      allRoles = []
      return
    }
    allRoles = (res?.data || []).map(normalizeRole)
    fetchRoles()
  } catch {
    ElMessage.error('角色列表加载失败，请稍后重试')
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
  dialogForm.role_code = ''
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
  dialogForm.role_code = row.role_code || ''
  dialogForm.name = row.name
  dialogForm.description = row.description
  dialogForm.icon = row.icon
  dialogForm.status = row.status
  dialogVisible.value = true
}

/**
 * 对话框确认提交
 * 创建模式调用 API-80A 创建角色；编辑模式后端暂无更新接口，仍为页面内模拟
 */
const handleDialogConfirm = async () => {
  // 表单校验
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  // 名称唯一性预检（后端仍会校验，这里提前给出反馈）
  const duplicate = allRoles.some(
    (r) => r.name === dialogForm.name && (dialogMode.value === 'create' || r.id !== dialogForm.id),
  )
  if (duplicate) {
    ElMessage.warning(`角色名称「${dialogForm.name}」已被使用，请更换名称`)
    return
  }

  if (dialogMode.value === 'create') {
    // 创建角色（API-80A）
    isSubmitting.value = true
    try {
      const res = await createAdminRole({
        role_code: dialogForm.role_code,
        role_name: dialogForm.name,
        description: dialogForm.description,
        status: dialogForm.status === 'active' ? 1 : 0,
      })
      if (res?.code !== 0 && res?.code !== 200) {
        ElMessage.error(res?.message || '创建角色失败')
        return
      }
      // 后端返回与 API-80 列表项一致的结构，归一化后插入列表头部
      const newRole = normalizeRole(res.data)
      allRoles.unshift(newRole)
      ElMessage.success(`已成功创建角色「${newRole.name}」，请配置权限`)
      dialogVisible.value = false
      fetchRoles()
      // 延迟打开权限抽屉，确保 DOM 更新完毕
      setTimeout(() => {
        openPermDrawer(newRole)
      }, 200)
    } catch {
      ElMessage.error('创建角色失败，请稍后重试')
    } finally {
      isSubmitting.value = false
    }
  } else {
    // 更新角色信息（API-80B）：role_code 不传（不可修改），仅提交表单编辑的字段
    isSubmitting.value = true
    try {
      const res = await updateAdminRole(dialogForm.id, {
        role_name: dialogForm.name,
        description: dialogForm.description,
        status: dialogForm.status === 'active' ? 1 : 0,
      })
      if (res?.code !== 0 && res?.code !== 200) {
        ElMessage.error(res?.message || '更新角色失败')
        return
      }
      // 用后端返回的最新数据整体替换列表中的行（成员数/状态等同步刷新）
      const updated = normalizeRole(res.data)
      const idx = allRoles.findIndex((r) => r.id === dialogForm.id)
      if (idx !== -1) {
        allRoles.splice(idx, 1, updated)
      }
      ElMessage.success(`已成功更新角色「${updated.name}」的信息`)
      dialogVisible.value = false
      fetchRoles()
    } catch {
      ElMessage.error('更新角色失败，请稍后重试')
    } finally {
      isSubmitting.value = false
    }
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
    .then(async () => {
      try {
        const res = await deleteAdminRole(row.id)
        if (res?.code !== 0 && res?.code !== 200) {
          ElMessage.error(res?.message || '删除角色失败')
          return
        }
        ElMessage.success(`已删除角色「${row.name}」`)
        // 本地列表同步移除；如果当前页删空了且不是第一页，回到上一页
        allRoles = allRoles.filter((r) => r.id !== row.id)
        if (roleList.value.length === 1 && pagination.currentPage > 1) {
          pagination.currentPage--
        }
        fetchRoles()
      } catch {
        ElMessage.error('删除角色失败，请稍后重试')
      }
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
 * 保存权限配置（API-82）
 * 将复选框状态转为权限矩阵 JSON 提交后端；后端仅返回 Result<Void>，
 * 成功后用提交的矩阵同步本地列表显示（持有者的鉴权缓存由后端清除）
 */
const handleSavePermissions = async () => {
  isSavingPerm.value = true
  try {
    // 将校验状态转为权限矩阵（与 API-82 约定的结构一致，后端解析 granted=true 的权限码）
    const matrix = PERMISSION_MODULES.map((mod) => ({
      moduleKey: mod.key,
      moduleLabel: mod.label,
      actions: mod.actions.map((act) => ({
        key: act.key,
        label: act.label,
        granted: !!permCheckStates[mod.key]?.[act.key],
      })),
    }))
    const res = await updateRolePermissions(permEditingRoleId.value, JSON.stringify(matrix))
    if (res?.code !== 0 && res?.code !== 200) {
      ElMessage.error(res?.message || '保存权限配置失败')
      return
    }
    // 本地列表同步更新
    const idx = allRoles.findIndex((r) => r.id === permEditingRoleId.value)
    if (idx !== -1) {
      allRoles[idx].permissions = matrix
    }
    const row = roleList.value.find((r) => r.id === permEditingRoleId.value)
    if (row) {
      row.permissions = matrix
    }

    hasPermChanges.value = false
    permDrawerVisible.value = false
    ElMessage.success(`角色「${permEditingRoleName.value}」的权限配置已保存`)
  } catch {
    ElMessage.error('保存权限配置失败，请稍后重试')
  } finally {
    isSavingPerm.value = false
  }
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

        <!-- 角色编码（全局唯一，创建后不可修改，编辑态置灰） -->
        <el-form-item label="角色编码" prop="role_code">
          <el-input
            v-model="dialogForm.role_code"
            placeholder="如 content_auditor（小写字母开头，可含数字/下划线）"
            maxlength="50"
            :disabled="dialogMode === 'edit'"
            :style="{ '--el-border-radius-base': 'var(--zh-radius8)' }"
          />
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
