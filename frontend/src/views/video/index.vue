<template>
  <section class="page" data-module="video">
    <header class="page-head">
      <div>
        <h2>视频点位在线巡查</h2>
        <p class="page-desc">按站点登记监控画面地址、在线状态与最近离线时刻，汇总在线率、离线时长与异常点位数，不用盯屏幕也能看出哪个摄像头掉了。</p>
      </div>
      <div class="page-actions">
        <button class="btn" type="button" @click="reload">刷新</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="applyFilters">
      <label class="filter-item">
        <span>站点范围</span>
        <select v-model="draft.station">
          <option value="">全部站点</option>
          <option v-for="name in stations" :key="name" :value="name">{{ name }}</option>
        </select>
      </label>
      <label class="filter-item">
        <span>在线状态</span>
        <select v-model="draft.status">
          <option value="">全部状态</option>
          <option v-for="name in statusOptions" :key="name" :value="name">{{ name }}</option>
        </select>
      </label>
      <label class="filter-item">
        <span>点位编号/名称</span>
        <input v-model="draft.keyword" placeholder="按点位编号或名称检索" />
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <h3 class="section-title">按站点统计</h3>
    <table class="data-table">
      <thead>
        <tr>
          <th>站点</th>
          <th>点位总数</th>
          <th>纳入统计</th>
          <th>在线</th>
          <th>离线</th>
          <th>画面异常</th>
          <th>异常点位数</th>
          <th>离线时长</th>
          <th>在线率</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in summaryRows" :key="row.站点">
          <td>{{ row.站点 }}</td>
          <td>{{ row.点位总数 }}</td>
          <td>{{ row.纳入统计 }}</td>
          <td>{{ row.在线 }}</td>
          <td>{{ row.离线 }}</td>
          <td>{{ row.画面异常 }}</td>
          <td>{{ row.异常点位数 }}</td>
          <td>{{ formatMinutes(row.离线时长分钟) }}</td>
          <td>{{ row.在线率 === null ? '—' : `${row.在线率}%` }}</td>
        </tr>
        <tr v-if="!summaryRows.length">
          <td colspan="9" class="empty-state">统计数据读取失败或暂无站点范围</td>
        </tr>
      </tbody>
    </table>
    <p v-for="note in summaryNotes" :key="note" class="note-text">{{ note }}</p>

    <h3 class="section-title">点位台账</h3>
    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td>{{ row.点位编号 }}</td>
          <td>{{ row.点位名称 }}</td>
          <td>{{ row.所属站点 }}</td>
          <td>{{ row.监控画面地址 }}</td>
          <td><span class="status-tag" :class="statusClass(String(row.在线状态 ?? ''))">{{ row.在线状态 }}</span></td>
          <td>{{ row.最近离线时刻 || '—' }}</td>
          <td>{{ row.离线原因 || '—' }}</td>
          <td class="row-actions">
            <button class="link" type="button" @click="openDetail(row)">巡检记录</button>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">
            当前站点范围「{{ scopeLabel }}」内暂无符合条件的视频点位，可切换站点范围或重置条件
          </td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条视频点位记录</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { fetchJson } from '@/api/client'
import { useVideoStore } from '@/stores/video'
import type { VideoRow, VideoSummary } from '@/stores/video'

const ENDPOINT = '/api/video'
const columns = ['点位编号', '点位名称', '所属站点', '监控画面地址', '在线状态', '最近离线时刻', '离线原因']
const statusOptions = ['在线', '离线', '画面异常']

const store = useVideoStore()
const router = useRouter()

const stations = ref<string[]>([])
const draft = reactive({ station: '', status: '', keyword: '' })
const rows = ref<VideoRow[]>([])
const total = ref(0)
const summary = ref<VideoSummary | null>(null)
const errorMessage = ref('')

const summaryRows = computed(() => summary.value?.stations ?? [])

const summaryNotes = computed(() => {
  const notes: string[] = []
  for (const row of summaryRows.value) {
    if (row.说明) {
      notes.push(`${row.站点}：${row.说明}`)
    }
    for (const item of row.未纳入点位) {
      notes.push(`${row.站点}：点位 ${item.点位编号} 缺少「${item.缺失字段.join('、')}」，未纳入在线率统计`)
    }
  }
  return notes
})

const stats = computed(() => {
  const totals = summary.value?.totals
  return [
    { label: '点位总数', value: totals?.点位总数 ?? 0 },
    { label: '整体在线率', value: totals && totals.在线率 !== null ? `${totals.在线率}%` : '—' },
    { label: '离线点位数', value: totals?.离线 ?? 0 },
    { label: '异常点位数', value: totals?.异常点位数 ?? 0 },
  ]
})

const scopeLabel = computed(() => store.station || '全部站点')

function statusClass(status: string) {
  if (status === '在线') return 'online'
  if (status === '离线') return 'offline'
  return 'abnormal'
}

function formatMinutes(minutes: number) {
  if (!minutes) return '0 分钟'
  if (minutes < 60) return `${minutes} 分钟`
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  return rest ? `${hours} 小时 ${rest} 分钟` : `${hours} 小时`
}

function openDetail(row: VideoRow) {
  void router.push(`/video/${String(row.id)}`)
}

function applyFilters() {
  store.station = draft.station
  store.status = draft.status
  store.keyword = draft.keyword
  void reload()
}

function resetFilters() {
  draft.station = ''
  draft.status = ''
  draft.keyword = ''
  applyFilters()
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams()
  if (store.station) query.set('station', store.station)
  if (store.status) query.set('status', store.status)
  if (store.keyword) query.set('keyword', store.keyword)
  query.set('size', '200')
  const summaryQuery = store.station ? `?station=${encodeURIComponent(store.station)}` : ''
  try {
    const [listPayload, summaryPayload] = await Promise.all([
      fetchJson<{ items: VideoRow[]; total: number }>(`${ENDPOINT}?${query.toString()}`),
      fetchJson<VideoSummary>(`${ENDPOINT}/summary${summaryQuery}`),
    ])
    rows.value = listPayload.items ?? []
    total.value = listPayload.total ?? rows.value.length
    summary.value = summaryPayload
    store.cache({ rows: rows.value, total: total.value, summary: summaryPayload })
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '视频点位列表读取失败'
  }
}

onMounted(async () => {
  draft.station = store.station
  draft.status = store.status
  draft.keyword = store.keyword
  try {
    const payload = await fetchJson<{ stations: string[] }>(`${ENDPOINT}/stations`)
    stations.value = payload.stations ?? []
  } catch {
    stations.value = []
  }
  // 从点位详情返回时直接恢复快照，在线率与离线点位数保持进入前的一致
  if (store.loaded && store.summary) {
    rows.value = store.rows
    total.value = store.total
    summary.value = store.summary
    return
  }
  await reload()
})
</script>
