<template>
  <section class="page" data-module="video-detail">
    <header class="page-head">
      <div>
        <h2>视频点位详情</h2>
        <p class="page-desc">点位在线情况与最近 {{ LIMIT }} 次录像巡检记录，导出条数与视图条数保持一致。</p>
      </div>
      <div class="page-actions">
        <button class="btn" type="button" @click="goBack">返回巡查视图</button>
      </div>
    </header>

    <div v-if="pointError" class="retry-bar">
      <span class="error-text">{{ pointError }}</span>
      <button class="btn" type="button" @click="loadPoint">重试</button>
    </div>
    <section v-else-if="point" class="panel">
      <h3>点位信息</h3>
      <div class="detail-grid">
        <div v-for="cell in pointCells" :key="cell.label" class="cell">
          <span>{{ cell.label }}</span>
          <strong :class="{ 'warn-text': cell.warn }">{{ cell.value }}</strong>
        </div>
      </div>
    </section>

    <section class="panel">
      <h3>最近录像巡检记录</h3>
      <div class="page-actions panel-actions">
        <button class="btn" type="button" :disabled="!point" @click="exportInspections">
          导出巡检记录
        </button>
        <span v-if="exportMessage" class="export-note">{{ exportMessage }}</span>
      </div>
      <div v-if="inspectionsError" class="retry-bar">
        <span class="error-text">{{ inspectionsError }}</span>
        <button class="btn" type="button" @click="loadInspections">重试</button>
      </div>
      <table v-else class="data-table">
        <thead>
          <tr>
            <th v-for="column in inspectionColumns" :key="column">{{ column }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in inspections" :key="String(row.id)">
            <td v-for="column in inspectionColumns" :key="column">{{ row[column] ?? '—' }}</td>
          </tr>
          <tr v-if="!inspections.length">
            <td :colspan="inspectionColumns.length" class="empty-state">
              该点位暂无录像巡检记录
            </td>
          </tr>
        </tbody>
      </table>
    </section>

    <footer class="page-foot">
      <span>视图显示 {{ inspections.length }} 条巡检记录</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { fetchJsonWithRetry } from '@/api/client'

type Row = Record<string, string | number | null>

type InspectionPage = {
  items: Row[]
  total: number
}

type InspectionExport = {
  module: string
  point_id: number
  点位编号: string
  total: number
  items: Row[]
}

const LIMIT = 5
const inspectionColumns = ['巡检编号', '巡检时间', '巡检结果', '录像完整率（%）', '巡检人', '备注']

const route = useRoute()
const router = useRouter()
const pointId = Number(route.params.id)

const point = ref<Row | null>(null)
const pointError = ref('')
const inspections = ref<Row[]>([])
const inspectionsError = ref('')
const exportMessage = ref('')

const pointCells = computed(() => {
  if (!point.value) return []
  const missing = point.value['在线状态'] === '离线' && !String(point.value['离线原因'] ?? '').trim()
  return [
    { label: '点位编号', value: point.value['点位编号'] ?? '—' },
    { label: '所属站点', value: point.value['所属站点'] ?? '—' },
    { label: '监控画面地址', value: point.value['监控画面地址'] ?? '—' },
    { label: '在线状态', value: point.value['在线状态'] ?? '—' },
    { label: '最近离线时刻', value: point.value['最近离线时刻'] ?? '—' },
    {
      label: '离线原因',
      value: missing ? '未登记（不纳入在线率统计）' : point.value['离线原因'] ?? '—',
      warn: missing,
    },
    { label: '累计离线时长（分钟）', value: point.value['累计离线时长（分钟）'] ?? '—' },
  ]
})

async function loadPoint() {
  pointError.value = ''
  try {
    point.value = await fetchJsonWithRetry<Row>(`/api/video/points/${pointId}`)
  } catch (error) {
    pointError.value = error instanceof Error ? error.message : '视频点位读取失败'
  }
}

async function loadInspections() {
  inspectionsError.value = ''
  try {
    const payload = await fetchJsonWithRetry<InspectionPage>(
      `/api/video/points/${pointId}/inspections?limit=${LIMIT}`,
    )
    inspections.value = payload.items ?? []
  } catch (error) {
    inspectionsError.value = error instanceof Error ? error.message : '录像巡检记录读取失败'
  }
}

async function exportInspections() {
  exportMessage.value = ''
  try {
    const payload = await fetchJsonWithRetry<InspectionExport>(
      `/api/video/points/${pointId}/inspections/export?limit=${LIMIT}`,
    )
    const match = payload.total === inspections.value.length
      && payload.items.length === inspections.value.length
    downloadJson(payload, `${payload.点位编号 || pointId}-录像巡检记录.json`)
    exportMessage.value = match
      ? `已导出 ${payload.total} 条，与视图显示条数一致`
      : `导出 ${payload.total} 条，与视图 ${inspections.value.length} 条不一致，请刷新后重试`
  } catch (error) {
    exportMessage.value = error instanceof Error ? error.message : '巡检记录导出失败'
  }
}

function downloadJson(data: unknown, filename: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

function goBack() {
  void router.push('/video')
}

onMounted(() => {
  void loadPoint()
  void loadInspections()
})
</script>
