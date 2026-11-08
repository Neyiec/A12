// Navigation hints only. Java still authorizes every admin API independently.
export const adminRoutePermissions = {
  '/main/dashboard': ['dashboard:view'],
  '/main/questions': ['audit:view', 'resources:edit'],
  '/main/audit': ['audit:view'],
  '/main/resources': ['resources:view'],
  '/main/users': ['users:view'],
  '/main/roles': ['roles:view'],
  '/main/settings': ['settings:view'],
}
export function permissionList(value) {
  try { const list=typeof value==='string'?JSON.parse(value):value;return Array.isArray(list)?list.filter(item=>typeof item==='string'):[] } catch { return [] }
}
export function hasPermission(permissions, permission) { return permissionList(permissions).includes(permission) }
export function canAccessAdminPath(path, permissions) {
  return !!adminRoutePermissions[path]?.some(permission=>hasPermission(permissions,permission))
}
export function firstAdminPath(permissions) {
  return Object.keys(adminRoutePermissions).find(path=>canAccessAdminPath(path,permissions))||'/main/access'
}
export function filterAdminMenus(items, permissions) {
  return items.flatMap(item=>{
    if(item.children){const children=filterAdminMenus(item.children,permissions);return children.length?[{...item,children}]:[]}
    return canAccessAdminPath(item.path,permissions)?[item]:[]
  })
}
