<template>
  <div class="page">
    <div class="page-title">
      <h2>审核流</h2>
      <span class="sub">提交 → 通过 / 驳回（带意见）→ 状态流转，分集与素材都可送审</span>
      <div style="flex: 1"></div>
      <el-button size="small" :icon="Plus" @click="createDialog = true">提交审核</el-button>
      <el-button size="small" @click="load">刷新</el-button>
    </div>

    <div class="stat-grid">
      <div class="stat-card">
        <div class="label">待审核</div>
        <div class="value">{{ stats.pending || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="label">已通过</div>
        <div class="value">{{ stats.approved || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="label">已驳回</div>
        <div class="value">{{ stats.rejected || 0 }}</div>
      </div>
      <div class="stat-card">
        <div class="label">审核总数</div>
        <div class="value">{{ stats.total || 0 }}</div>
      </div>
    </div>

    <div class="toolbar" style="margin-top: 14px">
      <el-radio-group v-model="query.status" @change="load">
        <el-radio-button label="">全部</el-radio-button>
        <el-radio-button label="pending">待审核</el-radio-button>
        <el-radio-button label="approved">已通过</el-radio-button>
        <el-radio-button label="rejected">已驳回</el-radio-button>
      </el-radio-group>
      <span class="muted">共 {{ total }} 条</span>
    </div>

    <el-table v-loading="loading" :data="items" size="small" empty-text="暂无审核记录">
      <el-table-column prop="id" label="#" width="60" />
      <el-table-column prop="title" label="送审标题" min-width="200" />
      <el-table-column label="对象" width="110">
        <template #default="{ row }">{{ targetLabels[row.target_type] || row.target_type }} #{{ row.target_id }}</template>
      </el-table-column>
      <el-table-column prop="submitted_by" label="提交人" width="110" />
      <el-table-column prop="comment" label="说明" min-width="180" show-overflow-tooltip />
      <el-table-column label="状态" width="96">
        <template #default="{ row }">
          <el-tag size="small" :type="tagType(row.status)">{{ statusLabels[row.status] }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="reviewer_name" label="审核人" width="110" />
      <el-table-column label="提交时间" width="150">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="170" fixed="right">
        <template #default="{ row }">
          <template v-if="row.status === 'pending'">
            <el-button link type="success" @click="decide(row, true)">通过</el-button>
            <el-button link type="danger" @click="decide(row, false)">驳回</el-button>
          </template>
          <span v-else class="muted small">{{ row.decided_at ? formatDate(row.decided_at) : '已处理' }}</span>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="createDialog" title="提交审核" width="560px">
      <el-form :model="form" label-width="92px">
        <el-form-item label="送审对象">
          <el-radio-group v-model="form.target_type">
            <el-radio-button label="episode">分集</el-radio-button>
            <el-radio-button label="asset">素材</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="对象 ID">
          <el-input-number v-model="form.target_id" :min="1" />
          <span class="muted">&nbsp;当前项目分集/素材编号</span>
        </el-form-item>
        <el-form-item label="标题"><el-input v-model="form.title" /></el-form-item>
        <el-form-item label="送审说明"><el-input v-model="form.comment" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="所属项目">
          <el-input-number v-model="form.series_id" :min="1" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="create">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'

import { reviewApi } from '@/api'
import { formatDate, tagType } from '@/utils/format'

const loading = ref(false)
const saving = ref(false)
const items = ref<any[]>([])
const total = ref(0)
const stats = ref<any>({})
const query = reactive({ status: 'pending' })
const createDialog = ref(false)

const targetLabels: Record<string, string> = { episode: '分集', timeline: '合成单', asset: '素材' }
const statusLabels: Record<string, string> = { pending: '待审核', approved: '已通过', rejected: '已驳回' }

const form = reactive({
  target_type: 'episode',
  target_id: 1,
  title: '第 1 集 分镜与素材提交审核',
  comment: '请审核分镜节奏与角色一致性',
  series_id: 1
})

async function load() {
  loading.value = true
  try {
    const [list, statsData] = await Promise.all([
      reviewApi.list({ status: query.status || undefined, size: 50 }),
      reviewApi.stats()
    ])
    items.value = list.items
    total.value = list.total
    stats.value = statsData
  } finally {
    loading.value = false
  }
}

async function decide(row: any, approve: boolean) {
  const { value } = await ElMessageBox.prompt(
    approve ? '填写通过意见（可留空）' : '请填写驳回意见，说明需要修改的地方',
    approve ? '通过审核' : '驳回审核',
    {
      inputType: 'textarea',
      inputPlaceholder: approve ? '如：节奏可以，进入生成' : '如：第 3 镜角色发型与设定卡不一致',
      inputValue: approve ? '通过，可进入下一阶段' : ''
    }
  )
  await reviewApi.decide(row.id, { approve, comment: value || '' })
  ElMessage.success(approve ? '已通过' : '已驳回')
  await load()
}

async function create() {
  if (!form.title.trim()) {
    ElMessage.warning('请填写送审标题')
    return
  }
  saving.value = true
  try {
    await reviewApi.create({ ...form })
    ElMessage.success('已提交审核')
    createDialog.value = false
    await load()
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.small {
  font-size: 11px;
}
</style>
