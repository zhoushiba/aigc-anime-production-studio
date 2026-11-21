<template>
  <div class="page">
    <div class="page-title">
      <h2>成片合成单</h2>
      <span class="sub">{{ timeline?.name || '按镜头顺序合成，导出 CSV / JSON / SRT / ZIP' }}</span>
      <div style="flex: 1"></div>
      <el-button size="small" @click="autoFill">按分镜重新生成</el-button>
      <el-dropdown @command="exportAs">
        <el-button size="small" type="primary" :icon="Download">
          导出<el-icon class="el-icon--right"><ArrowDown /></el-icon>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="csv">导出 CSV</el-dropdown-item>
            <el-dropdown-item command="json">导出 JSON</el-dropdown-item>
            <el-dropdown-item command="srt">导出字幕 SRT</el-dropdown-item>
            <el-dropdown-item command="zip">打包 ZIP</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <el-skeleton v-if="loading" :rows="6" animated />

    <template v-else>
      <div class="stat-grid">
        <div class="stat-card">
          <div class="label">镜头数</div>
          <div class="value">{{ summary.shot_count || 0 }}</div>
        </div>
        <div class="stat-card">
          <div class="label">总时长</div>
          <div class="value">{{ formatDuration(summary.total_duration) }}</div>
        </div>
        <div class="stat-card">
          <div class="label">已配字幕</div>
          <div class="value">{{ summary.subtitle_count || 0 }}</div>
        </div>
        <div class="stat-card">
          <div class="label">质检完成度</div>
          <div class="value">{{ checklistDone }} / {{ checklist.length }}</div>
        </div>
      </div>

      <div class="panel" style="margin-top: 14px">
        <div class="panel-head">
          <strong>镜头清单</strong>
          <span class="muted">上移 / 下移调整成片顺序，字幕与转场在此确定</span>
        </div>
        <el-table :data="items" size="small" empty-text="还没有镜头，点击「按分镜重新生成」">
          <el-table-column prop="seq" label="序" width="56" />
          <el-table-column prop="shot_no" label="镜号" width="84" />
          <el-table-column label="素材" width="108">
            <template #default="{ row }">
              <el-image v-if="row.asset_url" :src="mediaUrl(row.asset_url)" fit="cover" class="thumb" />
              <div v-else class="thumb thumb-empty">未选素材</div>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="画面" min-width="180" show-overflow-tooltip />
          <el-table-column label="台词 / 字幕" min-width="200">
            <template #default="{ row }">
              <el-input
                v-model="row.subtitle"
                size="small"
                placeholder="字幕文本"
                @change="(value: string) => updateItem(row, { subtitle: value })"
              />
            </template>
          </el-table-column>
          <el-table-column label="时长" width="100">
            <template #default="{ row }">
              <el-input-number
                v-model="row.duration_seconds"
                size="small"
                :min="0.5"
                :max="120"
                :step="0.5"
                :controls="false"
                style="width: 74px"
                @change="(value: number) => updateItem(row, { duration_seconds: value })"
              />
            </template>
          </el-table-column>
          <el-table-column label="转场" width="120">
            <template #default="{ row }">
              <el-select v-model="row.transition" size="small" @change="(value: string) => updateItem(row, { transition: value })">
                <el-option label="直切" value="cut" />
                <el-option label="叠化" value="dissolve" />
                <el-option label="淡入淡出" value="fade" />
                <el-option label="划像" value="wipe" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="排序" width="108" fixed="right">
            <template #default="{ row }">
              <el-button link @click="moveItem(row, 'up')">上移</el-button>
              <el-button link @click="moveItem(row, 'down')">下移</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="two-col">
        <div class="panel">
          <div class="panel-head">
            <strong>成片质检清单</strong>
            <span class="muted">逐项确认后才算通过审核</span>
          </div>
          <div v-for="item in checklist" :key="item.id" class="check-row">
            <el-checkbox v-model="item.checked" @change="(value: boolean) => updateChecklist(item, value)">
              {{ item.label }}
            </el-checkbox>
            <el-tag v-if="item.checked_by" size="small" type="success">{{ item.checked_by }}</el-tag>
          </div>
        </div>

        <div class="panel">
          <div class="panel-head">
            <strong>导出记录</strong>
            <el-button size="small" @click="createExportRecord">生成导出文件（ZIP）</el-button>
          </div>
          <el-table :data="exportJobs" size="small" empty-text="还没有导出记录">
            <el-table-column prop="format" label="格式" width="72" />
            <el-table-column label="镜头" width="72">
              <template #default="{ row }">{{ row.payload?.shot_count }}</template>
            </el-table-column>
            <el-table-column label="时长" width="92">
              <template #default="{ row }">{{ formatDuration(row.payload?.total_duration) }}</template>
            </el-table-column>
            <el-table-column label="生成时间">
              <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ArrowDown, Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'

import { checklistApi, downloadExport, timelineApi } from '@/api'
import { formatDate, formatDuration, mediaUrl } from '@/utils/format'

const route = useRoute()
const episodeId = Number(route.params.id)

const loading = ref(true)
const timeline = ref<any>(null)
const items = ref<any[]>([])
const summary = reactive<{ shot_count: number; total_duration: number; subtitle_count: number }>({
  shot_count: 0,
  total_duration: 0,
  subtitle_count: 0
})
const checklist = ref<any[]>([])
const exportJobs = ref<any[]>([])

const checklistDone = computed(() => checklist.value.filter((item) => item.checked).length)

async function load() {
  loading.value = true
  try {
    const data = await timelineApi.get(episodeId)
    timeline.value = data.timeline
    items.value = data.items
    Object.assign(summary, data.summary)
    const check = await checklistApi.get(episodeId)
    checklist.value = check.items
    const exports = await timelineApi.exports(episodeId)
    exportJobs.value = exports.items
  } finally {
    loading.value = false
  }
}

async function updateItem(row: any, payload: Record<string, unknown>) {
  await timelineApi.updateItem(row.id, payload)
  const data = await timelineApi.get(episodeId)
  Object.assign(summary, data.summary)
}

async function moveItem(row: any, direction: 'up' | 'down') {
  await timelineApi.moveItem(row.id, direction)
  await load()
}

async function autoFill() {
  await timelineApi.autoFill(episodeId)
  ElMessage.success('已按当前分镜重建镜头清单')
  await load()
}

async function exportAs(format: string) {
  try {
    await downloadExport(episodeId, format)
    ElMessage.success(`已导出 ${format.toUpperCase()}`)
  } catch (error) {
    ElMessage.error('导出失败，请确认已登录')
  }
}

async function createExportRecord() {
  await timelineApi.createExport(episodeId, { format: 'zip' })
  ElMessage.success('导出文件已生成，可在记录中查看')
  await load()
}

async function updateChecklist(item: any, checked: boolean) {
  await checklistApi.update(item.id, { checked, note: item.note || '' })
  await load()
}

onMounted(load)
</script>

<style scoped>
.thumb {
  width: 84px;
  height: 52px;
  border-radius: 6px;
  display: block;
}

.thumb-empty {
  display: grid;
  place-items: center;
  font-size: 10px;
  color: var(--aigc-muted);
  background: #10141c;
  border: 1px dashed var(--aigc-line);
}

.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-top: 14px;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.check-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px dashed var(--aigc-line);
}
</style>
