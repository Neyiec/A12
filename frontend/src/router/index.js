import{
    createRouter,
    createWebHashHistory
} from 'vue-router'

import {getRouters} from'../apis/login.js'
import {isSessionExpired} from '../utils/JWTParser.js'
// 全局用户 store — 替代直接操作 localStorage
import { useUserStore } from '../storage/user.js'

// 所有页面保持按需加载。之前既静态导入页面、又用变量 import 扫描整个
// components 目录，会把创作工作台及其编辑器依赖一并放入首屏包。
// 这里仍支持后端菜单返回组件名，但只允许加载构建时已知的同级 Vue 组件。
const componentLoaders = import.meta.glob('../components/*.vue')
const getComponentLoader = (componentName) => {
  const normalizedName = String(componentName || '').replace(/\.vue$/i, '').trim()
  return componentLoaders[`../components/${normalizedName}.vue`] || null
}

const login = getComponentLoader('login')
const LandingPage = getComponentLoader('LandingPage')
const TeacherHome = getComponentLoader('TeacherHome')
const TeacherLayout = getComponentLoader('TeacherLayout')
const ResourceLibrary = getComponentLoader('ResourceLibrary')
const CommunityHub = getComponentLoader('CommunityHub')
const ExportCenter = getComponentLoader('ExportCenter')
const CreationWorkspace = getComponentLoader('CreationWorkspace')
const AccountSettings = getComponentLoader('AccountSettings')
const CourseGraphWorkspace = getComponentLoader('CourseGraphWorkspace')

const routes = [
  {
    path: '/',
    component: LandingPage,
    meta: { publicPage: true },
  },
  {
    path: '/login',
    component: login,
  },
  {
    path: '/main',
    name: 'M',
    component: TeacherLayout,
    children: [
      { path: '', component: TeacherHome, meta: { menu: 'home', title: '个人工作空间', staticTeacherPage: true } },
      { path: 'resources', component: ResourceLibrary, meta: { menu: 'resources', title: '个人资源库', staticTeacherPage: true } },
      { path: 'community', component: CommunityHub, meta: { menu: 'community', title: '技能与案例', staticTeacherPage: true } },
      { path: 'exports', component: ExportCenter, meta: { menu: 'exports', title: '成果导出中心', staticTeacherPage: true } },
      { path: 'workspace', component: CreationWorkspace, meta: { menu: 'workspace', title: '创作工作台', staticTeacherPage: true } },
      { path: 'settings', component: AccountSettings, meta: { menu: 'settings', title: '账号与安全', staticTeacherPage: true } },
      { path: 'courses', component: CourseGraphWorkspace, meta: { menu: 'courses', title: '课程双图谱', staticTeacherPage: true } },
    ],
  },
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
    let relativePath = menu.path
    if (relativePath.startsWith('/main/')) {
      relativePath = relativePath.replace('/main/', '')
    }
    // TODO 这里的父路由名被固定为Main，后期可以改成动态获取
    if (menu.path && menu.component){
      const component = getComponentLoader(menu.component)
      if (component) {
        router.addRoute('M', {
          path: relativePath,
          component
        })
      } else {
        // 菜单数据不能让浏览器尝试加载一个构建产物中不存在的任意路径。
        console.warn(`[router] 未找到菜单组件：${menu.component}`)
      }
    }

    // 递归处理子菜单
    if(menu.children && menu.children.length > 0){
      addDynamicRoutes(menu.children);
    }
  }
  )
}


/* 添加路由守卫 */
let menusLoaded = false

router.beforeEach((to, from, next) => {
  // 本地开发预览入口：便于在外部浏览器检查教师端界面，不影响生产环境鉴权。
  const isDevelopmentPreview =
    import.meta.env.DEV && to.path.startsWith('/main') && to.query.preview === '1'

  if (isDevelopmentPreview) {
    next()
    return
  }

  // 从 Pinia store 获取 token（自动从持久化的 localStorage 恢复）
  const userStore = useUserStore()
  const token = userStore.token
  const sessionExpired = !token || isSessionExpired(token, userStore.loginAt)

  if (!to.meta.publicPage && to.path !== '/login' && sessionExpired) {
    next('/login')
    return
  }

  // 清除过期或缺失 token 的用户状态
  if (sessionExpired) {
    userStore.clearUser()
    menusLoaded = false
  }

  // 动态路由加载：非静态教师页面且菜单未加载时，请求后端获取菜单
  if (to.path.startsWith('/main/') && !to.meta.staticTeacherPage && !menusLoaded) {
    getRouters().then(res => {
      // 添加动态路由
      addDynamicRoutes(res.data.menus)
      // 标记菜单已加载
      menusLoaded = true
      // 将菜单数据存入 Pinia store（自动持久化）
      userStore.setMenus(res.data.menus)

      next(to.fullPath)
    })
  } else {
    next()
  }
})

export default router
