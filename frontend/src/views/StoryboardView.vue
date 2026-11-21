<template>
  <div class="page">
    <div class="page-title">
      <h2>分镜工作台</h2>
      <el-tag v-if="episode" size="small" type="warning">{{ episode.title }}</el-tag>
      <span class="sub">镜号 / 景别 / 机位 / 运镜 / 时长 / 画面 / 台词 / BGM，可上下移动排序</span>
      <div style="flex: 1"></div>
      <el-button size="small" :icon="MagicStick" @click="generateAllPrompts">批量生成提示词</el-button>
      <el-button size="small" type="primary" :icon="Plus" @click="openCreate">新增分镜</el-button>
    </div>

    <el-skeleton v-if="loading" :rows="8" animated />

    <template v-else>
      <div class="toolbar">
        <span class="muted">共 {{ total }} 个分镜 · 预计 {{ totalDuration.toFixed(1) }} 秒</span>
        <div style="flex: 1"></div>
        <el-button size="small" @click="$router.push(`/episodes/${episodeId}/timeline`)">进入合成单</el-button>
        <el-button size="small" @click="refresh">刷新</el-button>
      </div>

      <el-table :data="shots" size="small" empty-text="还没有分镜，点击右上角新增">
        <el-table-column prop="shot_no" label="镜号" width="76" />
        <el-table-column label="素材" width="112">
          <template #default="{ row }">
            <el-image
              v-if="row.asset_url"
              :src="mediaUrl(row.asset_url)"
              fit="cover"
              class="thumb"
              :preview-src-list="[mediaUrl(row.asset_url)]"
            />
            <div v-else class="thumb thumb-empty">未生成</div>
          </template>
        </el-table-column>
        <el-table-column label="镜头" width="150">
          <template #default="{ row }">
            <div>{{ row.shot_size }} · {{ row.camera_angle }}</div>
            <div class="muted small">{{ row.camera_move }} · {{ row.duration_seconds }}s</div>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="画面描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="dialogue" label="台词" min-width="160" show-overflow-tooltip />
        <el-table-column prop="bgm" label="BGM" width="110" show-overflow-tooltip />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="tagType(row.status)">{{ row.status_label }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="286" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="primary" @click="buildPrompt(row)">提示词</el-button>
            <el-button link type="success" @click="openGenerate(row)">生成</el-button>
            <el-button link @click="move(row, 'up')">上移</el-button>
            <el-button link @click="move(row, 'down')">下移</el-button>
          </template>
        </el-table-column>
      </el-table>
    </template>

    <el-dialog v-model="editDialog" :title="editingId ? '编辑分镜' : '新增分镜'" width="640px">
      <el-form :model="form" label-width="92px">
        <el-form-item label="景别">
          <el-select v-model="form.shot_size" style="width: 160px">
            <el-option v-for="item in meta.shot_sizes" :key="item" :label="item" :value="item" />
          </el-select>
          <span style="width: 16px"></span>
          <el-select v-model="form.camera_angle" style="width: 140px">
            <el-option v-for="item in meta.camera_angles" :key="item" :label="item" :value="item" />
          </el-select>
          <span style="width: 16px"></span>
          <el-select v-model="form.camera_move" style="width: 120px">
            <el-option v-for="item in meta.camera_moves" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="时长（秒）">
          <el-input-number v-model="form.duration_seconds" :min="0.5" :max="120" :step="0.5" />
        </el-form-item>
        <el-form-item label="画面描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="谁、在哪、做什么、什么光线" />
        </el-form-item>
        <el-form-item label="台词">
          <el-input v-model="form.dialogue" type="textarea" :rows="2" placeholder="角色：台词" />
        </el-form-item>
        <el-form-item label="BGM / 音效">
          <el-input v-model="form.bgm" placeholder="如：钢琴单音、海浪环境音" />
        </el-form-item>
        <el-form-item label="一致性前缀">
          <div style="display: flex; gap: 8px; width: 100%">
            <el-select v-model="form.character_id" placeholder="角色" clearable style="flex: 1">
              <el-option v-for="item in characters" :key="item.id" :label="item.name" :value="item.id" />
            </el-select>
            <el-select v-model="form.scene_card_id" placeholder="场景卡" clearable style="flex: 1">
              <el-option v-for="item in sceneCards" :key="item.id" :label="item.name" :value="item.id" />
            </el-select>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialog = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="generateDialog" title="生成素材（AIGC）" width="640px">
      <el-form label-width="92px">
        <el-form-item label="正向提示词">
          <el-input v-model="genForm.prompt" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item label="负向提示词">
          <el-input v-model="genForm.negative_prompt" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="生成类型">
          <el-radio-group v-model="genForm.kind">
            <el-radio-button label="text2image">文生图</el-radio-button>
            <el-radio-button label="img2video">图生视频</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="种子">
          <el-input-number v-model="genForm.seed" :min="0" :max="4294967295" />
          <span class="muted">&nbsp;固定种子便于复现同一画面</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="generateDialog = false">取消</el-button>
        <el-button type="primary" :loading="generating" @click="submitGenerate">提交生成任务</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="promptDrawer" title="提示词预览" size="480px">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="正向">{{ currentPrompt.prompt }}</el-descriptions-item>
        <el-descriptions-item label="负向">{{ currentPrompt.negative_prompt }}</el-descriptions-item>
        <el-descriptions-item label="画风">{{ currentPrompt.style?.name }}</el-descriptions-item>
      </el-descriptions>
      <div style="margin-top: 14px; display: flex; gap: 8px">
        <el-button type="primary" size="small" @click="copyPrompt">复制正向提示词</el-button>
        <el-button size="small" @click="openGenerate(currentShot, currentPrompt)">直接生成</el-button>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { MagicStick, Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'

import { episodeApi, generationApi, metaApi, seriesApi, storyboardApi } from '@/api'
import { mediaUrl, tagType } from '@/utils/format'

const route = useRoute()
const episodeId = Number(route.params.id)

const loading = ref(true)
const episode = ref<any>(null)
const shots = ref<any[]>([])
const total = ref(0)
const totalDuration = ref(0)
const characters = ref<any[]>([])
const sceneCards = ref<any[]>([])
const meta = reactive<{ shot_sizes: string[]; camera_angles: string[]; camera_moves: string[] }>({
  shot_sizes: [],
  camera_angles: [],
  camera_moves: []
})

const editDialog = ref(false)
const editingId = ref<number | null>(null)
const form = reactive<any>({
  shot_size: '中景',
  camera_angle: '平视',
  camera_move: '固定',
  duration_seconds: 5,
  description: '',
  dialogue: '',
  bgm: '',
  character_id: null,
  scene_card_id: null
})

const generateDialog = ref(false)
const generating = ref(false)
const genForm = reactive<any>({ prompt: '', negative_prompt: '', kind: 'text2image', seed: 20240501 })
const currentShot = ref<any>(null)

const promptDrawer = ref(false)
const currentPrompt = ref<any>({})

async function refresh() {
  loading.value = true
  try {
    const data = await storyboardApi.shots(episodeId)
    shots.value = data.items
    total.value = data.total
    totalDuration.value = data.total_duration
    episode.value = data.episode
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  Object.assign(form, {
    shot_size: '中景',
    camera_angle: '平视',
    camera_move: '固定',
    duration_seconds: 5,
    description: '',
    dialogue: '',
    bgm: '',
    character_id: null,
    scene_card_id: null
  })
  editDialog.value = true
}

function openEdit(row: any) {
  editingId.value = row.id
  Object.assign(form, {
    shot_size: row.shot_size,
    camera_angle: row.camera_angle,
    camera_move: row.camera_move,
    duration_seconds: row.duration_seconds,
    description: row.description,
    dialogue: row.dialogue,
    bgm: row.bgm,
    character_id: row.character_id || null,
    scene_card_id: row.scene_card_id || null
  })
  editDialog.value = true
}

async function save() {
  if (!form.description.trim()) {
    ElMessage.warning('请填写画面描述')
    return
  }
  if (editingId.value) {
    await storyboardApi.update(editingId.value, { ...form })
  } else {
    await storyboardApi.create(episodeId, { ...form })
  }
  ElMessage.success('已保存')
  editDialog.value = false
  await refresh()
}

async function move(row: any, direction: 'up' | 'down') {
  await storyboardApi.move(row.id, direction)
  await refresh()
}

async function buildPrompt(row: any) {
  const data = await storyboardApi.promptFromShot(row.id)
  currentShot.value = row
  currentPrompt.value = data
  promptDrawer.value = true
  await refresh()
}

async function generateAllPrompts() {
  for (const row of shots.value.filter((item) => !item.prompt)) {
    await storyboardApi.promptFromShot(row.id, { save: true })
  }
  ElMessage.success('已为缺少提示词的分镜补齐')
  await refresh()
}

function openGenerate(row: any, prompt?: any) {
  currentShot.value = row
  genForm.prompt = prompt?.prompt || row?.prompt || row?.description || ''
  genForm.negative_prompt = prompt?.negative_prompt || row?.negative_prompt || ''
  genForm.kind = 'text2image'
  genForm.seed = row?.id ? 20240501 + row.id * 7 : 20240501
  generateDialog.value = true
}

async function submitGenerate() {
  if (!genForm.prompt.trim()) {
    ElMessage.warning('提示词不能为空')
    return
  }
  generating.value = true
  try {
    const task = await generationApi.create({
      prompt: genForm.prompt,
      negative_prompt: genForm.negative_prompt,
      kind: genForm.kind,
      provider: 'mock',
      seed: genForm.seed,
      series_id: episode.value?.series_id,
      episode_id: episodeId,
      shot_id: currentShot.value?.id,
      params: { steps: 24, cfg_scale: 6.5 }
    })
    ElMessage.success(`任务 #${task.id} 状态：${task.status_label}`)
    generateDialog.value = false
    promptDrawer.value = false
    await refresh()
  } finally {
    generating.value = false
  }
}

async function copyPrompt() {
  await navigator.clipboard.writeText(currentPrompt.value.prompt || '')
  ElMessage.success('已复制')
}

onMounted(async () => {
  const options = await metaApi.options()
  meta.shot_sizes = options.shot_sizes
  meta.camera_angles = options.camera_angles
  meta.camera_moves = options.camera_moves
  await refresh()
  if (episode.value?.series_id) {
    const [chars, cards] = await Promise.all([
      seriesApi.characters(episode.value.series_id),
      seriesApi.sceneCards(episode.value.series_id)
    ])
    characters.value = chars.items
    sceneCards.value = cards.items
  }
})
</script>

<style scoped>
.thumb {
  width: 88px;
  height: 56px;
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

.small {
  font-size: 11px;
}
</style>
