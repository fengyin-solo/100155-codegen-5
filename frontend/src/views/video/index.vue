<template>
  <section class="page" data-module="video">
    <header class="page-head">
      <div>
        <h2>视频点位在线巡查</h2>
        <p class="page-desc">按站点巡查视频点位在线情况：在线率、离线时长、异常点位数一屏看清，点开点位可查最近录像巡检记录。</p>
      </div>
      <div class="page-actions">
        <button class="btn" type="button" @click="refreshAll">刷新巡查数据</button>
      </div>
    </header>

    <form class="filter-bar" @submit.prevent="reloadPoints">
      <label class="filter-item">
        <span>站点范围</span>
        <select v-model="stationScope" @change="onScopeChange">
          <option value="">全部站点</option>
          <option v-for="name in stationOptions" :key="name" :value="name">{{ name }}</option>
        </select>
      </label>
      <label class="filter-item">
        <span>监控画面地址</span>
        <input v-model="filters.keyword" placeholder="按监控画面地址检索" />
      </label>
      <label class="filter-item">
        <span>在线状态</span>
        <select v-model="filters.status">
          <option value="">全部状态</option>
          <option v-for="item in statuses" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <div v-if="summaryItems.length" class="stat-row">
      <article v-for="card in headlineCards" :key="card.label" class="stat-card">
        <span class="stat-label">{{ card.label }}</span>
        <strong class="stat-value">{{ card.value }}</strong>
      </article>
    </div>

    <section class="panel">
      <h3>按站点统计</h3>
      <div v-if="summaryError" class="retry-bar">
        <span class="error-text">{{ summaryError }}</span>
        <button class="btn" type="button" @click="loadSummary(true)">重试</button>
      </div>
      <p v-else-if="summaryMessage" class="empty-hint">{{ summaryMessage }}</p>
      <template v-else-if="summaryItems.length">
        <table class="data-table">
          <thead>
            <tr>
              <th>站点</th>
              <th>点位总数</th>
              <th>在线</th>
              <th>离线</th>
              <th>画面异常</th>
              <th>在线率</th>
              <th>离线时长（分钟）</th>
              <th>异常点位数</th>
              <th>统计说明</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in summaryItems" :key="item.站点">
              <td>{{ item.站点 }}</td>
              <td>{{ item.点位总数 }}</td>
              <td>{{ item.在线数 }}</td>
              <td>{{ item.离线数 }}</td>
              <td>{{ item.画面异常数 }}</td>
              <td>{{ item.在线率 === null ? '—' : `${item.在线率}%` }}</td>
              <td>{{ item.离线时长分钟 }}</td>
              <td>{{ item.异常点位数 }}</td>
              <td>
                <span v-if="item.excluded.length" class="warn-text">
                  {{ excludedText(item) }}
                </span>
                <span v-else>全部纳入统计</span>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-if="excludedNote" class="warn-text">{{ excludedNote }}</p>
      </template>
    </section>

    <section class="panel">
      <h3>视频点位列表</h3>
      <div v-if="pointsError" class="retry-bar">
        <span class="error-text">{{ pointsError }}</span>
        <button class="btn" type="button" @click="reloadPoints">重试</button>
      </div>
      <table v-else class="data-table">
        <thead>
          <tr>
            <th v-for="column in columns" :key="column">{{ column }}</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="String(row.id)">
            <td v-for="column in columns" :key="column">
              <span :class="{ 'warn-text': column === '离线原因' && missingReason(row) }">
                {{ cellText(row, column) }}
              </span>
            </td>
            <td class="row-actions">
              <button class="link" type="button" @click="openDetail(row)">查看巡检</button>
            </td>
          </tr>
          <tr v-if="!rows.length">
            <td :colspan="columns.length + 1" class="empty-state">{{ pointsEmptyText }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <footer class="page-foot">
      <span>共 {{ total }} 个视频点位</span>
      <span>在线率统计口径：离线点位缺「离线原因」时不纳入统计</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { fetchJsonWithRetry } from '@/api/client'
import { useVideoStore, type SummaryPayload } from '@/stores/video'

type Row = Record<string, string | number | null>

const ENDPOINT = '/api/video'
const columns = ['点位编号', '所属站点', '监控画面地址', '在线状态', '最近离线时刻', '离线原因', '累计离线时长（分钟）']
const statuses = ['在线', '离线', '画面异常']

const router = useRouter()
const store = useVideoStore()

const stationScope = ref(store.scope)
const filters = ref({ ...store.filters })
const stationOptions = ref<string[]>([])
const summaryItems = ref<SummaryPayload['items']>([])
const summaryMessage = ref('')
const excludedNote = ref('')
const summaryError = ref('')
const rows = ref<Row[]>([])
const total = ref(0)
const pointsError = ref('')

const headlineCards = computed(() => {
  const items = summaryItems.value
  const included = items.reduce((sum, item) => sum + item.纳入统计数, 0)
  const online = items.reduce((sum, item) => sum + item.在线数, 0)
  return [
    { label: '点位总数', value: items.reduce((sum, item) => sum + item.点位总数, 0) },
    { label: '整体在线率', value: included ? `${((100 * online) / included).toFixed(1)}%` : '—' },
    { label: '离线点位数', value: items.reduce((sum, item) => sum + item.离线数, 0) },
    { label: '异常点位数', value: items.reduce((sum, item) => sum + item.异常点位数, 0) },
  ]
})

const pointsEmptyText = computed(() => {
  if (stationScope.value && !filters.value.keyword && !filters.value.status) {
    return `「${stationScope.value}」暂未登记视频点位，可切换到其他站点范围查看`
  }
  if (filters.value.keyword || filters.value.status) {
    return '当前筛选条件下没有视频点位，可调整监控画面地址或在线状态后重试'
  }
  return '暂无视频点位数据'
})

function excludedText(item: SummaryPayload['items'][number]) {
  const detail = item.excluded.map((entry) => `${entry.点位编号}（缺${entry.缺失字段}）`).join('、')
  return `${item.未纳入统计数} 个未纳入：${detail}`
}

function missingReason(row: Row) {
  return row['在线状态'] === '离线' && !String(row['离线原因'] ?? '').trim()
}

function cellText(row: Row, column: string) {
  const value = row[column]
  if (value === null || value === undefined || value === '') {
    return column === '离线原因' && missingReason(row) ? '未登记（不纳入在线率统计）' : '—'
  }
  return value
}

function applySummary(payload: SummaryPayload) {
  summaryItems.value = payload.items ?? []
  summaryMessage.value = payload.message ?? ''
  excludedNote.value = payload.note ?? ''
}

async function loadSummary(force = false) {
  summaryError.value = ''
  const scope = stationScope.value
  if (!force) {
    const cached = store.cachedSummary(scope)
    if (cached) {
      applySummary(cached)
      return
    }
  }
  try {
    const query = scope ? `?station=${encodeURIComponent(scope)}` : ''
    const payload = await fetchJsonWithRetry<SummaryPayload>(`${ENDPOINT}/summary${query}`)
    store.cacheSummary(scope, payload)
    applySummary(payload)
  } catch (error) {
    summaryError.value = error instanceof Error ? error.message : '站点汇总读取失败'
  }
}

async function loadStations() {
  try {
    const payload = await fetchJsonWithRetry<{ items: string[] }>(`${ENDPOINT}/stations`)
    stationOptions.value = payload.items ?? []
  } catch {
    stationOptions.value = []
  }
}

async function reloadPoints() {
  pointsError.value = ''
  store.setFilters({ ...filters.value })
  const query = new URLSearchParams()
  if (stationScope.value) query.set('station', stationScope.value)
  if (filters.value.keyword) query.set('keyword', filters.value.keyword)
  if (filters.value.status) query.set('status', filters.value.status)
  try {
    const payload = await fetchJsonWithRetry<{ items: Row[]; total: number }>(
      `${ENDPOINT}/points?${query.toString()}`,
    )
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  } catch (error) {
    pointsError.value = error instanceof Error ? error.message : '视频点位列表读取失败'
  }
}

function onScopeChange() {
  store.setScope(stationScope.value)
  void loadSummary()
  void reloadPoints()
}

function resetFilters() {
  filters.value = { keyword: '', status: '' }
  void reloadPoints()
}

function refreshAll() {
  void loadSummary(true)
  void reloadPoints()
}

function openDetail(row: Row) {
  void router.push(`/video/${row.id}`)
}

onMounted(() => {
  void loadStations()
  void loadSummary()
  void reloadPoints()
})
</script>
