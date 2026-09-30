"""
数据中心 API：搜索 MSDS 参考文件、预览、目录树。
"""
import os
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import FileResponse
from app.database import SessionLocal
from app.models.msds_index import MSDSIndex
from app.services.data_center_service import DataCenterService
from app.core.config import MSDS_DIR, REFERENCES_DIR
from app.core.audit_decorator import audit_action

router = APIRouter(prefix="/api/v1/data-center", tags=["data-center"])

_MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".json": "application/json",
}


def _content_disposition(filename: str, disposition: str = "attachment") -> str:
    """RFC 5987 Content-Disposition，兼容中文文件名（Latin-1 header 安全）。"""
    return f"{disposition}; filename=\"file\"; filename*=UTF-8''{quote(filename)}"


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
        media_type = _MEDIA_TYPES.get(ext, "application/octet-stream")

        filename = os.path.basename(file_path)
        headers = {"Content-Disposition": _content_disposition(filename, "inline")}
        return FileResponse(
            file_path,
            media_type=media_type,
            headers=headers,
        )
    finally:
        db.close()


# ------------------------------------------------------------
# POST /reindex — 手动重建索引（管理员用）
# ------------------------------------------------------------
@router.post("/reindex")
@audit_action("msds_reindex", "data-center")
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


# ------------------------------------------------------------
# GET /file?path=... — 通过文件路径直接读取文件
# ------------------------------------------------------------
@router.get("/file")
async def serve_file_by_path(path: str = Query(...)):
    """根据 file_path 直接读取 references/ 下的文件用于预览/下载"""
    # 安全检查：resolve 后必须落在 REFERENCES_DIR 内（拒绝同前缀兄弟目录与符号链接逃逸）
    try:
        request_path = Path(path).resolve()
        references_root = Path(REFERENCES_DIR).resolve()
    except (OSError, ValueError, RuntimeError):
        raise HTTPException(status_code=403, detail="Access denied")

    if not request_path.is_relative_to(references_root):
        raise HTTPException(status_code=403, detail="Access denied")

    if not request_path.is_file():
        raise HTTPException(status_code=404, detail="File not found on disk")

    ext = request_path.suffix.lower()
    media_type = _MEDIA_TYPES.get(ext, "application/octet-stream")

    # PDF 用 inline 显示（预览），其他用 attachment（下载）
    disposition = "inline" if ext == ".pdf" else "attachment"
    headers = {"Content-Disposition": _content_disposition(request_path.name, disposition)}

    return FileResponse(str(request_path), media_type=media_type, headers=headers)