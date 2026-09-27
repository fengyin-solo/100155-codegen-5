"""视频点位在线巡查业务规则：统计口径、缺项判定与巡检记录筛选都收在这里。

口径约定：
- 在线状态为「离线」的点位，必须登记最近离线时刻与离线原因；缺任意一项就不纳入
  在线率统计，并在汇总里逐条说明缺了哪一项，避免分母不清。
- 离线时长只累计纳入统计的点位，保证在线率与离线时长是同一批点位算出来的。
- 巡检记录的列表与导出共用 list_inspections，保证视图条数与导出条数一致。
"""
from __future__ import annotations

from typing import Any

from app.store import store

MODULE = "video"
INSPECTION_MODULE = "video_inspection"

# 站点巡查范围：西岭观测站暂未登记任何视频点位，用于空范围提示。
SCOPE_STATIONS = ["城东观测站", "临港观测站", "北山观测站", "西岭观测站"]

STATUSES = ["在线", "离线", "画面异常"]
OFFLINE_STATUS = "离线"
ABNORMAL_STATUSES = ["离线", "画面异常"]
# 离线点位参与在线率统计前必须补齐的字段。
OFFLINE_REQUIRED_FIELDS = ["最近离线时刻", "离线原因"]


class VideoService:
    def stations(self) -> list[str]:
        """站点范围选项：以巡查范围为准，而不是只列已有数据的站点。"""
        return list(SCOPE_STATIONS)

    def list_points(
        self,
        *,
        station: str | None = None,
        status: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        if station:
            rows = [row for row in rows if row.get("所属站点") == station]
        if status:
            rows = [row for row in rows if row.get("在线状态") == status]
        if keyword:
            rows = [
                row
                for row in rows
                if keyword in str(row.get("点位编号", "")) or keyword in str(row.get("点位名称", ""))
            ]
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def get_point(self, point_id: int) -> dict[str, Any] | None:
        point = store.find(MODULE, point_id)
        if point is None:
            return None
        detail = dict(point)
        missing = self.missing_stat_fields(point)
        if missing:
            detail["统计缺失字段"] = missing
        return detail

    def missing_stat_fields(self, point: dict[str, Any]) -> list[str]:
        """离线点位缺了哪些统计必填项；在线与画面异常点位不做此项要求。"""
        if point.get("在线状态") != OFFLINE_STATUS:
            return []
        return [
            field
            for field in OFFLINE_REQUIRED_FIELDS
            if not str(point.get(field) or "").strip()
        ]

    def summary(self, station: str | None = None) -> dict[str, Any]:
        """按站点汇总在线率、离线时长与异常点位数；缺项点位单独列出并说明。"""
        stations = [station] if station else self.stations()
        rows = [self._station_summary(name) for name in stations]
        return {"stations": rows, "totals": self._totals(rows)}

    def _station_summary(self, station: str) -> dict[str, Any]:
        points = [row for row in store.rows(MODULE) if row.get("所属站点") == station]
        excluded = [
            {"点位编号": point.get("点位编号"), "缺失字段": missing}
            for point in points
            if (missing := self.missing_stat_fields(point))
        ]
        counted = [point for point in points if not self.missing_stat_fields(point)]
        online = sum(1 for point in counted if point.get("在线状态") == "在线")
        offline = sum(1 for point in counted if point.get("在线状态") == "离线")
        abnormal = sum(1 for point in counted if point.get("在线状态") == "画面异常")
        offline_minutes = sum(
            int(point.get("离线时长分钟") or 0)
            for point in counted
            if point.get("在线状态") == OFFLINE_STATUS
        )
        total_counted = len(counted)
        note = ""
        online_rate: float | None = None
        if not points:
            note = "该站点范围内暂未登记视频点位"
        elif total_counted == 0:
            note = "该站点点位均缺少统计必填项，在线率暂不计算"
        else:
            online_rate = round(online * 100 / total_counted, 1)
        return {
            "站点": station,
            "点位总数": len(points),
            "纳入统计": total_counted,
            "在线": online,
            "离线": offline,
            "画面异常": abnormal,
            "异常点位数": offline + abnormal,
            "离线时长分钟": offline_minutes,
            "在线率": online_rate,
            "未纳入点位": excluded,
            "说明": note,
        }

    def _totals(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        counted = sum(int(row["纳入统计"]) for row in rows)
        online = sum(int(row["在线"]) for row in rows)
        offline = sum(int(row["离线"]) for row in rows)
        abnormal = sum(int(row["画面异常"]) for row in rows)
        return {
            "站点": "全部站点",
            "点位总数": sum(int(row["点位总数"]) for row in rows),
            "纳入统计": counted,
            "在线": online,
            "离线": offline,
            "画面异常": abnormal,
            "异常点位数": offline + abnormal,
            "离线时长分钟": sum(int(row["离线时长分钟"]) for row in rows),
            "在线率": round(online * 100 / counted, 1) if counted else None,
            "未纳入点位": [item for row in rows for item in row["未纳入点位"]],
            "说明": "",
        }

    def list_inspections(
        self,
        *,
        point_id: int | None = None,
        point_code: str | None = None,
        station: str | None = None,
        limit: int | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """录像巡检记录：默认按巡检时刻倒序，列表与导出共用本方法保证条数一致。"""
        rows = store.rows(INSPECTION_MODULE)
        if point_id is not None:
            point = store.find(MODULE, point_id)
            if point is None:
                return [], 0
            point_code = str(point.get("点位编号", ""))
        if point_code:
            rows = [row for row in rows if row.get("点位编号") == point_code]
        if station:
            rows = [row for row in rows if row.get("所属站点") == station]
        rows = sorted(rows, key=lambda row: str(row.get("巡检时刻", "")), reverse=True)
        total = len(rows)
        if limit is not None:
            rows = rows[: max(limit, 0)]
        return rows, total
