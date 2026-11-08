<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../../storage/user'
import { getCurrentUser } from '../../apis/login'
import { firstAdminPath, permissionList } from '../../utils/adminAccess'
const route=useRoute(),router=useRouter(),user=useUserStore(),loading=ref(false)
const permissions=computed(()=>permissionList(user.userInfo?.permissions))
const roles=computed(()=>Array.isArray(user.userInfo?.roles)?user.userInfo.roles.join('、'):'未配置')
async function refresh(){
  if(loading.value)return
  loading.value=true
  try {
    const result=await getCurrentUser();user.setUserInfo(result.data)
    const target=firstAdminPath(user.userInfo?.permissions)
    if(target!=='/main/access')await router.replace(target)
    else ElMessage.info('账号已登录，但暂未分配管理权限，请联系有授权权限的管理员')
  }catch(error){ElMessage.error(error.message||'权限刷新失败，请检查账号服务')}
  finally{loading.value=false}
}
onMounted(()=>window.addEventListener('admin-refresh',refresh))
onBeforeUnmount(()=>window.removeEventListener('admin-refresh',refresh))
</script>
<template>
  <section class="access-notice">
    <p class="eyebrow">ACCOUNT ACCESS</p><h1>账号已登录，请检查管理权限</h1>
    <p>“管理员”角色名称不等于已拥有所有功能权限。为避免无效请求，当前仅展示你有权限访问的功能。</p>
    <el-alert v-if="route.query.service" title="暂时无法获取最新权限，请检查后端服务后点击刷新。" type="warning" :closable="false"/>
    <dl><dt>当前账号</dt><dd>{{ user.userInfo?.username || '当前用户' }}</dd><dt>当前角色</dt><dd>{{ roles }}</dd><dt>已有权限</dt><dd>{{ permissions.length ? permissions.join('、') : '暂无管理权限' }}</dd></dl>
    <p>需要审核题目或社区投稿，请申请审核权限；需要录入题目或维护公共资源，请申请资源管理权限。系统不会自动提权。</p>
    <el-button type="primary" :loading="loading" @click="refresh">刷新我的权限</el-button>
  </section>
</template>
<style scoped>.access-notice{max-width:900px;margin:40px auto;background:white;border:1px solid #dbe7f8;border-radius:18px;padding:36px;color:#223955}.access-notice p{line-height:1.8;color:#62758f}.access-notice .eyebrow{color:#2563eb;font-weight:600}.access-notice h1{font-size:27px;margin:14px 0}dl{display:grid;grid-template-columns:100px 1fr;gap:14px;padding:24px;background:#f3f7ff;border-radius:12px;margin:24px 0}dd{margin:0;overflow-wrap:anywhere}dt{color:#62758f}@media(max-width:600px){.access-notice{padding:20px}dl{grid-template-columns:1fr}}</style>
