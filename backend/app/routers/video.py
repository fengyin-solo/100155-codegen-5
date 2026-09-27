"""视频点位在线巡查接口：点位台账、按站点在线率汇总、点位详情与录像巡检记录。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import PageResult
from app.services.video import STATUSES, VideoService

router = APIRouter(prefix="/api/video", tags=["视频点位"])

service = VideoService()

LIST_FIELDS = ["点位编号", "点位名称", "所属站点", "监控画面地址", "在线状态", "最近离线时刻", "离线原因"]


@router.get("", response_model=PageResult[dict])
def list_points(
    station: str | None = Query(default=None, description="按所属站点筛选"),
    status: str | None = Query(default=None, description="在线、离线、画面异常"),
    keyword: str | None = Query(default=None, description="按点位编号或名称检索"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """视频点位台账；切到没有点位的站点范围时返回空页，由前端给出说明。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    if status is not None and status not in STATUSES:
        raise HTTPException(status_code=400, detail=f"在线状态仅支持：{'、'.join(STATUSES)}")
    items, total = service.list_points(
        station=station, status=status, keyword=keyword, page=page, size=size
    )
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/stations")
def list_stations() -> dict[str, object]:
    """站点巡查范围选项，包含尚未登记点位的站点。"""
    return {"stations": service.stations()}


@router.get("/summary")
def summary(station: str | None = Query(default=None, description="按所属站点汇总")) -> dict[str, Any]:
    """按站点排列在线率、离线时长、异常点位数；缺统计字段的点位不进在线率并说明缺项。"""
    return service.summary(station=station)


@router.get("/inspections/export")
def export_inspections(
    point_id: int | None = Query(default=None, description="按点位 id 过滤"),
    station: str | None = Query(default=None, description="按所属站点过滤"),
) -> dict[str, Any]:
    """导出录像巡检记录：与点位详情视图共用同一筛选函数，条数对得上。"""
    items, total = service.list_inspections(point_id=point_id, station=station)
    return {"module": "video_inspection", "total": total, "items": items}


@router.get("/{point_id}", response_model=dict)
def get_point(point_id: int) -> dict[str, Any]:
    """读取单个点位明细；不存在时给出可读的错误说明。"""
    point = service.get_point(point_id)
    if point is None:
        raise HTTPException(status_code=404, detail=f"视频点位 {point_id} 不存在或已撤点")
    return point


@router.get("/{point_id}/inspections")
def point_inspections(
    point_id: int,
    limit: int | None = Query(default=None, description="只取最近几条；不传则取全部"),
) -> dict[str, Any]:
    """列出点位最近几次录像巡检记录；total 与导出接口同源。"""
    point = service.get_point(point_id)
    if point is None:
        raise HTTPException(status_code=404, detail=f"视频点位 {point_id} 不存在或已撤点")
    items, total = service.list_inspections(point_id=point_id, limit=limit)
    return {"point": point, "items": items, "total": total}
