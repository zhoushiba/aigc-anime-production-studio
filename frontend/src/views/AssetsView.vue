<template>
  <div class="page">
    <div class="page-title">
      <h2>素材库</h2>
      <span class="sub">按项目 / 角色 / 场次归类，评分、入选、淘汰与二次优化重绘</span>
      <div style="flex: 1"></div>
      <el-button size="small" :disabled="!selection.length" @click="batch('select')">
        批量入选（{{ selection.length }}）
      </el-button>
      <el-button size="small" :disabled="!selection.length" @click="batch('reject')">批量淘汰</el-button>
    </div>

    <div class="stat-grid">
      <div class="stat-card">
        <div class="label">素材总数</div>
        <div class="value">{{ stats.total || 0 }}</div>
        <div class="muted">入选 {{ stats.selected || 0 }} · 候选 {{ stats.candidate || 0 }} · 淘汰 {{ stats.rejected || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="label">平均评分</div>
        <div class="value">{{ stats.avg_rating || 0 }}</div>
        <div class="muted">满分 5 分</div>
      </div>
      <div class="stat-card">
        <div class="label">占用空间</div>
        <div class="value">{{ stats.total_size_mb || 0 }} MB</div>
        <div class="muted">PNG 主图 + JPEG 缩略图</div>
      </div>
      <div class="stat-card">
        <div class="label">类型分布</div>
        <div class="value">{{ Object.keys(stats.by_kind || {}).length }} 类</div>
        <div class="muted">{{ formatKinds(stats.by_kind) }}</div>
      </div>
    </div>

    <div class="toolbar" style="margin-top: 14px">
      <el-select v-model="query.status" placeholder="全部状态" clearable style="width: 140px" @change="load">
        <el-option label="候选" value="candidate" />
        <el-option label="已入选" value="selected" />
        <el-option label="已淘汰" value="rejected" />
        <el-option label="已归档" value="archived" />
      </el-select>
      <el-input v-model="query.keyword" placeholder="搜索标题 / 提示词" clearable style="width: 240px" @change="load" />
      <span class="muted">共 {{ total }} 张素材</span>
    </div>

    <el-skeleton v-if="loading" :rows="6" animated />
    <template v-else>
      <el-empty v-if="!items.length" description="还没有素材，去分镜工作台生成第一张图" />
      <div class="asset-grid">
        <div v-for="asset in items" :key="asset.id" class="asset-card">
          <div class="asset-cover">
            <el-checkbox v-model="selection" :label="asset.id" class="picker" @change="toggle(asset.id)" />
            <el-image
              :src="mediaUrl(asset.thumb_url || asset.url)"
              fit="cover"
              class="asset-img"
              :preview-src-list="[mediaUrl(asset.url)]"
            />
            <el-tag class="asset-tag" size="small" :type="tagType(asset.status)">{{ asset.status_label }}</el-tag>
          </div>
          <div class="asset-body">
            <div class="asset-title" :title="asset.title">{{ asset.title }}</div>
            <div class="muted small">{{ asset.width }}×{{ asset.height }} · {{ formatSize(asset.file_size) }} · seed {{ asset.seed }}</div>
            <el-rate :model-value="asset.rating || 0" :max="5" size="small" @change="(value: number) => rate(asset, value)" />
            <div class="asset-actions">
              <el-button link size="small" type="success" @click="update(asset, { status: 'selected' })">入选</el-button>
              <el-button link size="small" type="danger" @click="update(asset, { status: 'rejected' })">淘汰</el-button>
              <el-button link size="small" type="primary" @click="openRevise(asset)">二次优化</el-button>
            </div>
          </div>
        </div>
      </div>
    </template>

    <el-dialog v-model="reviseDialog" title="二次优化（问题标注 → 追加修正词 → 重绘）" width="620px">
      <el-form label-width="92px">
        <el-form-item label="问题标注">
          <el-checkbox-group v-model="reviseForm.issues">
            <el-checkbox v-for="item in issues" :key="item.key" :label="item.key">{{ item.label }}</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="修正说明">
          <el-input v-model="reviseForm.note" type="textarea" :rows="2" placeholder="如：手部结构崩坏，需要重绘双手" />
        </el-form-item>
        <el-form-item label="原提示词">
          <el-input :model-value="reviseAsset?.prompt" type="textarea" :rows="3" readonly />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reviseDialog = false">取消</el-button>
        <el-button type="primary" :loading="revising" @click="submitRevise">提交重绘</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'

import { assetApi, promptApi } from '@/api'
import { formatSize, mediaUrl, tagType } from '@/utils/format'

const loading = ref(false)
const items = ref<any[]>([])
const total = ref(0)
const stats = ref<any>({})
const query = reactive({ status: '', keyword: '' })
const selection = ref<number[]>([])

const issues = ref<any[]>([])
const reviseDialog = ref(false)
const revising = ref(false)
const reviseAsset = ref<any>(null)
const reviseForm = reactive<{ issues: string[]; note: string }>({ issues: [], note: '' })

function formatKinds(byKind: Record<string, number> = {}): string {
  return Object.entries(byKind)
    .map(([key, value]) => `${key}:${value}`)
    .join(' · ')
}

async function load() {
  loading.value = true
  try {
    const [list, statsData] = await Promise.all([
      assetApi.list({ status: query.status || undefined, keyword: query.keyword || undefined, size: 60 }),
      assetApi.stats()
    ])
    items.value = list.items
    total.value = list.total
    stats.value = statsData
    selection.value = selection.value.filter((id) => items.value.some((item) => item.id === id))
  } finally {
    loading.value = false
  }
}

function toggle(id: number) {
  if (!selection.value.includes(id)) {
    selection.value.push(id)
  } else {
    selection.value = selection.value.filter((item) => item !== id)
  }
}

async function rate(asset: any, score: number) {
  await assetApi.rate(asset.id, { score, comment: '' })
  asset.rating = score
  ElMessage.success(`已评分 ${score} 分`)
  const statsData = await assetApi.stats()
  stats.value = statsData
}

async function update(asset: any, payload: Record<string, unknown>) {
  await assetApi.update(asset.id, payload)
  ElMessage.success('已更新')
  await load()
}

async function batch(action: string) {
  await assetApi.batch({ ids: selection.value, action })
  ElMessage.success(action === 'select' ? '已批量入选' : '已批量淘汰')
  selection.value = []
  await load()
}

function openRevise(asset: any) {
  reviseAsset.value = asset
  reviseForm.issues = []
  reviseForm.note = ''
  reviseDialog.value = true
}

async function submitRevise() {
  if (!reviseForm.issues.length) {
    ElMessage.warning('请至少标注一个问题')
    return
  }
  revising.value = true
  try {
    const data = await assetApi.revise(reviseAsset.value.id, { ...reviseForm })
    ElMessage.success(`已重绘生成新素材 #${data.new_asset.id}`)
    reviseDialog.value = false
    await load()
  } finally {
    revising.value = false
  }
}

onMounted(async () => {
  const data = await promptApi.issues()
  issues.value = data.items
  await load()
})
</script>

<style scoped>
.asset-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(226px, 1fr));
  gap: 14px;
}

.asset-card {
  background: linear-gradient(180deg, rgba(27, 34, 48, 0.94), rgba(21, 26, 36, 0.94));
  border: 1px solid var(--aigc-line);
  border-radius: 12px;
  overflow: hidden;
}

.asset-cover {
  position: relative;
}

.asset-img {
  width: 100%;
  height: 168px;
  display: block;
}

.picker {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 2;
  background: rgba(10, 13, 19, 0.7);
  border-radius: 6px;
  padding: 2px 6px;
}

.asset-tag {
  position: absolute;
  top: 8px;
  right: 8px;
}

.asset-body {
  padding: 10px 12px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.asset-title {
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.small {
  font-size: 11px;
}

.asset-actions {
  display: flex;
  gap: 6px;
  margin-top: 2px;
}
</style>
