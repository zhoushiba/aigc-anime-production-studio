<template>
  <div class="page">
    <div class="page-title">
      <h2>提示词工作台</h2>
      <span class="sub">公式：主体 + 动作 + 镜头语言 + 画风 + 光影 + 画质词 + 负向词</span>
      <div style="flex: 1"></div>
      <el-button size="small" @click="copyAll">复制提示词</el-button>
    </div>

    <div class="studio">
      <div class="panel">
        <div class="panel-head"><strong>提示词构建器</strong><span class="muted">改哪一项都能立即看到组合结果</span></div>
        <el-form label-width="88px">
          <el-form-item label="主体">
            <el-input v-model="form.subject" placeholder="银发少女站在灯塔顶端" />
          </el-form-item>
          <el-form-item label="动作">
            <el-input v-model="form.action" placeholder="回头看向镜头，披风被风吹起" />
          </el-form-item>
          <el-form-item label="景别 / 机位">
            <el-select v-model="form.shot_size" style="width: 128px">
              <el-option v-for="item in meta.shot_sizes" :key="item" :label="item" :value="item" />
            </el-select>
            <span style="width: 12px"></span>
            <el-select v-model="form.camera_angle" style="width: 128px">
              <el-option v-for="item in meta.camera_angles" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="运镜">
            <el-radio-group v-model="form.camera_move">
              <el-radio-button v-for="item in meta.camera_moves" :key="item" :label="item" />
            </el-radio-group>
          </el-form-item>
          <el-form-item label="画风">
            <el-select v-model="form.style" style="width: 100%">
              <el-option v-for="item in meta.styles" :key="item.key" :label="item.name" :value="item.name" />
            </el-select>
          </el-form-item>
          <el-form-item label="光影">
            <el-select v-model="form.lighting" style="width: 100%" clearable>
              <el-option v-for="item in lightingOptions" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="画质词">
            <el-input v-model="form.quality" placeholder="masterpiece, best quality, 8k" />
          </el-form-item>
          <el-form-item label="一致性">
            <el-switch v-model="form.consistency" active-text="追加角色/场景一致性与固定种子" />
          </el-form-item>
          <el-button type="primary" :loading="building" @click="build">生成提示词</el-button>
        </el-form>
      </div>

      <div class="right">
        <div class="panel">
          <div class="panel-head"><strong>组合结果</strong><span class="muted">{{ result.style?.name }}</span></div>
          <div class="prompt-block">
            <div class="label">正向提示词</div>
            <div class="text">{{ result.prompt || '填写左侧信息后点击「生成提示词」' }}</div>
          </div>
          <div class="prompt-block negative">
            <div class="label">负向提示词</div>
            <div class="text">{{ result.negative_prompt || '-' }}</div>
          </div>
          <div class="parts" v-if="result.parts">
            <el-tag v-for="(value, key) in result.parts" :key="key" size="small" type="info">
              {{ partLabels[key as string] || key }}：{{ value || '-' }}
            </el-tag>
          </div>
        </div>

        <div class="panel">
          <div class="panel-head">
            <strong>画风模板</strong>
            <span class="muted">共 {{ templates.length }} 套，点击套用</span>
          </div>
          <div class="template-grid">
            <div v-for="item in templates" :key="item.id" class="template" @click="applyTemplate(item)">
              <div class="template-name">{{ item.name }}</div>
              <div class="muted small">{{ item.description || item.category }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="panel" style="margin-top: 14px">
      <div class="panel-head"><strong>最近生成记录</strong><span class="muted">每次生成都会留下提示词与参数，方便复现</span></div>
      <el-table :data="history" size="small" empty-text="还没有生成记录">
        <el-table-column prop="prompt" label="提示词" show-overflow-tooltip />
        <el-table-column prop="kind_label" label="类型" width="100" />
        <el-table-column label="时间" width="160">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'

import { metaApi, promptApi } from '@/api'
import { formatDate } from '@/utils/format'

const meta = reactive<any>({ shot_sizes: [], camera_angles: [], camera_moves: [], styles: [] })
const lightingOptions = ['夜晚霓虹', '黄昏逆光', '清晨薄雾', '月光冷调', '室内暖光', '爆炸高光']

const form = reactive({
  subject: '银发少女站在灯塔顶端',
  action: '回头看向镜头，披风被海风吹起',
  shot_size: '近景',
  camera_angle: '仰视',
  camera_move: '推',
  style: '日系赛璐璐',
  lighting: '夜晚霓虹',
  quality: 'masterpiece, best quality, ultra detailed',
  consistency: true
})

const building = ref(false)
const result = ref<any>({})
const templates = ref<any[]>([])
const history = ref<any[]>([])

const partLabels: Record<string, string> = {
  subject: '主体',
  action: '动作',
  shot: '镜头',
  style: '画风',
  lighting: '光影',
  quality: '画质',
  consistency: '一致性'
}

async function build() {
  building.value = true
  try {
    result.value = await promptApi.build({ ...form, negative: 'text, watermark' })
  } finally {
    building.value = false
  }
}

function applyTemplate(item: any) {
  form.style = item.name
  ElMessage.success(`已套用画风：${item.name}`)
  build()
}

async function copyAll() {
  if (!result.value.prompt) {
    ElMessage.warning('请先生成提示词')
    return
  }
  await navigator.clipboard.writeText(result.value.prompt)
  ElMessage.success('正向提示词已复制')
}

onMounted(async () => {
  const options = await metaApi.options()
  Object.assign(meta, options)
  const [templateData, historyData] = await Promise.all([promptApi.templates(), promptApi.history({ limit: 10 })])
  templates.value = templateData.items
  history.value = historyData.items
  await build()
})
</script>

<style scoped>
.studio {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.right {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 12px;
}

.prompt-block {
  border: 1px solid var(--aigc-line);
  border-radius: 10px;
  padding: 10px 12px;
  background: #10141c;
  margin-bottom: 10px;
}

.prompt-block .label {
  font-size: 11px;
  color: var(--aigc-muted);
  margin-bottom: 6px;
}

.prompt-block .text {
  font-family: 'Consolas', monospace;
  font-size: 12px;
  line-height: 1.8;
  color: #cfd9ea;
  word-break: break-word;
  max-height: 190px;
  overflow-y: auto;
}

.prompt-block.negative .text {
  color: #e08a9b;
}

.parts {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 8px;
  max-height: 260px;
  overflow-y: auto;
}

.template {
  border: 1px solid var(--aigc-line);
  border-radius: 8px;
  padding: 8px 10px;
  cursor: pointer;
  background: #10141c;
  transition: border-color 0.15s ease;
}

.template:hover {
  border-color: var(--aigc-accent);
}

.template-name {
  font-size: 12px;
  margin-bottom: 4px;
}

.small {
  font-size: 11px;
}
</style>
