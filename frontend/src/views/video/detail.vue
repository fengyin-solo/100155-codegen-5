<template>
  <section class="page" data-module="video-detail">
    <header class="page-head">
      <div>
        <h2>点位详情{{ point ? ` ${String(point.点位编号 ?? '')}` : '' }}</h2>
        <p class="page-desc">查看点位台账与最近几次录像巡检记录；导出条数与本页条数一致，接口失败会自动重试补齐。</p>
      </div>
      <div class="page-actions">
        <button class="btn" type="button" @click="goBack">返回巡查视图</button>
        <button class="btn primary" type="button" :disabled="exporting || !point" @click="exportWithRetry">
          {{ exporting ? '导出中…' : '导出录像巡检记录' }}
        </button>
      </div>
    </header>

    <p v-if="loadError" class="error-text">{{ loadError }}</p>

    <template v-if="point">
      <table class="data-table detail-table">
        <tbody>
          <tr v-for="field in detailFields" :key="field">
            <th>{{ field }}</th>
            <td>
              <span v-if="field === '在线状态'" class="status-tag" :class="statusClass(String(point.在线状态 ?? ''))">
                {{ point.在线状态 }}
              </span>
              <template v-else>{{ point[field] || '—' }}</template>
            </td>
          </tr>
          <tr v-if="missingFields.length">
            <th>统计说明</th>
            <td class="error-text">缺少「{{ missingFields.join('、') }}」，该点位未纳入在线率统计</td>
          </tr>
        </tbody>
      </table>

      <h3 class="section-title">最近录像巡检记录</h3>
      <table class="data-table">
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
            <td :colspan="inspectionColumns.length" class="empty-state">该点位暂无录像巡检记录</td>
          </tr>
        </tbody>
      </table>

      <footer class="page-foot">
        <span>共 {{ inspectionTotal }} 条录像巡检记录</span>
        <span v-if="exportMessage" :class="exportOk ? '' : 'error-text'">{{ exportMessage }}</span>
      </footer>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { fetchJson } from '@/api/client'

type Row = Record<string, string | number | null | string[]>

const ENDPOINT = '/api/video'
const detailFields = ['点位编号', '点位名称', '所属站点', '监控画面地址', '在线状态', '最近离线时刻', '离线原因', '离线时长分钟']
const inspectionColumns = ['记录编号', '巡检时刻', '巡检结果', '缺失时长分钟', '巡检人员', '处理状态']
const MAX_ATTEMPTS = 3

const route = useRoute()
const router = useRouter()
const pointId = String(route.params.id ?? '')

const point = ref<Row | null>(null)
const inspections = ref<Row[]>([])
const inspectionTotal = ref(0)
const loadError = ref('')
const exporting = ref(false)
const exportMessage = ref('')
const exportOk = ref(false)

const missingFields = computed(() => {
  const value = point.value?.统计缺失字段
  return Array.isArray(value) ? value.map(String) : []
})

function statusClass(status: string) {
  if (status === '在线') return 'online'
  if (status === '离线') return 'offline'
  return 'abnormal'
}

function goBack() {
  void router.push('/video')
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function csvCell(value: unknown) {
  const text = String(value ?? '')
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

function downloadCsv(items: Row[]) {
  const lines = items.map((item) => inspectionColumns.map((col) => csvCell(item[col])).join(','))
  const content = `﻿${[inspectionColumns.join(','), ...lines].join('\n')}`
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `录像巡检记录_${String(point.value?.点位编号 ?? pointId)}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

async function fetchExport() {
  const payload = await fetchJson<{ total: number; items: Row[] }>(
    `${ENDPOINT}/inspections/export?point_id=${encodeURIComponent(pointId)}`,
  )
  if ((payload.items?.length ?? -1) !== payload.total) {
    throw new Error(`导出数据不完整：标注 ${payload.total} 条，实到 ${payload.items?.length ?? 0} 条`)
  }
  return payload
}

async function exportWithRetry() {
  exporting.value = true
  exportMessage.value = ''
  exportOk.value = false
  let lastError = '导出失败'
  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt += 1) {
    try {
      const payload = await fetchExport()
      if (payload.total !== inspectionTotal.value) {
        throw new Error(`导出 ${payload.total} 条，与视图 ${inspectionTotal.value} 条不一致`)
      }
      downloadCsv(payload.items)
      exportOk.value = true
      exportMessage.value = `已导出 ${payload.total} 条，与视图条数一致`
      exporting.value = false
      return
    } catch (error) {
      lastError = error instanceof Error ? error.message : '导出失败'
      if (attempt < MAX_ATTEMPTS) {
        await sleep(400 * attempt)
      }
    }
  }
  exportMessage.value = `导出失败，已重试 ${MAX_ATTEMPTS} 次仍未补齐：${lastError}`
  exporting.value = false
}

onMounted(async () => {
  loadError.value = ''
  try {
    const payload = await fetchJson<{ point: Row; items: Row[]; total: number }>(
      `${ENDPOINT}/${encodeURIComponent(pointId)}/inspections`,
    )
    point.value = payload.point
    inspections.value = payload.items ?? []
    inspectionTotal.value = payload.total ?? inspections.value.length
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '点位信息读取失败，可能已撤点'
  }
})
</script>
