<template>
  <el-container class="layout">
    <el-aside width="212px" class="aside">
      <div class="brand">
        <div class="logo">AIGC</div>
        <div class="brand-text">
          <strong>番剧制作工作台</strong>
          <span>Anime Production Studio</span>
        </div>
      </div>
      <el-menu :default-active="activeMenu" router class="menu">
        <el-menu-item index="/dashboard"><el-icon><DataLine /></el-icon><span>数据看板</span></el-menu-item>
        <el-menu-item index="/series"><el-icon><VideoCamera /></el-icon><span>项目管理</span></el-menu-item>
        <el-menu-item index="/prompts"><el-icon><MagicStick /></el-icon><span>提示词工作台</span></el-menu-item>
        <el-menu-item index="/tasks"><el-icon><Cpu /></el-icon><span>生成任务</span></el-menu-item>
        <el-menu-item index="/assets"><el-icon><PictureFilled /></el-icon><span>素材库</span></el-menu-item>
        <el-menu-item index="/reviews"><el-icon><Stamp /></el-icon><span>审核流</span></el-menu-item>
      </el-menu>
      <div class="aside-foot muted">v1.0.0 · 离线 Mock 生成可用</div>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="crumb">{{ currentTitle }}</div>
        <div class="user">
          <el-tag size="small" type="success" effect="dark">{{ roleLabel }}</el-tag>
          <span class="muted">{{ userName }}</span>
          <el-button link size="small" @click="logout">退出登录</el-button>
        </div>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const roleLabels: Record<string, string> = {
  director: '导演',
  storyboard: '分镜师',
  artist: '美术',
  reviewer: '审核',
  student: '学员',
  admin: '管理员'
}

const currentTitle = computed(() => (route.meta.title as string) || '工作台')
const activeMenu = computed(() => {
  if (route.path.startsWith('/series')) return '/series'
  if (route.path.startsWith('/episodes')) return '/series'
  return route.path
})
const userName = computed(() => auth.user?.display_name || auth.user?.username || '未登录')
const roleLabel = computed(() => roleLabels[auth.user?.role || ''] || auth.user?.role_label || '访客')

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.layout {
  height: 100vh;
}

.aside {
  background: #12161f;
  border-right: 1px solid var(--aigc-line);
  display: flex;
  flex-direction: column;
}

.brand {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 18px 16px;
  border-bottom: 1px solid var(--aigc-line);
}

.logo {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  font-weight: 700;
  font-size: 12px;
  background: linear-gradient(140deg, var(--aigc-accent), var(--aigc-accent-2));
  color: #0b0e14;
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
  font-size: 13px;
}

.brand-text span {
  color: var(--aigc-muted);
  font-size: 10px;
  letter-spacing: 0.4px;
}

.menu {
  border-right: none;
  background: transparent;
  flex: 1;
}

.aside-foot {
  padding: 12px 16px;
  font-size: 11px;
  border-top: 1px solid var(--aigc-line);
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--aigc-line);
  background: rgba(18, 22, 31, 0.86);
  height: 56px;
}

.crumb {
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.user {
  display: flex;
  align-items: center;
  gap: 10px;
}

.main {
  padding: 0;
  overflow-y: auto;
}

/* Element Plus 菜单在深色侧边栏下的对比度：默认文字是深色，需要显式提亮 */
.menu :deep(.el-menu-item) {
  color: #c3cbdb;
  height: 46px;
  margin: 2px 8px;
  border-radius: 8px;
}

.menu :deep(.el-menu-item:hover) {
  background: rgba(124, 92, 255, 0.14);
  color: #ffffff;
}

.menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(100deg, rgba(124, 92, 255, 0.34), rgba(53, 208, 186, 0.16));
  color: #ffffff;
  font-weight: 600;
}

.menu :deep(.el-menu-item .el-icon) {
  margin-right: 8px;
}
</style>
