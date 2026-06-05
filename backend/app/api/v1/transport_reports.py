"""
运输鉴定报告 API：搜索、预览（来自 references/海运鉴定报告/ 目录）。
"""
import os
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import FileResponse
from app.database import SessionLocal
from app.models.transport_report import TransportReport
from app.services.transport_service import TransportService
from app.core.config import TRANSPORT_REPORTS_DIR

router = APIRouter(prefix="/api/v1/transport-reports", tags=["transport-reports"])


@router.get("/search")
async def search_transport_reports(q: str = Query("")):
    """在 references/海运鉴定报告/ 目录中搜索 PDF，匹配文件名或内容。"""
    svc = TransportService()
    db = SessionLocal()
    try:
        results = svc.search(query=q, db_session=db)
        # results 是 [{"filename": ..., "match_type": ...}]
        items = []
        for r in results:
            record = db.query(TransportReport).filter(
                TransportReport.filename == r["filename"]
            ).first()
            if record:
                fields = svc.get_cached_fields(r["filename"]) or {}
                items.append({
                    "id": record.id,
                    "filename": record.filename,
                    "file_path": record.file_path,
                    "match_type": r["match_type"],
                    "report_no": fields.get("report_no", ""),
                    "sample_description": fields.get("sample_description", ""),
                })
        return {"items": items, "total": len(items)}
    finally:
        db.close()


@router.get("/files/{filename}")
async def serve_transport_report(filename: str):
    """预览 PDF（inline），避免浏览器下载。"""
    db = SessionLocal()
    try:
        record = db.query(TransportReport).filter(
            TransportReport.filename == filename
        ).first()
        if not record:
            raise HTTPException(status_code=404, detail="File not found")
        file_path = record.file_path
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found on disk")
        headers = {"Content-Disposition": "inline; filename*=utf-8''"}
        return FileResponse(
            file_path,
            media_type="application/pdf",
            headers=headers,
        )
    finally:
        db.close()


@router.post("/reindex")
async def reindex_transport_reports():
    """手动重建索引（管理员用）。"""
    svc = TransportService()
    db = SessionLocal()
    try:
        count = svc.scan_directory(TRANSPORT_REPORTS_DIR, db)
        return {"indexed": count}
    finally:
        db.close()
