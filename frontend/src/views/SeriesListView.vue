<template>
  <div class="page">
    <div class="page-title">
      <h2>项目管理</h2>
      <span class="sub">番剧 / 短片的题材、集数、时长、风格与制作状态</span>
      <div style="flex: 1"></div>
      <el-button type="primary" :icon="Plus" @click="dialogVisible = true">新建项目</el-button>
    </div>

    <div class="toolbar">
      <el-input v-model="query.search" placeholder="搜索标题 / 类型 / 一句话梗概" clearable style="width: 260px" @change="load" />
      <el-select v-model="query.status" placeholder="全部状态" clearable style="width: 150px" @change="load">
        <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
      <span class="muted">共 {{ total }} 个项目</span>
    </div>

    <el-table v-loading="loading" :data="items" empty-text="暂无项目，点击右上角新建" @row-click="openDetail">
      <el-table-column label="封面" width="92">
        <template #default="{ row }">
          <el-image v-if="row.cover_url" :src="mediaUrl(row.cover_url)" fit="cover" class="cover" />
          <div v-else class="cover cover-empty">无封面</div>
        </template>
      </el-table-column>
      <el-table-column prop="title" label="项目" min-width="180">
        <template #default="{ row }">
          <div class="title">{{ row.title }}</div>
          <div class="muted small">{{ row.logline }}</div>
        </template>
      </el-table-column>
      <el-table-column prop="genre" label="题材" width="92" />
      <el-table-column prop="style" label="画风" width="120" />
      <el-table-column label="形态" width="96">
        <template #default="{ row }">{{ row.platform_label }}</template>
      </el-table-column>
      <el-table-column label="集数" width="90">
        <template #default="{ row }">{{ row.episode_count }} / {{ row.episodes_planned }}</template>
      </el-table-column>
      <el-table-column label="分镜" width="80">
        <template #default="{ row }">{{ row.shot_count }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag size="small" :type="tagType(row.status)">{{ row.status_label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="更新时间" width="150">
        <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" title="新建项目" width="560px">
      <el-form :model="form" label-width="92px">
        <el-form-item label="项目标题" required>
          <el-input v-model="form.title" placeholder="如：星海拾光" />
        </el-form-item>
        <el-form-item label="题材">
          <el-select v-model="form.genre" style="width: 100%">
            <el-option v-for="genre in meta.genres" :key="genre" :label="genre" :value="genre" />
          </el-select>
        </el-form-item>
        <el-form-item label="一句话梗概">
          <el-input v-model="form.logline" type="textarea" :rows="2" placeholder="用一句话说清故事" />
        </el-form-item>
        <el-form-item label="画风">
          <el-select v-model="form.style" style="width: 100%">
            <el-option v-for="style in meta.styles" :key="style.key" :label="style.name" :value="style.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="规划集数">
          <el-input-number v-model="form.episodes_planned" :min="1" :max="60" />
        </el-form-item>
        <el-form-item label="单集时长">
          <el-input-number v-model="form.target_duration" :min="15" :max="600" :step="5" /> <span class="muted">&nbsp;秒</span>
        </el-form-item>
        <el-form-item label="画面形态">
          <el-radio-group v-model="form.platform">
            <el-radio-button label="vertical">竖屏短片</el-radio-button>
            <el-radio-button label="horizontal">横屏番剧</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="create">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { metaApi, seriesApi } from '@/api'
import { formatDate, mediaUrl, tagType } from '@/utils/format'

const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const items = ref<any[]>([])
const total = ref(0)
const query = reactive({ search: '', status: '' })
const meta = reactive<{ genres: string[]; styles: any[] }>({ genres: [], styles: [] })

const statusOptions = [
  { value: 'draft', label: '策划中' },
  { value: 'in_production', label: '制作中' },
  { value: 'review', label: '审核中' },
  { value: 'completed', label: '已完成' },
  { value: 'archived', label: '已归档' }
]

const form = reactive({
  title: '',
  genre: '科幻',
  logline: '',
  style: '日系赛璐璐',
  episodes_planned: 6,
  target_duration: 90,
  platform: 'vertical'
})

async function load() {
  loading.value = true
  try {
    const data = await seriesApi.list({ search: query.search || undefined, status: query.status || undefined, size: 50 })
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function create() {
  if (!form.title.trim()) {
    ElMessage.warning('请填写项目标题')
    return
  }
  saving.value = true
  try {
    const created = await seriesApi.create({ ...form })
    ElMessage.success('项目已创建')
    dialogVisible.value = false
    router.push(`/series/${created.id}`)
  } finally {
    saving.value = false
  }
}

function openDetail(row: any) {
  router.push(`/series/${row.id}`)
}

onMounted(async () => {
  const options = await metaApi.options()
  meta.genres = options.genres
  meta.styles = options.styles
  await load()
})
</script>

<style scoped>
.cover {
  width: 64px;
  height: 40px;
  border-radius: 6px;
  display: block;
}

.cover-empty {
  display: grid;
  place-items: center;
  font-size: 10px;
  color: var(--aigc-muted);
  background: #10141c;
  border: 1px dashed var(--aigc-line);
}

.title {
  font-weight: 600;
}

.small {
  font-size: 11px;
}

:deep(.el-table__row) {
  cursor: pointer;
}
</style>
