<!--
  [数据交互说明]
  - 导入: 资源库演示数据、Element Plus 组件与图标
  - 输出: 教师个人资源库页面
-->
<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Delete, Folder, Lock, MoreFilled, Search, Upload } from '@element-plus/icons-vue'
import { RESOURCE_PAGE } from '../config/teacherPages.config.js'

const keyword = ref('')
const activeFolder = ref('全部素材')
const selectedRows = ref([])
const filteredFiles = computed(() => RESOURCE_PAGE.files.filter((file) => (
  (activeFolder.value === '全部素材' || activeFolder.value === '我的课件' && file.type === 'PPT') &&
  file.name.toLowerCase().includes(keyword.value.toLowerCase())
)))

/** 模拟上传入口反馈。 */
const startUpload = () => ElMessage.info('请选择 Word、PDF、PPT、图片、音频或视频文件')
</script>

<template>
  <div class="page-wrap">
    <header class="page-heading">
      <div><p class="page-kicker">个人教学资产</p><h1>个人资源库</h1><p>统一管理私有素材，并决定哪些内容可供智能体引用。</p></div>
      <el-button type="primary" :icon="Upload" @click="startUpload">上传素材</el-button>
    </header>

    <section class="stat-strip" aria-label="资源库概览">
      <article v-for="stat in RESOURCE_PAGE.stats" :key="stat.label">
        <span>{{ stat.label }}</span><strong>{{ stat.value }}</strong><small>{{ stat.detail }}</small>
      </article>
    </section>

    <section class="resource-layout">
      <aside class="folder-panel">
        <div class="panel-title"><span>分类目录</span><el-button text circle aria-label="新建分类">+</el-button></div>
        <button v-for="folder in RESOURCE_PAGE.folders" :key="folder" :class="{ active: activeFolder === folder }" @click="activeFolder = folder">
          <el-icon><Folder /></el-icon><span>{{ folder }}</span>
        </button>
        <div class="privacy-note"><el-icon><Lock /></el-icon><p><strong>默认私有</strong><br>仅你和授权的智能体可以访问。</p></div>
      </aside>

      <div class="resource-content">
        <div class="resource-toolbar">
          <el-input v-model="keyword" :prefix-icon="Search" placeholder="搜索文件名、课程或标签" clearable />
          <el-select model-value="全部类型" aria-label="资源类型"><el-option label="全部类型" value="全部类型" /><el-option label="课件" value="课件" /><el-option label="文档" value="文档" /></el-select>
          <el-button :icon="Delete" :disabled="selectedRows.length === 0">批量管理</el-button>
        </div>
        <el-table :data="filteredFiles" @selection-change="selectedRows = $event">
          <el-table-column type="selection" width="42" />
          <el-table-column label="素材" min-width="260">
            <template #default="{ row }"><div class="file-cell"><span class="file-mark">{{ row.type.slice(0, 1) }}</span><div><strong>{{ row.name }}</strong><small>{{ row.course }} · {{ row.size }}</small></div></div></template>
          </el-table-column>
          <el-table-column prop="date" label="更新时间" min-width="120" />
          <el-table-column label="解析状态" width="110"><template #default="{ row }"><el-tag :type="row.status === '已解析' ? 'success' : row.status === '解析中' ? 'warning' : 'info'" effect="light">{{ row.status }}</el-tag></template></el-table-column>
          <el-table-column label="权限" width="92"><template #default><span class="private-label"><el-icon><Lock /></el-icon> 私有</span></template></el-table-column>
          <el-table-column width="54"><template #default><el-button text circle aria-label="更多操作"><el-icon><MoreFilled /></el-icon></el-button></template></el-table-column>
        </el-table>
      </div>
    </section>
  </div>
</template>

<style scoped>
.page-wrap { width: min(1220px, calc(100% - 48px)); margin: 0 auto; padding: 42px 0 56px; }
.page-heading { display: flex; align-items: end; justify-content: space-between; gap: 24px; }
.page-kicker { margin: 0 0 6px !important; color: var(--zh-text-theme) !important; font-size: 13px !important; font-weight: 600; }
.page-heading h1 { margin: 0; font-size: 30px; letter-spacing: var(--zh-tracking-tight); }
.page-heading p { margin: 8px 0 0; color: var(--zh-text-secondary); font-size: 14px; }
.stat-strip { display: grid; grid-template-columns: repeat(3, 1fr); margin-top: 32px; border-block: 1px solid var(--zh-line-border); }
.stat-strip article { display: grid; grid-template-columns: 1fr auto; gap: 4px 12px; padding: 22px 28px; border-right: 1px solid var(--zh-line-border); }
.stat-strip article:last-child { border: 0; }
.stat-strip span, .stat-strip small { color: var(--zh-text-caption); font-size: 12px; }
.stat-strip strong { grid-row: 1 / 3; grid-column: 2; align-self: center; font: 600 26px var(--zh-font-number); }
.resource-layout { display: grid; grid-template-columns: 210px minmax(0, 1fr); gap: 24px; margin-top: 28px; }
.folder-panel { padding: 14px; border-radius: var(--zh-radius12); background: var(--zh-background-pc-sidebar); }
.panel-title { display: flex; align-items: center; justify-content: space-between; padding: 0 8px 8px; color: var(--zh-text-caption); font-size: 12px; }
.folder-panel > button { width: 100%; display: flex; align-items: center; gap: 9px; padding: 10px; border: 0; border-radius: var(--zh-radius8); color: var(--zh-text-secondary); background: transparent; cursor: pointer; text-align: left; }
.folder-panel > button:hover, .folder-panel > button.active { color: var(--zh-text-theme); background: var(--zh-background-option-on); }
.privacy-note { display: flex; gap: 8px; margin-top: 20px; padding: 12px; border-top: 1px solid var(--zh-line-border); color: var(--zh-text-caption); font-size: 11px; }
.privacy-note p { margin: 0; line-height: 1.6; }.privacy-note strong { color: var(--zh-text-secondary); }
.resource-content { min-width: 0; }.resource-toolbar { display: grid; grid-template-columns: minmax(240px, 1fr) 140px auto; gap: 10px; margin-bottom: 16px; }
.file-cell { display: flex; align-items: center; gap: 12px; }.file-cell > div { min-width: 0; display: flex; flex-direction: column; }
.file-cell strong { overflow: hidden; color: var(--zh-text-primary); font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }.file-cell small { margin-top: 3px; color: var(--zh-text-caption); }
.file-mark { width: 34px; height: 38px; display: grid; place-items: center; border-radius: 6px; color: var(--zh-text-theme); background: var(--zh-background-weaken); font-weight: 700; }
.private-label { display: inline-flex; align-items: center; gap: 4px; color: var(--zh-text-secondary); font-size: 12px; }
:deep(.el-table) { --el-table-border-color: var(--zh-line-parting); --el-table-header-bg-color: var(--zh-background-light); border-radius: var(--zh-radius12); }
@media (max-width: 820px) { .resource-layout { grid-template-columns: 1fr; }.folder-panel { display: none; }.stat-strip { grid-template-columns: 1fr; }.stat-strip article { border-right: 0; }.resource-toolbar { grid-template-columns: 1fr; } }
</style>
