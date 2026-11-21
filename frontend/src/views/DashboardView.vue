<template>
  <div class="page">
    <div class="page-title">
      <h2>数据看板</h2>
      <span class="sub">生成成功率 / 平均耗时 / 素材数 / 项目进度</span>
      <div style="flex: 1"></div>
      <el-button size="small" :icon="Refresh" @click="load">刷新</el-button>
    </div>

    <el-skeleton v-if="loading" :rows="8" animated />

    <template v-else>
      <div class="stat-grid">
        <div class="stat-card">
          <div class="label">生成成功率</div>
          <div class="value">{{ data?.tasks?.success_rate ?? 0 }}%</div>
          <div class="muted">共 {{ data?.tasks?.total ?? 0 }} 个任务</div>
        </div>
        <div class="stat-card">
          <div class="label">平均生成耗时</div>
          <div class="value">{{ formatMs(data?.tasks?.avg_duration_ms) }}</div>
          <div class="muted">排队 {{ data?.tasks?.queued ?? 0 }} · 生成中 {{ data?.tasks?.running ?? 0 }}</div>
        </div>
        <div class="stat-card">
          <div class="label">素材总数</div>
          <div class="value">{{ data?.assets?.total ?? 0 }}</div>
          <div class="muted">入选 {{ data?.assets?.selected ?? 0 }} · 淘汰 {{ data?.assets?.rejected ?? 0 }}</div>
        </div>
        <div class="stat-card">
          <div class="label">项目 / 分集 / 分镜</div>
          <div class="value">{{ data?.series_total ?? 0 }} / {{ data?.episode_total ?? 0 }} / {{ data?.shot_total ?? 0 }}</div>
          <div class="muted">制作中 {{ data?.series_in_production ?? 0 }} 个项目</div>
        </div>
        <div class="stat-card">
          <div class="label">待审核</div>
          <div class="value">{{ data?.pending_reviews ?? 0 }}</div>
          <div class="muted">已通过 {{ data?.approved_reviews ?? 0 }}</div>
        </div>
      </div>

      <div class="two-col">
        <div class="panel">
          <div class="panel-head">
            <strong>近 7 日生成趋势</strong>
            <span class="muted">按天统计任务量与成功率</span>
          </div>
          <div class="bar-chart">
            <div v-for="item in trend" :key="item.date" class="bar">
              <div class="fill" :style="{ height: barHeight(item.total) }" :title="`${item.total} 个任务`"></div>
              <div class="cap">{{ item.date.slice(5) }}</div>
              <div class="cap">{{ item.total }}</div>
            </div>
          </div>
        </div>

        <div class="panel">
          <div class="panel-head">
            <strong>项目进度</strong>
            <span class="muted">按已交付分集 / 规划集数</span>
          </div>
          <el-empty v-if="!data?.series_progress?.length" description="还没有项目" :image-size="70" />
          <div v-for="item in data?.series_progress || []" :key="item.id" class="progress-row">
            <div class="progress-title">
              <router-link :to="`/series/${item.id}`">{{ item.title }}</router-link>
              <el-tag size="small" :type="tagType(item.status)">{{ item.status_label }}</el-tag>
            </div>
            <el-progress :percentage="Math.min(100, item.progress)" :stroke-width="8" />
            <div class="muted small">已交付 {{ item.episodes_done }} / 规划 {{ item.episodes_planned }} 集</div>
          </div>
        </div>
      </div>

      <div class="two-col">
        <div class="panel">
          <div class="panel-head">
            <strong>最近生成任务</strong>
            <router-link to="/tasks">查看全部</router-link>
          </div>
          <el-table :data="data?.recent_tasks || []" size="small" empty-text="暂无任务">
            <el-table-column prop="id" label="#" width="56" />
            <el-table-column prop="kind_label" label="类型" width="92" />
            <el-table-column prop="prompt" label="提示词" show-overflow-tooltip />
            <el-table-column label="状态" width="92">
              <template #default="{ row }">
                <el-tag size="small" :type="tagType(row.status)">{{ row.status_label }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="耗时" width="80">
              <template #default="{ row }">{{ formatMs(row.duration_ms) }}</template>
            </el-table-column>
          </el-table>
        </div>

        <div class="panel">
          <div class="panel-head">
            <strong>最新素材</strong>
            <router-link to="/assets">进入素材库</router-link>
          </div>
          <div class="thumb-grid">
            <div v-for="asset in data?.recent_assets || []" :key="asset.id" class="thumb">
              <el-image :src="mediaUrl(asset.thumb_url)" fit="cover" class="thumb-img" />
              <div class="thumb-meta">
                <span class="ellipsis">{{ asset.title }}</span>
                <el-tag size="small" :type="tagType(asset.status)">{{ asset.status_label }}</el-tag>
              </div>
            </div>
            <el-empty v-if="!data?.recent_assets?.length" description="还没有素材" :image-size="70" />
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { Refresh } from '@element-plus/icons-vue'
import { onMounted, ref } from 'vue'

import { dashboardApi } from '@/api'
import { formatMs, mediaUrl, tagType } from '@/utils/format'

const loading = ref(true)
const data = ref<any>(null)
const trend = ref<any[]>([])

function barHeight(total: number): string {
  const max = Math.max(1, ...trend.value.map((item) => item.total))
  return `${Math.max(6, Math.round((total / max) * 100))}%`
}

async function load() {
  loading.value = true
  try {
    const [overview, trendData] = await Promise.all([dashboardApi.overview(), dashboardApi.trend(7)])
    data.value = overview
    trend.value = trendData.items
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.two-col {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 14px;
  margin-top: 14px;
}

.panel-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 12px;
}

.panel-head .muted {
  font-size: 12px;
}

.progress-row {
  margin-bottom: 14px;
}

.progress-title {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 6px;
}

.small {
  font-size: 11px;
}

.thumb-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(132px, 1fr));
  gap: 10px;
}

.thumb {
  border: 1px solid var(--aigc-line);
  border-radius: 10px;
  overflow: hidden;
  background: #10141c;
}

.thumb-img {
  width: 100%;
  height: 108px;
  display: block;
}

.thumb-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 6px 8px;
  font-size: 11px;
}

.ellipsis {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
