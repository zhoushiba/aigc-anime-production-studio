import http from './http'

/** 接口封装：与后端 app/routers 一一对应，返回值已剥离统一响应体 */
export interface PageResult<T = any> {
  items: T[]
  total: number
  page: number
  size: number
}

export interface UserInfo {
  id: number
  username: string
  display_name: string
  role: string
  role_label: string
}

export const authApi = {
  login: (payload: { username: string; password: string }): Promise<any> => http.post('/auth/login', payload),
  register: (payload: { username: string; password: string; display_name?: string; role?: string }): Promise<any> =>
    http.post('/auth/register', payload),
  me: (): Promise<UserInfo> => http.get('/auth/me')
}

export const metaApi = {
  options: (): Promise<any> => http.get('/meta/options')
}

export const seriesApi = {
  list: (params: Record<string, unknown> = {}): Promise<PageResult> => http.get('/series', { params }),
  create: (payload: Record<string, unknown>): Promise<any> => http.post('/series', payload),
  detail: (id: number): Promise<any> => http.get(`/series/${id}`),
  update: (id: number, payload: Record<string, unknown>): Promise<any> => http.patch(`/series/${id}`, payload),
  remove: (id: number): Promise<any> => http.delete(`/series/${id}`),
  episodes: (id: number): Promise<PageResult> => http.get(`/series/${id}/episodes`),
  createEpisode: (id: number, payload: Record<string, unknown>): Promise<any> => http.post(`/series/${id}/episodes`, payload),
  characters: (id: number): Promise<PageResult> => http.get(`/series/${id}/characters`),
  createCharacter: (id: number, payload: Record<string, unknown>): Promise<any> => http.post(`/series/${id}/characters`, payload),
  sceneCards: (id: number): Promise<PageResult> => http.get(`/series/${id}/scene-cards`),
  createSceneCard: (id: number, payload: Record<string, unknown>): Promise<any> => http.post(`/series/${id}/scene-cards`, payload)
}

export const episodeApi = {
  detail: (id: number): Promise<any> => http.get(`/episodes/${id}`),
  update: (id: number, payload: Record<string, unknown>): Promise<any> => http.patch(`/episodes/${id}`, payload),
  script: (id: number): Promise<any> => http.get(`/episodes/${id}/script`),
  saveScript: (id: number, payload: Record<string, unknown>): Promise<any> => http.put(`/episodes/${id}/script`, payload),
  scenes: (id: number): Promise<PageResult> => http.get(`/episodes/${id}/scenes`),
  createScene: (id: number, payload: Record<string, unknown>): Promise<any> => http.post(`/episodes/${id}/scenes`, payload),
  moveScene: (sceneId: number, direction: 'up' | 'down'): Promise<any> => http.post(`/scenes/${sceneId}/move`, { direction })
}

export const storyboardApi = {
  shots: (episodeId: number): Promise<any> => http.get(`/episodes/${episodeId}/shots`),
  create: (episodeId: number, payload: Record<string, unknown>): Promise<any> => http.post(`/episodes/${episodeId}/shots`, payload),
  update: (shotId: number, payload: Record<string, unknown>): Promise<any> => http.patch(`/shots/${shotId}`, payload),
  remove: (shotId: number): Promise<any> => http.delete(`/shots/${shotId}`),
  move: (shotId: number, direction: 'up' | 'down'): Promise<any> => http.post(`/shots/${shotId}/move`, { direction }),
  reorder: (episodeId: number, orderedIds: number[]): Promise<any> =>
    http.post(`/episodes/${episodeId}/shots/reorder`, { ordered_ids: orderedIds }),
  promptFromShot: (shotId: number, payload: Record<string, unknown> = {}): Promise<any> =>
    http.post(`/shots/${shotId}/prompt`, { shot_id: shotId, consistency: true, save: true, ...payload })
}

export const promptApi = {
  build: (payload: Record<string, unknown>): Promise<any> => http.post('/prompts/build', payload),
  templates: (params: Record<string, unknown> = {}): Promise<PageResult> => http.get('/prompts/templates', { params }),
  history: (params: Record<string, unknown> = {}): Promise<PageResult> => http.get('/prompts/history', { params }),
  issues: (): Promise<PageResult> => http.get('/prompts/issues')
}

export const generationApi = {
  providers: (): Promise<PageResult> => http.get('/generation/providers'),
  stats: (): Promise<any> => http.get('/generation/stats'),
  list: (params: Record<string, unknown> = {}): Promise<PageResult> => http.get('/generation/tasks', { params }),
  detail: (id: number): Promise<any> => http.get(`/generation/tasks/${id}`),
  create: (payload: Record<string, unknown>): Promise<any> => http.post('/generation/tasks', payload),
  retry: (id: number, payload: Record<string, unknown> = {}): Promise<any> => http.post(`/generation/tasks/${id}/retry`, payload),
  cancel: (id: number): Promise<any> => http.post(`/generation/tasks/${id}/cancel`)
}

export const assetApi = {
  list: (params: Record<string, unknown> = {}): Promise<PageResult> => http.get('/assets', { params }),
  stats: (): Promise<any> => http.get('/assets/stats'),
  detail: (id: number): Promise<any> => http.get(`/assets/${id}`),
  update: (id: number, payload: Record<string, unknown>): Promise<any> => http.patch(`/assets/${id}`, payload),
  rate: (id: number, payload: Record<string, unknown>): Promise<any> => http.post(`/assets/${id}/rate`, payload),
  revise: (id: number, payload: Record<string, unknown>): Promise<any> => http.post(`/assets/${id}/revise`, payload),
  revisions: (id: number): Promise<any> => http.get(`/assets/${id}/revisions`),
  batch: (payload: Record<string, unknown>): Promise<any> => http.post('/assets/batch', payload)
}

export const timelineApi = {
  get: (episodeId: number): Promise<any> => http.get(`/episodes/${episodeId}/timeline`),
  save: (episodeId: number, payload: Record<string, unknown>): Promise<any> => http.put(`/episodes/${episodeId}/timeline`, payload),
  autoFill: (episodeId: number): Promise<any> => http.post(`/episodes/${episodeId}/timeline/auto-fill`),
  updateItem: (itemId: number, payload: Record<string, unknown>): Promise<any> => http.patch(`/timeline-items/${itemId}`, payload),
  moveItem: (itemId: number, direction: 'up' | 'down'): Promise<any> =>
    http.post(`/timeline-items/${itemId}/move`, { direction }),
  exports: (episodeId: number): Promise<PageResult> => http.get(`/episodes/${episodeId}/exports`),
  createExport: (episodeId: number, payload: Record<string, unknown>): Promise<any> =>
    http.post(`/episodes/${episodeId}/exports`, payload)
}

export const checklistApi = {
  get: (episodeId: number): Promise<any> => http.get(`/episodes/${episodeId}/checklist`),
  update: (itemId: number, payload: Record<string, unknown>): Promise<any> => http.patch(`/checklist/${itemId}`, payload)
}

export const reviewApi = {
  list: (params: Record<string, unknown> = {}): Promise<PageResult> => http.get('/reviews', { params }),
  stats: (): Promise<any> => http.get('/reviews/stats'),
  create: (payload: Record<string, unknown>): Promise<any> => http.post('/reviews', payload),
  decide: (id: number, payload: Record<string, unknown>): Promise<any> => http.post(`/reviews/${id}/decide`, payload)
}

export const dashboardApi = {
  overview: (): Promise<any> => http.get('/dashboard/overview'),
  trend: (days = 7): Promise<any> => http.get('/dashboard/trend', { params: { days } })
}

/** 导出文件下载地址（浏览器直接跳转，携带 query token 不安全，改用 fetch+blob） */
export async function downloadExport(episodeId: number, format: string): Promise<void> {
  const base = import.meta.env.VITE_API_BASE || '/api'
  const token = localStorage.getItem('aigc_token') || ''
  const response = await fetch(`${base}/episodes/${episodeId}/export?format=${format}`, {
    headers: { Authorization: `Bearer ${token}` }
  })
  if (!response.ok) {
    throw new Error(`导出失败：HTTP ${response.status}`)
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `第${episodeId}集成片合成单.${format}`
  link.click()
  URL.revokeObjectURL(url)
}
