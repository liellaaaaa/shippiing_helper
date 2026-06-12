"""
数据中心 API：搜索 MSDS 参考文件、预览、修正上传。
"""
import os
from datetime import datetime

from fastapi import APIRouter, Query, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from app.database import SessionLocal
from app.models.msds_index import MSDSIndex
from app.models.msds_correction import MSDSCorrection
from app.services.data_center_service import DataCenterService
from app.services.msds_service import MSDSService
from app.core.config import MSDS_DIR, REFERENCES_DIR

router = APIRouter(prefix="/api/v1/data-center", tags=["data-center"])


# ------------------------------------------------------------
# GET /search — 三级优先级搜索
# ------------------------------------------------------------
@router.get("/search")
async def search_msds(q: str = Query("")):
    svc = DataCenterService()
    db = SessionLocal()
    try:
        results = svc.search_msds(q, db)
        items = []
        for r in results:
            record = db.query(MSDSIndex).filter(
                MSDSIndex.filename == r["filename"]
            ).first()
            if record:
                items.append({
                    "id": record.id,
                    "filename": record.filename,
                    "product_name_cn": record.product_name_cn,
                    "physical_form": record.physical_form,
                    "ion_type": record.ion_type,
                    "ph": record.ph,
                    "file_format": record.file_format,
                    "match_type": r["match_type"],
                    "file_path": record.file_path,
                })
        return {"items": items, "total": len(items)}
    finally:
        db.close()


# ------------------------------------------------------------
# GET /files/{file_id} — 预览文件（正确 Content-Type）
# ------------------------------------------------------------
@router.get("/files/{file_id}")
async def serve_msds_file(file_id: int):
    db = SessionLocal()
    try:
        record = db.query(MSDSIndex).filter(MSDSIndex.id == file_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="File not found")

        file_path = record.file_path
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found on disk")

        ext = os.path.splitext(file_path)[1].lower()
        media_types = {
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }
        media_type = media_types.get(ext, "application/octet-stream")

        headers = {"Content-Disposition": "inline; filename*=utf-8''"}
        return FileResponse(
            file_path,
            media_type=media_type,
            headers=headers,
        )
    finally:
        db.close()


# ------------------------------------------------------------
# POST /upload-corrected/{file_id} — 上传修正版
# ------------------------------------------------------------
@router.post("/upload-corrected/{file_id}")
async def upload_corrected_msds(
    file_id: int,
    file: UploadFile = File(...),
    user: str = Query("admin"),
):
    content = await file.read()
    original_filename = file.filename or "unknown"

    svc = DataCenterService()
    db = SessionLocal()
    try:
        result = svc.upload_corrected_msds(
            file_id=file_id,
            file_content=content,
            original_filename=original_filename,
            user=user,
            db_session=db,
        )
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    finally:
        db.close()


# ------------------------------------------------------------
# POST /reindex — 手动重建索引（管理员用）
# ------------------------------------------------------------
@router.post("/reindex")
async def reindex_msds():
    svc = DataCenterService()
    db = SessionLocal()
    try:
        count = svc.scan_msds_directory(MSDS_DIR, db)
        return {"indexed": count}
    finally:
        db.close()


# ------------------------------------------------------------
# GET /summary/{file_id} — 获取 MSDS 摘要
# ------------------------------------------------------------
@router.get("/summary/{file_id}")
async def get_msds_summary(file_id: int):
    svc = DataCenterService()
    db = SessionLocal()
    try:
        result = svc.get_msds_summary(file_id, db)
        if not result:
            raise HTTPException(status_code=404, detail="MSDS not found")
        return result
    finally:
        db.close()


# ------------------------------------------------------------
# GET /tree — 返回完整 references/ 目录树
# ------------------------------------------------------------
def count_leaves(nodes):
    total = 0
    for node in nodes:
        if node.get("isLeaf"):
            total += 1
        elif node.get("children"):
            total += count_leaves(node["children"])
    return total


@router.get("/tree")
async def get_data_center_tree():
    svc = DataCenterService()
    tree = svc.get_directory_tree(REFERENCES_DIR)
    return {"tree": tree, "total": count_leaves(tree)}