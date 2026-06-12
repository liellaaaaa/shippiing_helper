"""
品名对照 API。
GET /api/v1/name-mapping - 获取所有对照数据
GET /api/v1/name-mapping/lookup?cn=xxx - 中文查英文
GET /api/v1/name-mapping/lookup?en=xxx - 英文查中文
"""
from fastapi import APIRouter
from typing import Optional

from app.services.name_mapping_service import get_all_mappings, get_en_name, get_cn_name

router = APIRouter(prefix="/name-mapping", tags=["品名对照"])


@router.get("")
async def get_all():
    """获取所有品名对照数据"""
    return {"mappings": get_all_mappings()}


@router.get("/lookup")
async def lookup(cn: Optional[str] = None, en: Optional[str] = None):
    """查询对应语言名称"""
    if cn:
        result = get_en_name(cn)
        return {"cn": cn, "en": result} if result else {"cn": cn, "en": None}
    if en:
        result = get_cn_name(en)
        return {"en": en, "cn": result} if result else {"en": en, "cn": None}
    return {"error": "请提供 cn 或 en 参数"}