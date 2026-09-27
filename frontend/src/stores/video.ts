import { defineStore } from 'pinia'

export type VideoRow = Record<string, string | number | null>

export type ExcludedPoint = { 点位编号: string; 缺失字段: string[] }

export type StationSummary = {
  站点: string
  点位总数: number
  纳入统计: number
  在线: number
  离线: number
  画面异常: number
  异常点位数: number
  离线时长分钟: number
  在线率: number | null
  未纳入点位: ExcludedPoint[]
  说明: string
}

export type VideoSummary = {
  stations: StationSummary[]
  totals: StationSummary
}

/** 巡查视图快照：从点位详情返回列表时直接恢复，保证在线率与离线点位数一致。 */
export const useVideoStore = defineStore('video', {
  state: () => ({
    station: '',
    status: '',
    keyword: '',
    rows: [] as VideoRow[],
    total: 0,
    summary: null as VideoSummary | null,
    loaded: false,
  }),
  actions: {
    cache(payload: { rows: VideoRow[]; total: number; summary: VideoSummary }) {
      this.rows = payload.rows
      this.total = payload.total
      this.summary = payload.summary
      this.loaded = true
    },
  },
})
