"""
MSDS 自动化生成 API。

提供旧 MSDS 文件搜索、产品数据获取、MSDS 生成接口。
"""
import os
import base64
from fastapi import APIRouter, Query, Body
from pydantic import BaseModel
from typing import Optional
from app.services.msds_generator_service import MSDSGeneratorService
from app.services.onlyoffice_service import OnlyOfficeService
from app.models.shipment_doc import ShipmentDoc
from app.database import SessionLocal

router = APIRouter(prefix="/api/v1/msds-generator", tags=["msds-generator"])
msds_gen_svc = MSDSGeneratorService()
oo_svc = OnlyOfficeService()


class CompositionItem(BaseModel):
    component_cn: str
    cas: str
    percentage: str


class PhysicochemicalEdit(BaseModel):
    appearance: Optional[str] = None
    ion_type: Optional[str] = None
    ph: Optional[str] = None
    melting_point: Optional[str] = None
    boiling_point: Optional[str] = None
    density: Optional[str] = None
    flash_point: Optional[str] = None
    solubility: Optional[str] = None


class GenerateRequest(BaseModel):
    msds_file_path: str
    product_name: Optional[str] = None
    composition: list[CompositionItem] = []
    physicochemical: Optional[PhysicochemicalEdit] = None


@router.get("/search")
async def search_msds(keyword: str = Query(..., min_length=1)):
    """
    搜索 references/MSDS/ 目录中匹配的旧 MSDS 文件。
    """
    files = msds_gen_svc.search_msds(keyword)
    return {"files": files}


@router.post("/parse")
async def parse_msds(file_path: str = Body(..., embed=True)):
    """
    解析旧 MSDS 文件，提取产品信息、成分、理化特性。
    直接从文档解析，不查 customs_codes.json。
    """
    try:
        data = msds_gen_svc.parse_msds_file(file_path)
        return data
    except Exception as e:
        return {"error": str(e)}


@router.get("/products/search")
async def search_products(keyword: str = Query(..., min_length=1)):
    """
    从 customs_codes.json 搜索产品（按 customs_name 匹配）。
    """
    products = msds_gen_svc.search_products(keyword)
    return {"products": products}


@router.post("/product-data")
async def get_product_data(product_name: str = Body(..., embed=True)):
    """
    获取产品的预填数据（成分解析、外观等）。
    """
    product = msds_gen_svc.get_product_data(product_name)
    if not product:
        return {"product": None}

    # 解析成分
    components_str = product.get("components", "")
    composition = msds_gen_svc.parse_components(components_str)

    # 获取外观英文翻译
    appearance_cn = product.get("product_appearance", "")
    appearance_en = msds_gen_svc.translate_appearance(appearance_cn)

    # 获取产品名英文翻译
    product_name_en = msds_gen_svc.translate_product_name(product_name)

    return {
        "product": {
            "customs_name": product.get("customs_name", ""),
            "internal_code": product.get("internal_code", ""),
            "product_appearance": appearance_cn,
            "product_appearance_en": appearance_en,
            "product_name_en": product_name_en,
            "components": product.get("components", ""),
            "composition": composition,
        }
    }


@router.post("/generate")
async def generate_msds(request: GenerateRequest):
    """
    基于旧 MSDS 文件，生成新的 MSDS 文档。
    返回 OnlyOffice 配置，供前端直接打开编辑。
    """
    # 准备编辑内容
    edits = {
        "product_name": request.product_name or "",
        "composition": [
            {
                "component_cn": item.component_cn,
                "cas": item.cas,
                "percentage": item.percentage,
            }
            for item in request.composition
        ],
        "physicochemical": {},
    }

    # 处理理化特性
    if request.physicochemical:
        pc = request.physicochemical
        if pc.appearance:
            edits["physicochemical"]["外观与性状"] = pc.appearance
        if pc.ion_type:
            edits["physicochemical"]["离子性"] = pc.ion_type
        if pc.ph:
            edits["physicochemical"]["PH值"] = pc.ph
        if pc.melting_point:
            edits["physicochemical"]["熔点"] = pc.melting_point
        if pc.boiling_point:
            edits["physicochemical"]["沸点/沸点范围（℃）"] = pc.boiling_point
        if pc.density:
            edits["physicochemical"]["相对密度"] = pc.density
        if pc.flash_point:
            edits["physicochemical"]["闪点"] = pc.flash_point
        if pc.solubility:
            edits["physicochemical"]["溶解性"] = pc.solubility

    # 获取产品数据（用于生成 doc_key）
    product_data = {}
    if request.product_name:
        product_data = msds_gen_svc.get_product_data(request.product_name) or {}

    # 生成 MSDS
    content, doc_key = msds_gen_svc.generate_msds(
        msds_file_path=request.msds_file_path,
        product_data=product_data,
        edits=edits
    )

    # 保存并创建 OnlyOffice 配置
    token, config, safe_key = oo_svc.create_config(doc_key, "docx")
    _save_doc_to_db(doc_key, "msds", content, storage_key=safe_key)

    api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
    callback_base = os.getenv("ONLYOFFICE_CALLBACK_BASE_URL", "http://host.docker.internal:8000")

    return {
        **config,
        "url": f"{callback_base}/api/v1/onlyoffice/download/{safe_key}",
        "downloadUrl": f"{api_base}/api/v1/onlyoffice/download/{safe_key}",
    }


def _save_doc_to_db(doc_key: str, doc_type: str, content: bytes, storage_key: str = None):
    """保存文档到数据库"""
    db = SessionLocal()
    try:
        import hashlib
        content_hash = hashlib.md5(content).hexdigest()

        # 检查是否已存在
        existing = db.query(ShipmentDoc).filter(
            ShipmentDoc.content_hash == content_hash
        ).first()
        if existing:
            return existing.id

        # Use storage_key (UUID) as doc_key if provided, for OnlyOffice routing compatibility
        store_key = storage_key if storage_key else doc_key
        doc = ShipmentDoc(
            doc_key=store_key,
            doc_type=doc_type,
            file_blob=base64.b64encode(content).decode(),
            content_hash=content_hash,
            version=1,
            file_name=f"{doc_key}.docx",
            created_by="system",
        )
        db.add(doc)
        db.commit()
        return doc.id
    finally:
        db.close()
