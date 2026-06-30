"""审计日志查询与导出 API"""
import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from fastapi.responses import StreamingResponse
import io

from app.api.deps import get_audit_service, get_current_user
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/v1/audit", tags=["审计日志"])


@router.get("/logs")
async def get_logs(
    user_name: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    module: Optional[str] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    service: AuditService = Depends(get_audit_service),
):
    result = service.query_logs(user_name, event_type, module, start_time, end_time, page, page_size)
    logs = [{
        "id": log.id,
        "event_type": log.event_type,
        "user_name": log.user_name,
        "module": log.module,
        "action_time": log.action_time.isoformat() if log.action_time else None,
        "detail": log.detail,
        "ip_address": log.ip_address,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    } for log in result["logs"]]
    return {"logs": logs, "total": result["total"], "page": result["page"], "page_size": result["page_size"]}


@router.get("/stats")
async def get_stats(
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    service: AuditService = Depends(get_audit_service),
):
    result = service.get_stats(start_time=start_time, end_time=end_time)
    return result


@router.get("/export")
async def export_logs(
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    service: AuditService = Depends(get_audit_service),
):
    from openpyxl import Workbook

    logs = service.export_logs(start_time=start_time, end_time=end_time)
    wb = Workbook()
    ws = wb.active
    ws.title = "行为日志"

    headers = ["ID", "事件类型", "用户名", "模块", "发生时间", "详情", "IP地址", "记录时间"]
    ws.append(headers)

    for log in logs:
        ws.append([
            log.id, log.event_type, log.user_name, log.module or "",
            log.action_time.isoformat() if log.action_time else "",
            log.detail or "", log.ip_address or "",
            log.created_at.isoformat() if log.created_at else "",
        ])

    ws.column_dimensions['A'].width = 8
    ws.column_dimensions['B'].width = 20
    ws.column_dimensions['C'].width = 15
    ws.column_dimensions['D'].width = 15
    ws.column_dimensions['E'].width = 22
    ws.column_dimensions['F'].width = 40
    ws.column_dimensions['G'].width = 15
    ws.column_dimensions['H'].width = 22

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)

    filename = f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@router.post("/batch")
async def batch_log(
    request: Request,
    user: dict = Depends(get_current_user),
    service: AuditService = Depends(get_audit_service),
):
    """
    批量接收前端埋点日志。

    注意：sendBeacon 发送 Content-Type: text/plain，
    所以这里用 Request.body() 手动解析，不依赖 FastAPI Pydantic。
    """
    body = await request.body()
    try:
        data = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    events = data.get("events", [])
    if not isinstance(events, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="events must be a list")

    for item in events:
        # 安全校验：禁止伪造其他用户的日志
        item_user = item.get("user_name")
        if item_user != user["name"]:
            raise HTTPException(status_code=403, detail="forbidden")

        try:
            action_time = datetime.fromisoformat(item.get("action_time", "").replace("Z", "+00:00"))
        except Exception:
            action_time = datetime.now()

        service.log(
            event_type=item.get("event_type"),
            user_name=item.get("user_name"),
            module=item.get("module"),
            action_time=action_time,
            detail=item.get("detail"),
            ip_address=item.get("ip_address"),
        )

    return {"success": True, "count": len(events)}
