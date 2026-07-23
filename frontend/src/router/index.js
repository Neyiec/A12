import{
    createRouter,
    createWebHashHistory
} from 'vue-router'

import HelloWorld from '../components/HelloWorld.vue'
import {getRouters} from'../apis/login.js'
import {isTokenExpired} from '../utils/JWTParser.js'

const routes = [{
    path: '/login',
    component: HelloWorld
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
    let relativePath = menu.path
    if (relativePath.startsWith('/main/')) {
      relativePath = relativePath.replace('/main/', '')
    }
    // TODO 这里的父路由名被固定为Main，后期可以改成动态获取
    if (menu.path && menu.component){
      // 动态导入组件 - 从 components 目录加载
      const component = () => import(`@/components/${menu.component}.vue`)
      router.addRoute('M', {
        path: relativePath,
        component
      })
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
  const token = localStorage.getItem('token')
  
  if (to.path !== '/login' && (!token || isTokenExpired(token))) {
    next('/login')
    return
  }

  if(!token || isTokenExpired(token)){
      localStorage.removeItem('token')
      localStorage.removeItem('menus')
      menusLoaded = false
    }
  // 
  if (to.path.startsWith('/main') && !menusLoaded) {
    getRouters().then(res => {
      // 添加动态路由
      addDynamicRoutes(res.data.menus)
      // 标记菜单已加载
      menusLoaded = true
      // 存储菜单数据
      localStorage.setItem('menus', JSON.stringify(res.data.menus));

      next(to.fullPath);
    })
  } else {
    next()
  }
})

export default router