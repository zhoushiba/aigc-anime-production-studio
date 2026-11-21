/** 通用格式化工具：媒体地址、状态标签、时间、时长 */

export function mediaUrl(path?: string | null): string {
  if (!path) return ''
  if (path.startsWith('http')) return path
  if (path.startsWith('/media/')) return path
  return `/media/${path.replace(/^\/+/, '')}`
}

const TAG_TYPES: Record<string, string> = {
  succeeded: 'success',
  running: 'warning',
  queued: 'info',
  failed: 'danger',
  timeout: 'danger',
  canceled: 'info',
  selected: 'success',
  candidate: 'info',
  rejected: 'danger',
  archived: 'info',
  approved: 'success',
  pending: 'warning',
  in_production: 'warning',
  completed: 'success',
  draft: 'info',
  review: 'warning',
  storyboard: 'warning',
  scripting: 'info',
  generated: 'success',
  prompted: 'warning'
}

export function tagType(status?: string): string {
  return TAG_TYPES[status || ''] || 'info'
}

export function formatDate(value?: string | null): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

export function formatDuration(seconds?: number | null): string {
  if (!seconds && seconds !== 0) return '-'
  if (seconds < 60) return `${Number(seconds).toFixed(1)}s`
  const minutes = Math.floor(seconds / 60)
  const rest = Math.round(seconds % 60)
  return `${minutes}分${rest}秒`
}

export function formatMs(ms?: number | null): string {
  if (ms === null || ms === undefined) return '-'
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

export function formatSize(bytes?: number | null): string {
  if (!bytes) return '-'
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
  return `${(bytes / 1024 / 1024).toFixed(2)}MB`
}
