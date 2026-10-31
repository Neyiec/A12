import{
    createRouter,
    createWebHashHistory
} from 'vue-router'

import login from '../components/login.vue'
import main from '../components/main.vue'
import {getCurrentUser} from'../apis/login.js'
import {isTokenExpired} from '../utils/JWTParser.js'
// 全局用户 store — 替代直接操作 localStorage
import { useUserStore } from '../storage/user.js'
import { ElMessage } from 'element-plus'
import { canAccessAdminPath, firstAdminPath } from '../utils/adminAccess.js'
import { loginLocation } from '../../../frontend/src/utils/sessionRedirect.js'

const componentLoaders = import.meta.glob(['../components/*.vue', '../views/admin/*.vue'])

const routes = [
  {
    path: '/',
    redirect: '/main',
  },
  {
    path: '/login',
    component: login,
  },
  {
    path: '/main',
    component: main,
    name: 'M',
    redirect: '/main/dashboard',
    // 静态子路由 — 六个管理模块作为 main 布局的嵌套路由
    children: [
      { path: 'access', name: 'AdminAccess', component: () => import('../views/admin/AccessNotice.vue'), meta: { staticTeacherPage: true } },
      {
        path: 'questions', name: 'QuestionManagement',
        component: () => import('../views/admin/QuestionManagement.vue'),
        meta: { staticTeacherPage: true },
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/admin/Dashboard.vue'),
        meta: { staticTeacherPage: true },
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('../views/admin/SystemSettings.vue'),
        meta: { staticTeacherPage: true },
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('../views/admin/UserPermission.vue'),
        meta: { staticTeacherPage: true },
      },
      {
        path: 'roles',
        name: 'Roles',
        component: () => import('../views/admin/RoleManagement.vue'),
        meta: { staticTeacherPage: true },
      },
      {
        path: 'audit',
        name: 'Audit',
        component: () => import('../views/admin/ContentAudit.vue'),
        meta: { staticTeacherPage: true },
      },
      {
        path: 'resources',
        name: 'Resources',
        component: () => import('../views/admin/ResourceKnowledge.vue'),
        meta: { staticTeacherPage: true },
      },
    ],
  }
]

const router = createRouter({
    history: createWebHashHistory(),
    routes
})

/**
 * 动态导入路由，输入的菜单数据必须满足以下条件：
 * 1. path 属性必须存在，且要以/main开头
 * 2. component 属性必须存在，且必须是组件原名
 * @param {*} menus 菜单树对象
 */
export function addDynamicRoutes(menus) {
  // dfs遍历菜单树
  // 递归截止条件
  if (!menus || menus.length === 0) {
    return
  }
  // 遍历当前层
  menus.forEach(menu => {
    // 处理路径：确保是相对于 /main 的路径
    let relativePath = String(menu.path || '')
    if (relativePath.startsWith('/main/')) {
      relativePath = relativePath.replace('/main/', '')
    }
    // TODO 这里的父路由名被固定为Main，后期可以改成动态获取
    if (menu.path && menu.component && !router.getRoutes().some(route => route.path === menu.path)){
      const name = String(menu.component).replace(/\.vue$/i, '')
      const component = componentLoaders[`../components/${name}.vue`] || componentLoaders[`../views/admin/${name}.vue`]
      if(component && relativePath && !relativePath.startsWith('/')) router.addRoute('M', { path: relativePath, component })
    }

    // 递归处理子菜单
    if(menu.children && menu.children.length > 0){
      addDynamicRoutes(menu.children);
    }
  }
  )
}


/* 添加路由守卫 */
let checkedToken = ''

router.beforeEach(async (to) => {
  // 本地开发预览入口：便于在外部浏览器检查教师端界面，不影响生产环境鉴权。
  const isDevelopmentPreview =
    import.meta.env.DEV && to.path.startsWith('/main') && to.query.preview === '1'

  if (isDevelopmentPreview) {
    return
  }

  // 从 Pinia store 获取 token（自动从持久化的 localStorage 恢复）
  const userStore = useUserStore()
  const token = userStore.token

  if (to.path !== '/login' && (!token || isTokenExpired(token))) {
    userStore.clearUser()
    checkedToken = ''
    return loginLocation(to.fullPath)
  }

  // 清除过期或缺失 token 的用户状态
  if (!token || isTokenExpired(token)) {
    userStore.clearUser()
    checkedToken = ''
  }

  if (to.path === '/login' || to.path === '/main/access') return
  if (checkedToken !== token) {
    try {
      const result = await getCurrentUser()
      if (userStore.token !== token) return loginLocation(to.fullPath)
      userStore.setUserInfo(result.data)
      checkedToken = token
    } catch (error) {
      ElMessage.error(error.message || '账号权限加载失败')
      if (error.response?.status === 401 || error.code === 401) return loginLocation(to.fullPath)
      return { path: '/main/access', query: { service: 'unavailable' } }
    }
  }
  if (!canAccessAdminPath(to.path, userStore.userInfo?.permissions)) return firstAdminPath(userStore.userInfo?.permissions)
})

router.onError((error) => {
  console.warn('[admin-router] 页面加载失败', error)
  ElMessage.error('管理页面加载失败，请刷新后重试；若仍有问题，请重启前端服务')
})

export default router
