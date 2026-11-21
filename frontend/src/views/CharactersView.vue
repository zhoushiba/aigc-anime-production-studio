<template>
  <div class="page">
    <div class="page-title">
      <h2>角色与场景卡</h2>
      <span class="sub">性格 / 外形提示词 / 参考图 / LoRA / 固定种子，保证跨镜头一致性</span>
      <div style="flex: 1"></div>
      <el-button size="small" type="primary" :icon="Plus" @click="characterDialog = true">新增角色</el-button>
      <el-button size="small" :icon="Plus" @click="sceneDialog = true">新增场景卡</el-button>
    </div>

    <el-skeleton v-if="loading" :rows="6" animated />

    <template v-else>
      <h3 class="section-title">角色设定卡</h3>
      <div class="card-grid">
        <div v-for="item in characters" :key="item.id" class="role-card">
          <div class="role-head">
            <div>
              <strong>{{ item.name }}</strong>
              <el-tag size="small" :type="item.role_type === '主角' ? 'success' : 'info'">{{ item.role_type }}</el-tag>
            </div>
            <el-button link size="small" @click="editCharacter(item)">编辑</el-button>
          </div>
          <p class="muted">{{ item.personality || '尚未填写性格' }}</p>
          <div class="prompt-box">{{ item.appearance_prompt || '尚未填写外形提示词' }}</div>
          <div class="role-meta">
            <span v-if="item.lora_name">LoRA：{{ item.lora_name }} × {{ item.lora_weight }}</span>
            <span v-if="item.seed">seed：{{ item.seed }}</span>
            <span v-if="item.voice">声线：{{ item.voice }}</span>
          </div>
        </div>
        <el-empty v-if="!characters.length" description="还没有角色" />
      </div>

      <h3 class="section-title">场景卡</h3>
      <div class="card-grid">
        <div v-for="item in sceneCards" :key="item.id" class="role-card">
          <div class="role-head">
            <strong>{{ item.name }}</strong>
            <el-button link size="small" @click="editScene(item)">编辑</el-button>
          </div>
          <p class="muted">{{ item.description || '尚未填写描述' }}</p>
          <div class="prompt-box">{{ item.prompt || '尚未填写场景提示词' }}</div>
          <div class="role-meta">
            <span v-if="item.atmosphere">氛围：{{ item.atmosphere }}</span>
            <span v-if="item.seed">seed：{{ item.seed }}</span>
          </div>
        </div>
        <el-empty v-if="!sceneCards.length" description="还没有场景卡" />
      </div>
    </template>

    <el-dialog v-model="characterDialog" :title="characterForm.id ? '编辑角色' : '新增角色'" width="600px">
      <el-form :model="characterForm" label-width="104px">
        <el-form-item label="角色名" required><el-input v-model="characterForm.name" /></el-form-item>
        <el-form-item label="角色类型">
          <el-select v-model="characterForm.role_type" style="width: 100%">
            <el-option label="主角" value="主角" />
            <el-option label="配角" value="配角" />
            <el-option label="反派" value="反派" />
            <el-option label="群众" value="群众" />
          </el-select>
        </el-form-item>
        <el-form-item label="性格"><el-input v-model="characterForm.personality" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="外形提示词">
          <el-input v-model="characterForm.appearance_prompt" type="textarea" :rows="3" placeholder="silver hair, amber eyes, white hoodie..." />
        </el-form-item>
        <el-form-item label="一致性前缀">
          <el-input v-model="characterForm.prompt_prefix" placeholder="1girl, silver hair, amber eyes" />
        </el-form-item>
        <el-form-item label="LoRA 名称"><el-input v-model="characterForm.lora_name" placeholder="lin_che_v1" /></el-form-item>
        <el-form-item label="LoRA 权重">
          <el-slider v-model="characterForm.lora_weight" :min="0" :max="1.5" :step="0.05" show-input />
        </el-form-item>
        <el-form-item label="固定种子">
          <el-input-number v-model="characterForm.seed" :min="0" :max="4294967295" />
        </el-form-item>
        <el-form-item label="声线"><el-input v-model="characterForm.voice" placeholder="少年音 / 低沉女声" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="characterDialog = false">取消</el-button>
        <el-button type="primary" @click="saveCharacter">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="sceneDialog" :title="sceneForm.id ? '编辑场景卡' : '新增场景卡'" width="560px">
      <el-form :model="sceneForm" label-width="96px">
        <el-form-item label="场景名" required><el-input v-model="sceneForm.name" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="sceneForm.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="氛围"><el-input v-model="sceneForm.atmosphere" placeholder="压抑 / 温暖 / 空旷" /></el-form-item>
        <el-form-item label="场景提示词">
          <el-input v-model="sceneForm.prompt" type="textarea" :rows="3" placeholder="abandoned observatory on a cliff, starry sky..." />
        </el-form-item>
        <el-form-item label="固定种子"><el-input-number v-model="sceneForm.seed" :min="0" :max="4294967295" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="sceneDialog = false">取消</el-button>
        <el-button type="primary" @click="saveScene">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'

import { seriesApi } from '@/api'

const route = useRoute()
const seriesId = Number(route.params.id)

const loading = ref(true)
const characters = ref<any[]>([])
const sceneCards = ref<any[]>([])

const characterDialog = ref(false)
const characterForm = reactive<any>({
  id: null,
  name: '',
  role_type: '配角',
  personality: '',
  appearance_prompt: '',
  prompt_prefix: '',
  lora_name: '',
  lora_weight: 0.75,
  seed: 20240501,
  voice: ''
})

const sceneDialog = ref(false)
const sceneForm = reactive<any>({ id: null, name: '', description: '', atmosphere: '', prompt: '', seed: 1101 })

async function load() {
  loading.value = true
  try {
    const [chars, cards] = await Promise.all([seriesApi.characters(seriesId), seriesApi.sceneCards(seriesId)])
    characters.value = chars.items
    sceneCards.value = cards.items
  } finally {
    loading.value = false
  }
}

function editCharacter(item: any) {
  Object.assign(characterForm, item)
  characterDialog.value = true
}

async function saveCharacter() {
  if (!characterForm.name.trim()) {
    ElMessage.warning('请填写角色名')
    return
  }
  const payload = { ...characterForm }
  delete payload.id
  if (characterForm.id) {
    await seriesApi.createCharacter(seriesId, payload)
  } else {
    await seriesApi.createCharacter(seriesId, payload)
  }
  ElMessage.success('角色设定已保存')
  characterDialog.value = false
  await load()
}

function editScene(item: any) {
  Object.assign(sceneForm, item)
  sceneDialog.value = true
}

async function saveScene() {
  if (!sceneForm.name.trim()) {
    ElMessage.warning('请填写场景名')
    return
  }
  const payload = { ...sceneForm }
  delete payload.id
  await seriesApi.createSceneCard(seriesId, payload)
  ElMessage.success('场景卡已保存')
  sceneDialog.value = false
  await load()
}

onMounted(async () => {
  Object.assign(characterForm, { id: null })
  await load()
})
</script>

<style scoped>
.section-title {
  margin: 16px 0 10px;
  font-size: 15px;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}

.role-card {
  background: linear-gradient(180deg, rgba(27, 34, 48, 0.94), rgba(21, 26, 36, 0.94));
  border: 1px solid var(--aigc-line);
  border-radius: 12px;
  padding: 14px;
}

.role-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.role-head div {
  display: flex;
  gap: 8px;
  align-items: center;
}

.prompt-box {
  margin-top: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #10141c;
  border: 1px dashed var(--aigc-line);
  font-family: 'Consolas', monospace;
  font-size: 11px;
  color: #9fb0c9;
  line-height: 1.7;
  word-break: break-word;
}

.role-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 10px;
  font-size: 11px;
  color: var(--aigc-muted);
}
</style>
