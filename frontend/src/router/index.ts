import { createRouter, createWebHashHistory, type RouteRecordRaw } from 'vue-router'

import AppLayout from '@/components/AppLayout.vue'

const routes: RouteRecordRaw[] = [
  { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { public: true } },
  {
    path: '/',
    component: AppLayout,
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'dashboard', component: () => import('@/views/DashboardView.vue'), meta: { title: '数据看板' } },
      { path: 'series', name: 'series', component: () => import('@/views/SeriesListView.vue'), meta: { title: '项目管理' } },
      { path: 'series/:id', name: 'series-detail', component: () => import('@/views/SeriesDetailView.vue'), meta: { title: '项目详情' } },
      { path: 'episodes/:id/storyboard', name: 'storyboard', component: () => import('@/views/StoryboardView.vue'), meta: { title: '分镜工作台' } },
      { path: 'episodes/:id/timeline', name: 'timeline', component: () => import('@/views/TimelineView.vue'), meta: { title: '成片合成单' } },
      { path: 'series/:id/characters', name: 'characters', component: () => import('@/views/CharactersView.vue'), meta: { title: '角色与场景' } },
      { path: 'prompts', name: 'prompts', component: () => import('@/views/PromptStudioView.vue'), meta: { title: '提示词工作台' } },
      { path: 'tasks', name: 'tasks', component: () => import('@/views/TasksView.vue'), meta: { title: '生成任务' } },
      { path: 'assets', name: 'assets', component: () => import('@/views/AssetsView.vue'), meta: { title: '素材库' } },
      { path: 'reviews', name: 'reviews', component: () => import('@/views/ReviewsView.vue'), meta: { title: '审核流' } }
    ]
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' }
]

const router = createRouter({ history: createWebHashHistory(), routes })

router.beforeEach((to) => {
  const token = localStorage.getItem('aigc_token')
  if (!to.meta.public && !token) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.path === '/login' && token) {
    return { path: '/dashboard' }
  }
  return true
})

export default router
