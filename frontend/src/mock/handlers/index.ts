/**
 * [数据交互说明]
 * - 导出: 聚合所有模块的 MSW 请求处理器
 * - 依赖: 各模块 handler 文件（auth, user, ai, project, resource, export, community, admin, python-ppt）
 * - 输入: 被 mock/browser.ts 和 mock/node.ts 引用
 * - 输出: 统一的 RequestHandler[] 数组，供 setupWorker / setupServer 使用
 */

import { authHandlers } from './auth'
import { userHandlers } from './user'
import { aiHandlers } from './ai'
import { projectHandlers } from './project'
import { resourceHandlers } from './resource'
import { exportHandlers } from './export'
import { communityHandlers } from './community'
import { adminHandlers } from './admin'
import { pythonPptHandlers } from './python-ppt'

const useRealAiApi = import.meta.env.VITE_USE_REAL_AI_API === 'true'
// 真实 AI 联调需要 Java 颁发的 JWT；同时放行教师端会话、项目和资源接口，避免 mock token 被真实网关拒绝。
const useRealTeacherApi = useRealAiApi

/**
 * 所有 API mock 处理器
 * 涵盖 API 文档中的全部接口：
 *   认证模块 (API-01~08)、用户模块 (API-09~11)、AI引擎 (API-12~18)、
 *   项目模块 (API-20~35)、资源库 (API-36~46)、导出中心 (API-47~56)、
 *   社区模块 (API-57~74)、后台管理 (API-75~132)、Python PPT服务 (API-133~144)
 */
export const handlers = [
  ...(useRealTeacherApi ? [] : authHandlers),
  ...(useRealTeacherApi ? [] : userHandlers),
  // 真实 AI 联调时不拦截会话、消息、大纲和任务请求，让它们走 Java 网关。
  ...(useRealAiApi ? [] : aiHandlers),
  ...(useRealTeacherApi ? [] : projectHandlers),
  ...(useRealTeacherApi ? [] : resourceHandlers),
  ...exportHandlers,
  ...communityHandlers,
  ...adminHandlers,
  ...pythonPptHandlers,
]
