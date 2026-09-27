"""视频点位在线巡查业务规则：在线率统计口径、录像巡检记录与导出都收在这里。

统计口径约定：
- 在线率 = 在线点位数 / 纳入统计点位数，按站点分组；
- 离线点位缺「离线原因」时记录不完整，不纳入在线率统计，并在结果里说明缺了哪一项；
- 录像巡检记录的列表与导出共用同一条查询，保证导出条数与视图条数一致。
"""
from __future__ import annotations

from typing import Any

from app.store import store

POINTS_MODULE = "video"
INSPECTION_MODULE = "video_inspection"
STATION_MODULE = "station"

ONLINE_STATUSES = ["在线", "离线", "画面异常"]
# 离线点位必须登记的字段，缺失时不纳入在线率统计
REQUIRED_FOR_STATS = ["离线原因"]
DEFAULT_INSPECTION_LIMIT = 5
MAX_INSPECTION_LIMIT = 50


class VideoService:
    def list_points(
        self,
        *,
        station: str | None = None,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(POINTS_MODULE)
        if station:
            rows = [row for row in rows if row.get("所属站点") == station]
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("监控画面地址", ""))]
        if status:
            rows = [row for row in rows if row.get("在线状态") == status]
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def get_point(self, point_id: int) -> dict[str, Any] | None:
        return store.find(POINTS_MODULE, point_id)

    def stations(self) -> list[str]:
        """站点范围选项：站点台账与视频点位的并集，没装摄像头的站点也要能选中。"""
        names: list[str] = []
        for row in store.rows(STATION_MODULE):
            name = str(row.get("站点名称") or "").strip()
            if name and name not in names:
                names.append(name)
        for row in store.rows(POINTS_MODULE):
            name = str(row.get("所属站点") or "").strip()
            if name and name not in names:
                names.append(name)
        return names

    def _missing_fields(self, row: dict[str, Any]) -> list[str]:
        """离线点位缺「离线原因」时不满足统计口径，返回缺失字段清单。"""
        if row.get("在线状态") != "离线":
            return []
        return [
            field
            for field in REQUIRED_FOR_STATS
            if not str(row.get(field) or "").strip()
        ]

    def summary(self, *, station: str | None = None) -> dict[str, Any]:
        """按站点汇总在线率、离线时长与异常点位数；范围无数据时给出说明而不是空响应。"""
        points = store.rows(POINTS_MODULE)
        if station:
            points = [row for row in points if row.get("所属站点") == station]
        if not points:
            scope = f"「{station}」" if station else "当前站点范围"
            return {
                "items": [],
                "excluded": [],
                "note": "",
                "message": f"{scope}暂未登记视频点位，在线率、离线时长与异常点位数暂不统计",
            }

        groups: dict[str, list[dict[str, Any]]] = {}
        for row in points:
            name = str(row.get("所属站点") or "").strip() or "未分配站点"
            groups.setdefault(name, []).append(row)

        items: list[dict[str, Any]] = []
        excluded_all: list[dict[str, Any]] = []
        for name in sorted(groups):
            rows = groups[name]
            included: list[dict[str, Any]] = []
            excluded: list[dict[str, Any]] = []
            for row in rows:
                missing = self._missing_fields(row)
                if missing:
                    excluded.append({
                        "点位编号": row.get("点位编号"),
                        "缺失字段": "、".join(missing),
                    })
                else:
                    included.append(row)
            online = sum(1 for row in included if row.get("在线状态") == "在线")
            rate = round(100 * online / len(included), 1) if included else None
            duration = sum(int(row.get("累计离线时长（分钟）", 0) or 0) for row in rows)
            abnormal = sum(1 for row in rows if row.get("在线状态") == "画面异常")
            items.append({
                "站点": name,
                "点位总数": len(rows),
                "在线数": sum(1 for row in rows if row.get("在线状态") == "在线"),
                "离线数": sum(1 for row in rows if row.get("在线状态") == "离线"),
                "画面异常数": abnormal,
                "纳入统计数": len(included),
                "未纳入统计数": len(excluded),
                "在线率": rate,
                "离线时长分钟": duration,
                "异常点位数": abnormal,
                "excluded": excluded,
            })
            excluded_all.extend({**item, "站点": name} for item in excluded)

        note = ""
        if excluded_all:
            detail = "、".join(
                f"{item['点位编号']}（缺{item['缺失字段']}）" for item in excluded_all
            )
            note = f"{len(excluded_all)} 个点位未纳入在线率统计：{detail}"
        return {"items": items, "excluded": excluded_all, "note": note, "message": ""}

    def list_inspections(
        self,
        point_id: int,
        *,
        limit: int = DEFAULT_INSPECTION_LIMIT,
    ) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        """最近几次录像巡检记录；视图与导出都走这里，条数天然对得上。"""
        point = store.find(POINTS_MODULE, point_id)
        if point is None:
            return None, []
        rows = [
            row
            for row in store.rows(INSPECTION_MODULE)
            if int(row.get("point_id", 0)) == point_id
        ]
        rows.sort(key=lambda row: str(row.get("巡检时间", "")), reverse=True)
        return point, rows[:limit]
