<template>
  <div class="page">
    <div class="page-title">
      <h2>生成任务</h2>
      <span class="sub">文生图 / 图生视频，状态：排队 → 生成中 → 成功 / 失败 / 超时</span>
      <div style="flex: 1"></div>
      <el-switch v-model="autoRefresh" active-text="自动刷新" style="margin-right: 12px" />
      <el-button size="small" :icon="Refresh" @click="load">刷新</el-button>
      <el-button size="small" type="primary" :icon="Plus" @click="createDialog = true">新建任务</el-button>
    </div>

    <div class="stat-grid">
      <div class="stat-card">
        <div class="label">任务总数</div>
        <div class="value">{{ stats.total || 0 }}</div>
        <div class="muted">成功 {{ stats.succeeded || 0 }} · 失败 {{ stats.failed || 0 }} · 超时 {{ stats.timeout || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="label">成功率</div>
        <div class="value">{{ stats.success_rate || 0 }}%</div>
        <div class="muted">排队 {{ stats.queued || 0 }} · 生成中 {{ stats.running || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="label">平均耗时</div>
        <div class="value">{{ formatMs(stats.avg_duration_ms) }}</div>
        <div class="muted">含 Mock 生成与落盘耗时</div>
      </div>
      <div class="stat-card">
        <div class="label">可用生成服务</div>
        <div class="value">{{ providers.filter((item) => item.available).length }} / {{ providers.length }}</div>
        <div class="muted">{{ providers.map((item) => item.name).join(' · ') }}</div>
      </div>
    </div>

    <div class="toolbar" style="margin-top: 14px">
      <el-select v-model="query.status" placeholder="全部状态" clearable style="width: 150px" @change="load">
        <el-option label="排队中" value="queued" />
        <el-option label="生成中" value="running" />
        <el-option label="成功" value="succeeded" />
        <el-option label="失败" value="failed" />
        <el-option label="超时" value="timeout" />
      </el-select>
      <el-select v-model="query.kind" placeholder="全部类型" clearable style="width: 150px" @change="load">
        <el-option label="文生图" value="text2image" />
        <el-option label="图生视频" value="img2video" />
      </el-select>
      <span class="muted">共 {{ total }} 个任务</span>
    </div>

    <el-table v-loading="loading" :data="items" size="small" empty-text="还没有生成任务">
      <el-table-column prop="id" label="#" width="60" />
      <el-table-column label="素材" width="100">
        <template #default="{ row }">
          <el-image v-if="row.asset_url" :src="mediaUrl(row.asset_url)" fit="cover" class="thumb" />
          <div v-else class="thumb thumb-empty">-</div>
        </template>
      </el-table-column>
      <el-table-column prop="kind_label" label="类型" width="96" />
      <el-table-column prop="prompt" label="正向提示词" min-width="230" show-overflow-tooltip />
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag size="small" :type="tagType(row.status)">{{ row.status_label }}</el-tag>
          <el-progress
            v-if="row.status === 'running'"
            :percentage="row.progress"
            :show-text="false"
            :stroke-width="4"
            style="margin-top: 4px"
          />
        </template>
      </el-table-column>
      <el-table-column prop="provider" label="服务" width="90" />
      <el-table-column label="耗时" width="82">
        <template #default="{ row }">{{ formatMs(row.duration_ms) }}</template>
      </el-table-column>
      <el-table-column label="创建时间" width="150">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="190" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDetail(row)">详情</el-button>
          <el-button v-if="!row.finished" link type="warning" @click="cancel(row)">取消</el-button>
          <el-button v-if="row.finished" link type="success" @click="retry(row)">重试</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="createDialog" title="新建生成任务" width="620px">
      <el-form :model="form" label-width="92px">
        <el-form-item label="提示词" required>
          <el-input v-model="form.prompt" type="textarea" :rows="4" placeholder="主体 + 动作 + 镜头 + 画风 + 光影 + 画质" />
        </el-form-item>
        <el-form-item label="负向提示词">
          <el-input v-model="form.negative_prompt" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="生成类型">
          <el-radio-group v-model="form.kind">
            <el-radio-button label="text2image">文生图</el-radio-button>
            <el-radio-button label="img2video">图生视频</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="生成服务">
          <el-select v-model="form.provider" style="width: 100%">
            <el-option
              v-for="item in providers"
              :key="item.name"
              :label="`${item.label}${item.available ? '' : '（未配置）'}`"
              :value="item.name"
              :disabled="!item.available"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="固定种子">
          <el-input-number v-model="form.seed" :min="0" :max="4294967295" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="create">提交</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailDrawer" title="任务详情" size="520px">
      <el-descriptions v-if="detail" :column="1" border>
        <el-descriptions-item label="任务编号">#{{ detail.id }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag size="small" :type="tagType(detail.status)">{{ detail.status_label }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="生成服务">{{ detail.provider }}</el-descriptions-item>
        <el-descriptions-item label="耗时">{{ formatMs(detail.duration_ms) }}</el-descriptions-item>
        <el-descriptions-item label="种子">{{ detail.seed }}</el-descriptions-item>
        <el-descriptions-item label="正向提示词">{{ detail.prompt }}</el-descriptions-item>
        <el-descriptions-item label="负向提示词">{{ detail.negative_prompt || '-' }}</el-descriptions-item>
        <el-descriptions-item label="错误信息">{{ detail.error || '-' }}</el-descriptions-item>
      </el-descriptions>
      <el-image
        v-if="detail?.asset_url"
        :src="mediaUrl(detail.asset_url)"
        fit="contain"
        style="width: 100%; margin-top: 14px; border-radius: 10px"
      />
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { Plus, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'

import { generationApi } from '@/api'
import { formatDate, formatMs, mediaUrl, tagType } from '@/utils/format'

const loading = ref(false)
const creating = ref(false)
const items = ref<any[]>([])
const total = ref(0)
const stats = ref<any>({})
const providers = ref<any[]>([])
const query = reactive({ status: '', kind: '' })
const autoRefresh = ref(true)
let timer: number | undefined

const createDialog = ref(false)
const form = reactive({
  prompt: 'silver haired girl standing on a lighthouse at night, cel shading anime style, cinematic lighting, masterpiece',
  negative_prompt: 'lowres, bad anatomy, watermark',
  kind: 'text2image',
  provider: 'mock',
  seed: 20240501
})

const detailDrawer = ref(false)
const detail = ref<any>(null)

async function load() {
  loading.value = true
  try {
    const [list, statsData] = await Promise.all([
      generationApi.list({ status: query.status || undefined, kind: query.kind || undefined, size: 50 }),
      generationApi.stats()
    ])
    items.value = list.items
    total.value = list.total
    stats.value = statsData
  } finally {
    loading.value = false
  }
}

async function create() {
  if (!form.prompt.trim()) {
    ElMessage.warning('请填写提示词')
    return
  }
  creating.value = true
  try {
    const task = await generationApi.create({ ...form, params: { steps: 24, cfg_scale: 6.5 } })
    ElMessage.success(`任务 #${task.id} 已提交，当前状态：${task.status_label}`)
    createDialog.value = false
    await load()
  } finally {
    creating.value = false
  }
}

async function cancel(row: any) {
  await generationApi.cancel(row.id)
  ElMessage.success('已取消')
  await load()
}

async function retry(row: any) {
  await generationApi.retry(row.id, { params: { steps: 24 } })
  ElMessage.success('已重新提交')
  await load()
}

async function openDetail(row: any) {
  detail.value = await generationApi.detail(row.id)
  detailDrawer.value = true
}

onMounted(async () => {
  const providerData = await generationApi.providers()
  providers.value = providerData.items
  await load()
  timer = window.setInterval(() => {
    if (autoRefresh.value) {
      load()
    }
  }, 4000)
})

onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<style scoped>
.thumb {
  width: 76px;
  height: 48px;
  border-radius: 6px;
  display: block;
}

.thumb-empty {
  display: grid;
  place-items: center;
  font-size: 11px;
  color: var(--aigc-muted);
  background: #10141c;
  border: 1px dashed var(--aigc-line);
}
</style>
