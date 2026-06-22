"""
运输鉴定报告 API：搜索、预览（来自 references/海运鉴定报告/ 目录）。
"""
import os
from datetime import datetime
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.database import SessionLocal
from app.models.transport_report import TransportReport
from app.models.order_item_transport_report import OrderItemTransportReport
from app.services.transport_service import TransportService
from app.services.name_mapping_service import get_en_name, get_cn_name
from app.core.config import TRANSPORT_REPORTS_DIR

router = APIRouter(prefix="/api/v1/transport-reports", tags=["transport-reports"])


# ─── Request/Response models ────────────────────────────────────────────────

class LinkRequest(BaseModel):
    order_item_id: int
    transport_report_id: int


# ─── 搜索 ────────────────────────────────────────────────────────────────────

@router.get("/search")
async def search_transport_reports(q: str = Query("")):
    """在 transport_reports 表中搜索 PDF，匹配 filename / 报告编号 / 样品中英文名。"""
    db = SessionLocal()
    try:
        if not q.strip():
            records = db.query(TransportReport).limit(20).all()
        else:
            q_like = f"%{q}%"
            records = db.query(TransportReport).filter(
                (TransportReport.filename.like(q_like))
                | (TransportReport.report_no.like(q_like))
                | (TransportReport.product_name_cn.like(q_like))
                | (TransportReport.product_name_en.like(q_like))
            ).limit(50).all()

        items = [{
            "id": r.id,
            "filename": r.filename,
            "report_no": r.report_no or "",
            "product_name_cn": r.product_name_cn or "",
            "product_name_en": r.product_name_en or "",
            "sample_desc_cn": r.sample_desc_cn or "",
            "sample_desc_en": r.sample_desc_en or "",
        } for r in records]
        return {"items": items, "total": len(items)}
    finally:
        db.close()


@router.get("/search-by-name")
async def search_by_name(q: str = Query("")):
    """按品名（中文或英文）搜索，自动通过品名对照表转换后再查。

    用户输入 "皂洗粉" → 品名表查到 "皂洗剂" → 英文 "SOAPING AGENT" → 搜索匹配记录。
    用户输入 "ENZYME" → 品名表查到 "酶制剂" → 同时匹配中英文名。
    """
    db = SessionLocal()
    try:
        if not q.strip():
            return {"items": [], "total": 0}

        q_str = q.strip()

        # Step 1: 通过品名对照表做扩展搜索
        en_name = get_en_name(q_str)
        cn_name = get_cn_name(q_str)
        extra_names = []
        if en_name:
            extra_names.append(en_name)
        if cn_name:
            extra_names.append(cn_name)

        # 去重
        all_names = list(dict.fromkeys([q_str] + extra_names))

        # Step 2: 在 transport_reports 中模糊匹配
        all_items = []
        seen_ids = set()
        for name in all_names:
            name_like = f"%{name}%"
            records = db.query(TransportReport).filter(
                (TransportReport.filename.like(name_like))
                | (TransportReport.product_name_cn.like(name_like))
                | (TransportReport.product_name_en.like(name_like))
            ).limit(20).all()
            for r in records:
                if r.id not in seen_ids:
                    seen_ids.add(r.id)
                    all_items.append({
                        "id": r.id,
                        "filename": r.filename,
                        "report_no": r.report_no or "",
                        "product_name_cn": r.product_name_cn or "",
                        "product_name_en": r.product_name_en or "",
                        "sample_desc_cn": r.sample_desc_cn or "",
                        "sample_desc_en": r.sample_desc_en or "",
                        "matched_name": name,
                    })

        return {"items": all_items, "total": len(all_items), "query": q_str}
    finally:
        db.close()


# ─── 关联管理 ────────────────────────────────────────────────────────────────

@router.get("/linked/{order_item_id}")
async def get_linked_reports(order_item_id: int):
    """获取指定 order_item 已关联的所有运输鉴定报告。"""
    db = SessionLocal()
    try:
        links = db.query(OrderItemTransportReport).filter(
            OrderItemTransportReport.order_item_id == order_item_id
        ).order_by(OrderItemTransportReport.link_order).all()

        items = []
        for link in links:
            r = db.query(TransportReport).get(link.transport_report_id)
            if r:
                items.append({
                    "link_id": link.id,
                    "id": r.id,
                    "filename": r.filename,
                    "report_no": r.report_no or "",
                    "product_name_cn": r.product_name_cn or "",
                    "product_name_en": r.product_name_en or "",
                    "sample_desc_cn": r.sample_desc_cn or "",
                    "sample_desc_en": r.sample_desc_en or "",
                    "link_order": link.link_order,
                    "linked_at": link.linked_at.isoformat() if link.linked_at else None,
                })
        return {"items": items, "total": len(items)}
    finally:
        db.close()


@router.post("/link")
async def link_report(body: LinkRequest):
    """将运输鉴定报告关联到指定 order_item。"""
    db = SessionLocal()
    try:
        # 验证 transport_report 存在
        report = db.query(TransportReport).get(body.transport_report_id)
        if not report:
            raise HTTPException(status_code=404, detail="运输鉴定报告不存在")

        # 验证是否已关联
        existing = db.query(OrderItemTransportReport).filter(
            OrderItemTransportReport.order_item_id == body.order_item_id,
            OrderItemTransportReport.transport_report_id == body.transport_report_id,
        ).first()
        if existing:
            return {"message": "已关联，无需重复添加", "link_id": existing.id}

        # 获取当前最大 link_order
        max_order = db.query(OrderItemTransportReport.link_order).filter(
            OrderItemTransportReport.order_item_id == body.order_item_id,
        ).scalar() or 0

        link = OrderItemTransportReport(
            order_item_id=body.order_item_id,
            transport_report_id=body.transport_report_id,
            link_order=max_order + 1,
            linked_at=datetime.now(),
        )
        db.add(link)
        db.commit()

        return {
            "message": "关联成功",
            "link_id": link.id,
            "link_order": link.link_order,
        }
    finally:
        db.close()


@router.delete("/unlink/{link_id}")
async def unlink_report(link_id: int):
    """取消关联。"""
    db = SessionLocal()
    try:
        link = db.query(OrderItemTransportReport).get(link_id)
        if not link:
            raise HTTPException(status_code=404, detail="关联记录不存在")
        db.delete(link)
        db.commit()
        return {"message": "已取消关联"}
    finally:
        db.close()


# ─── PDF 预览 ────────────────────────────────────────────────────────────────

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
    """手动重建索引（管理员用）：扫描 PDF 目录，提取字段，落库。"""
    svc = TransportService()
    db = SessionLocal()
    try:
        count = svc.scan_directory(TRANSPORT_REPORTS_DIR, db)
        return {"indexed": count}
    finally:
        db.close()
