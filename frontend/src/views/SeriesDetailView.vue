<template>
  <div class="page">
    <div class="page-title">
      <h2>{{ series?.title || '项目详情' }}</h2>
      <el-tag v-if="series" size="small" :type="tagType(series.status)">{{ series.status_label }}</el-tag>
      <span class="sub">{{ series?.genre }} · {{ series?.style }} · {{ series?.platform_label }}</span>
      <div style="flex: 1"></div>
      <el-button size="small" @click="$router.push('/series')">返回列表</el-button>
    </div>

    <el-skeleton v-if="loading" :rows="6" animated />

    <template v-else-if="series">
      <div class="panel summary">
        <div class="summary-main">
          <el-image v-if="series.cover_url" :src="mediaUrl(series.cover_url)" fit="cover" class="cover" />
          <div class="summary-text">
            <p class="logline">{{ series.logline }}</p>
            <p class="muted">{{ series.synopsis || '还没有补充故事梗概。' }}</p>
            <div class="meta-row">
              <span>规划 {{ series.episodes_planned }} 集</span>
              <span>单集 {{ series.target_duration }} 秒</span>
              <span>角色 {{ series.character_count }} 个</span>
              <span>场景 {{ series.scene_count }} 个</span>
              <span>创建人 {{ series.owner_name || '-' }}</span>
            </div>
          </div>
        </div>
        <div class="summary-actions">
          <el-button type="primary" plain :icon="Edit" @click="openEdit">编辑项目</el-button>
          <el-button :icon="User" @click="$router.push(`/series/${series.id}/characters`)">角色与场景卡</el-button>
          <el-button :icon="Delete" type="danger" plain @click="remove">删除项目</el-button>
        </div>
      </div>

      <el-tabs v-model="tab" class="tabs">
        <el-tab-pane label="分集管理" name="episodes">
          <div class="toolbar">
            <el-button size="small" type="primary" :icon="Plus" @click="episodeDialog = true">新增分集</el-button>
            <span class="muted">共 {{ episodes.length }} 集，点击「分镜」进入工作台</span>
          </div>
          <el-table :data="episodes" size="small" empty-text="还没有分集">
            <el-table-column prop="number" label="集" width="60" />
            <el-table-column prop="title" label="标题" min-width="180" />
            <el-table-column prop="summary" label="简介" show-overflow-tooltip />
            <el-table-column label="状态" width="110">
              <template #default="{ row }">
                <el-tag size="small" :type="tagType(row.status)">{{ row.status_label }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="260" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="$router.push(`/episodes/${row.id}/storyboard`)">分镜</el-button>
                <el-button link type="primary" @click="$router.push(`/episodes/${row.id}/timeline`)">合成单</el-button>
                <el-button link @click="editEpisode(row)">编辑</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="剧本与场次" name="script">
          <div class="toolbar">
            <el-select v-model="currentEpisodeId" placeholder="选择分集" style="width: 240px" @change="loadScript">
              <el-option v-for="ep in episodes" :key="ep.id" :label="`第 ${ep.number} 集 · ${ep.title}`" :value="ep.id" />
            </el-select>
            <el-select v-model="structure" style="width: 150px">
              <el-option v-for="item in structures" :key="item.name" :label="item.name" :value="item.name" />
            </el-select>
            <el-button type="primary" size="small" :loading="savingScript" @click="saveScript">保存为新版本</el-button>
            <span class="muted" v-if="script">当前版本 v{{ script.version }} · 共 {{ versions.length }} 个版本</span>
          </div>

          <div class="script-grid">
            <div class="panel">
              <el-input v-model="content" type="textarea" :rows="18" placeholder="按幕/场写剧本：角色、动作、对白……" />
              <div class="muted small" style="margin-top: 8px">
                保存时自动生成新版本，历史版本可在右侧回看，保证剧本可追溯。
              </div>
            </div>
            <div class="panel">
              <div class="panel-head"><strong>版本历史</strong></div>
              <el-timeline>
                <el-timeline-item
                  v-for="item in versions"
                  :key="item.id"
                  :timestamp="formatDate(item.created_at)"
                  :type="item.is_current ? 'primary' : 'info'"
                >
                  v{{ item.version }} · {{ item.structure }} · {{ item.content.length }} 字
                  <el-button v-if="!item.is_current" link size="small" @click="previewVersion(item)">查看</el-button>
                </el-timeline-item>
              </el-timeline>
            </div>
          </div>

          <div class="panel" style="margin-top: 14px">
            <div class="panel-head">
              <strong>场次清单</strong>
              <el-button size="small" :icon="Plus" @click="sceneDialog = true">新增场次</el-button>
            </div>
            <el-table :data="scenes" size="small" empty-text="还没有场次">
              <el-table-column prop="seq" label="序" width="56" />
              <el-table-column prop="title" label="场次" min-width="140" />
              <el-table-column prop="location" label="地点" width="140" />
              <el-table-column prop="time_of_day" label="时间" width="80" />
              <el-table-column prop="action_text" label="动作" show-overflow-tooltip />
              <el-table-column prop="dialogue" label="对白" show-overflow-tooltip />
              <el-table-column label="时长" width="80">
                <template #default="{ row }">{{ row.duration_seconds }}s</template>
              </el-table-column>
              <el-table-column label="排序" width="120" fixed="right">
                <template #default="{ row }">
                  <el-button link @click="moveScene(row, 'up')">上移</el-button>
                  <el-button link @click="moveScene(row, 'down')">下移</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>
    </template>

    <el-dialog v-model="editDialog" title="编辑项目" width="520px">
      <el-form :model="editForm" label-width="92px">
        <el-form-item label="标题"><el-input v-model="editForm.title" /></el-form-item>
        <el-form-item label="梗概"><el-input v-model="editForm.logline" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="故事梗概"><el-input v-model="editForm.synopsis" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="状态">
          <el-select v-model="editForm.status" style="width: 100%">
            <el-option label="策划中" value="draft" />
            <el-option label="制作中" value="in_production" />
            <el-option label="审核中" value="review" />
            <el-option label="已完成" value="completed" />
            <el-option label="已归档" value="archived" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialog = false">取消</el-button>
        <el-button type="primary" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="episodeDialog" title="新增分集" width="480px">
      <el-form :model="episodeForm" label-width="80px">
        <el-form-item label="标题"><el-input v-model="episodeForm.title" placeholder="如：第 4 集 · 夜航" /></el-form-item>
        <el-form-item label="简介"><el-input v-model="episodeForm.summary" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="episodeDialog = false">取消</el-button>
        <el-button type="primary" @click="createEpisode">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="sceneDialog" title="新增场次" width="560px">
      <el-form :model="sceneForm" label-width="80px">
        <el-form-item label="场次标题"><el-input v-model="sceneForm.title" /></el-form-item>
        <el-form-item label="地点"><el-input v-model="sceneForm.location" /></el-form-item>
        <el-form-item label="时间"><el-input v-model="sceneForm.time_of_day" placeholder="夜 / 黄昏 / 清晨" /></el-form-item>
        <el-form-item label="角色"><el-input v-model="sceneForm.characters" placeholder="林澈、苏眠" /></el-form-item>
        <el-form-item label="动作"><el-input v-model="sceneForm.action_text" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="对白"><el-input v-model="sceneForm.dialogue" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="时长">
          <el-input-number v-model="sceneForm.duration_seconds" :min="3" :max="600" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="sceneDialog = false">取消</el-button>
        <el-button type="primary" @click="createScene">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { Delete, Edit, Plus, User } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { episodeApi, metaApi, seriesApi } from '@/api'
import { formatDate, mediaUrl, tagType } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const seriesId = Number(route.params.id)

const loading = ref(true)
const series = ref<any>(null)
const episodes = ref<any[]>([])
const tab = ref('episodes')
const structures = ref<any[]>([])

const currentEpisodeId = ref<number | null>(null)
const script = ref<any>(null)
const versions = ref<any[]>([])
const content = ref('')
const structure = ref('三幕式')
const savingScript = ref(false)
const scenes = ref<any[]>([])

const editDialog = ref(false)
const editForm = reactive({ title: '', logline: '', synopsis: '', status: 'draft' })
const episodeDialog = ref(false)
const episodeForm = reactive({ title: '', summary: '' })
const sceneDialog = ref(false)
const sceneForm = reactive({
  title: '',
  location: '',
  time_of_day: '夜',
  characters: '',
  action_text: '',
  dialogue: '',
  duration_seconds: 20
})

async function load() {
  loading.value = true
  try {
    series.value = await seriesApi.detail(seriesId)
    const list = await seriesApi.episodes(seriesId)
    episodes.value = list.items
    if (!currentEpisodeId.value && episodes.value.length) {
      currentEpisodeId.value = episodes.value[0].id
    }
  } finally {
    loading.value = false
  }
}

async function loadScript() {
  if (!currentEpisodeId.value) return
  const data = await episodeApi.script(currentEpisodeId.value)
  script.value = data.script
  versions.value = data.versions
  content.value = data.script?.content || ''
  structure.value = data.script?.structure || '三幕式'
  const sceneList = await episodeApi.scenes(currentEpisodeId.value)
  scenes.value = sceneList.items
}

async function saveScript() {
  if (!currentEpisodeId.value || !content.value.trim()) {
    ElMessage.warning('剧本内容不能为空')
    return
  }
  savingScript.value = true
  try {
    await episodeApi.saveScript(currentEpisodeId.value, { content: content.value, structure: structure.value })
    ElMessage.success('已保存为新版本')
    await loadScript()
    await load()
  } finally {
    savingScript.value = false
  }
}

function previewVersion(item: any) {
  content.value = item.content
  ElMessage.info(`正在查看 v${item.version}，保存后会生成新版本`)
}

async function moveScene(row: any, direction: 'up' | 'down') {
  await episodeApi.moveScene(row.id, direction)
  await loadScript()
}

function openEdit() {
  Object.assign(editForm, {
    title: series.value.title,
    logline: series.value.logline,
    synopsis: series.value.synopsis,
    status: series.value.status
  })
  editDialog.value = true
}

async function saveEdit() {
  await seriesApi.update(seriesId, { ...editForm })
  ElMessage.success('已保存')
  editDialog.value = false
  await load()
}

async function remove() {
  await ElMessageBox.confirm('删除后分集、分镜、素材都会一并移除，确定继续？', '删除项目', { type: 'warning' })
  await seriesApi.remove(seriesId)
  ElMessage.success('已删除')
  router.push('/series')
}

async function createEpisode() {
  if (!episodeForm.title.trim()) {
    ElMessage.warning('请填写分集标题')
    return
  }
  await seriesApi.createEpisode(seriesId, { ...episodeForm })
  ElMessage.success('分集已创建')
  episodeDialog.value = false
  Object.assign(episodeForm, { title: '', summary: '' })
  await load()
}

function editEpisode(row: any) {
  currentEpisodeId.value = row.id
  tab.value = 'script'
  loadScript()
}

async function createScene() {
  if (!currentEpisodeId.value) {
    ElMessage.warning('请先选择分集')
    return
  }
  await episodeApi.createScene(currentEpisodeId.value, { ...sceneForm })
  ElMessage.success('场次已创建')
  sceneDialog.value = false
  await loadScript()
}

onMounted(async () => {
  const options = await metaApi.options()
  structures.value = options.structures
  await load()
  if (currentEpisodeId.value) {
    await loadScript()
  }
})
</script>

<style scoped>
.summary {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
}

.summary-main {
  display: flex;
  gap: 16px;
}

.cover {
  width: 148px;
  height: 92px;
  border-radius: 10px;
}

.logline {
  margin: 0 0 6px;
  font-size: 15px;
  font-weight: 600;
}

.meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  color: var(--aigc-muted);
  font-size: 12px;
  margin-top: 10px;
}

.summary-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.summary-actions .el-button {
  margin-left: 0;
}

.tabs {
  margin-top: 12px;
}

.script-grid {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 14px;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.small {
  font-size: 11px;
}
</style>
