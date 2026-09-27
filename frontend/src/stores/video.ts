import { defineStore } from 'pinia'

/** 视频巡查视图状态：站点范围、筛选条件与按范围缓存的站点汇总。
 *
 * 汇总按站点范围缓存：从列表进详情再返回时直接复用缓存，
 * 在线率与离线点位数不会因为重新请求而出现口径漂移。
 */
export type SummaryItem = {
  站点: string
  点位总数: number
  在线数: number
  离线数: number
  画面异常数: number
  纳入统计数: number
  未纳入统计数: number
  在线率: number | null
  离线时长分钟: number
  异常点位数: number
  excluded: { 点位编号: string; 缺失字段: string }[]
}

export type SummaryPayload = {
  items: SummaryItem[]
  excluded: { 点位编号: string; 缺失字段: string; 站点: string }[]
  note: string
  message: string
}

export const useVideoStore = defineStore('video', {
  state: () => ({
    scope: '',
    filters: { keyword: '', status: '' },
    summaryCache: {} as Record<string, SummaryPayload>,
  }),
  actions: {
    setScope(scope: string) {
      this.scope = scope
    },
    setFilters(filters: { keyword: string; status: string }) {
      this.filters = { ...filters }
    },
    cacheSummary(scope: string, payload: SummaryPayload) {
      this.summaryCache[scope] = payload
    },
    cachedSummary(scope: string): SummaryPayload | null {
      return this.summaryCache[scope] ?? null
    },
  },
})
