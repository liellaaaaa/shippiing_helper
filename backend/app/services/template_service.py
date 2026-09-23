# -*- coding: utf-8 -*-
"""客户定制清关模板服务 — 一客一单据类型一模板（录音方案 Phase C）。

首次用公共模板做完 → 另存为该客户模板 → 下次按 customer_code 自动调用。
客户模板 xlsx 可加行、改固定文案（多写说明），系统不再强制统一字段行。
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

from app.core.config import TEMPLATES
from app.database import SessionLocal
from app.models.customer_template import CustomerTemplate

logger = logging.getLogger(__name__)

_DOC_TYPE_TO_TEMPLATE = {
    "ci": "clearance_ci",
    "pl": "clearance_pl",
    "coa": "clearance_coa",
    "si": "clearance_si",
}

PUBLIC_TEMPLATE_NAME = {
    "ci": "CI-public.xlsx",
    "pl": "PL-public.xlsx",
    "coa": "COA-public.xlsx",
    "si": "SI-public.xlsx",
}


def get_active_customer_template(
    customer_code: Optional[str], doc_type: str
) -> Optional[CustomerTemplate]:
    if not customer_code:
        return None
    db = SessionLocal()
    try:
        return (
            db.query(CustomerTemplate)
            .filter(
                CustomerTemplate.customer_code == customer_code,
                CustomerTemplate.doc_type == doc_type,
                CustomerTemplate.is_active == 1,
            )
            .order_by(CustomerTemplate.version.desc())
            .first()
        )
    except Exception:
        # 表未建/连接异常时回退公共模板，避免整单 500
        return None
    finally:
        db.close()


def load_template_bytes(
    customer_code: Optional[str], doc_type: str
) -> tuple[bytes, str]:
    """返回 (xlsx_bytes, source) source=customer|public。"""
    try:
        row = get_active_customer_template(customer_code, doc_type)
        if row and row.template_blob:
            blob = row.template_blob
            if isinstance(blob, memoryview):
                blob = bytes(blob)
            return blob, "customer"
    except Exception:
        pass
    key = _DOC_TYPE_TO_TEMPLATE.get(doc_type)
    if not key:
        raise ValueError(f"Unknown clearance doc_type: {doc_type}")
    path = TEMPLATES[key]
    if not os.path.exists(path):
        raise FileNotFoundError(f"clearance template missing: {path}")
    with open(path, "rb") as f:
        return f.read(), "public"


def save_customer_template(
    customer_code: str,
    doc_type: str,
    template_blob: bytes,
    company_code: Optional[str] = None,
    options: Optional[dict[str, Any]] = None,
    created_by: Optional[str] = None,
    file_name: Optional[str] = None,
) -> dict:
    """另存/覆盖该客户模板（旧版停用，version+1）。"""
    if doc_type not in _DOC_TYPE_TO_TEMPLATE:
        raise ValueError(f"Unknown clearance doc_type: {doc_type}")
    if not customer_code:
        raise ValueError("customer_code required")
    if not template_blob:
        raise ValueError("template_blob required")

    db = SessionLocal()
    try:
        prev = (
            db.query(CustomerTemplate)
            .filter(
                CustomerTemplate.customer_code == customer_code,
                CustomerTemplate.doc_type == doc_type,
            )
            .order_by(CustomerTemplate.version.desc())
            .first()
        )
        version = (prev.version + 1) if prev else 1
        db.query(CustomerTemplate).filter(
            CustomerTemplate.customer_code == customer_code,
            CustomerTemplate.doc_type == doc_type,
            CustomerTemplate.is_active == 1,
        ).update({"is_active": 0})

        row = CustomerTemplate(
            customer_code=customer_code,
            doc_type=doc_type,
            company_code=company_code,
            template_blob=template_blob,
            options_json=json.dumps(options or {}, ensure_ascii=False),
            file_name=file_name or PUBLIC_TEMPLATE_NAME.get(doc_type, f"{doc_type}.xlsx"),
            version=version,
            is_active=1,
            created_by=created_by or "system",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return {
            "id": row.id,
            "customer_code": row.customer_code,
            "doc_type": row.doc_type,
            "version": row.version,
            "file_name": row.file_name,
        }
    finally:
        db.close()


def list_customer_templates(customer_code: Optional[str] = None) -> list[dict]:
    db = SessionLocal()
    try:
        q = db.query(CustomerTemplate).filter(CustomerTemplate.is_active == 1)
        if customer_code:
            q = q.filter(CustomerTemplate.customer_code == customer_code)
        rows = q.order_by(CustomerTemplate.customer_code, CustomerTemplate.doc_type).all()
        out = []
        for r in rows:
            options = {}
            if r.options_json:
                try:
                    options = json.loads(r.options_json)
                except json.JSONDecodeError:
                    options = {}
            out.append(
                {
                    "id": r.id,
                    "customer_code": r.customer_code,
                    "doc_type": r.doc_type,
                    "company_code": r.company_code,
                    "version": r.version,
                    "file_name": r.file_name,
                    "options": options,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                }
            )
        return out
    finally:
        db.close()


def delete_customer_template(template_id: int) -> bool:
    db = SessionLocal()
    try:
        row = db.query(CustomerTemplate).filter(CustomerTemplate.id == template_id).first()
        if not row:
            return False
        row.is_active = 0
        db.commit()
        return True
    finally:
        db.close()
