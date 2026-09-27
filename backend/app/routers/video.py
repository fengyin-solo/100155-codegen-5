"""视频点位在线巡查接口：点位列表、站点汇总、录像巡检记录与导出。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import PageResult
from app.services.video import (
    DEFAULT_INSPECTION_LIMIT,
    MAX_INSPECTION_LIMIT,
    ONLINE_STATUSES,
    VideoService,
)

router = APIRouter(prefix="/api/video", tags=["视频巡查"])

service = VideoService()


@router.get("/points", response_model=PageResult[dict])
def list_points(
    station: str | None = Query(default=None, description="站点范围，空为全部站点"),
    keyword: str | None = Query(default=None, description="按监控画面地址检索"),
    status: str | None = Query(default=None, description="在线、离线、画面异常"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按站点、监控画面地址与在线状态过滤视频点位；没有数据时返回空页，不报错。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    if status and status not in ONLINE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"在线状态只支持：{'、'.join(ONLINE_STATUSES)}",
        )
    items, total = service.list_points(
        station=station, keyword=keyword, status=status, page=page, size=size
    )
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/stations")
def list_stations() -> dict[str, Any]:
    """站点范围选项：含暂未登记视频点位的站点，便于巡查时确认覆盖情况。"""
    return {"items": service.stations()}


@router.get("/summary")
def summary(
    station: str | None = Query(default=None, description="站点范围，空为全部站点"),
) -> dict[str, Any]:
    """按站点汇总在线率、离线时长与异常点位数；缺离线原因的点位不纳入统计并逐项说明。"""
    return service.summary(station=station or None)


@router.get("/points/{point_id}", response_model=dict)
def get_point(point_id: int) -> dict:
    """读取单个视频点位明细；不存在时给出可读的错误说明。"""
    point = service.get_point(point_id)
    if point is None:
        raise HTTPException(status_code=404, detail=f"视频点位 {point_id} 不存在或已拆除")
    return point


@router.get("/points/{point_id}/inspections")
def list_inspections(
    point_id: int,
    limit: int = Query(default=DEFAULT_INSPECTION_LIMIT, ge=1, le=MAX_INSPECTION_LIMIT),
) -> dict[str, Any]:
    """最近几次录像巡检记录，按巡检时间倒序。"""
    point, items = service.list_inspections(point_id, limit=limit)
    if point is None:
        raise HTTPException(status_code=404, detail=f"视频点位 {point_id} 不存在或已拆除")
    return {"point_id": point_id, "limit": limit, "total": len(items), "items": items}


@router.get("/points/{point_id}/inspections/export")
def export_inspections(
    point_id: int,
    limit: int = Query(default=DEFAULT_INSPECTION_LIMIT, ge=1, le=MAX_INSPECTION_LIMIT),
) -> dict[str, Any]:
    """导出最近录像巡检记录：与视图共用同一查询，导出条数与视图条数一致。"""
    point, items = service.list_inspections(point_id, limit=limit)
    if point is None:
        raise HTTPException(status_code=404, detail=f"视频点位 {point_id} 不存在或已拆除")
    return {
        "module": "video_inspection",
        "point_id": point_id,
        "点位编号": point.get("点位编号"),
        "total": len(items),
        "items": items,
    }
