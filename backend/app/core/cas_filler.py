"""
报关成分 CAS 号自动补全。

对成分文本中缺 CAS 的组分（如「水 10%」），从成分库 IngredientMapping
按名称回填 CAS（→「水 7732-18-5 10%」）。合并预览阶段调用，源头补全后
下游 MSDS / 报关比对不再因缺号反复误判为新配方。
"""
from __future__ import annotations

import json
import re

from app.database import SessionLocal
from app.models.reference_data import IngredientMapping

CAS_RE = re.compile(r"\d{2,7}-\d{1,2}-\d{1,3}")
PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*[%％]")
# 按 + / 逗号 / 分号 / 换行 分块，保留分隔符以便原样拼回
SPLIT_RE = re.compile(r"(\s*(?:\+|，|,|；|;|\n)\s*)")


def load_name_to_cas() -> dict[str, str]:
    """从成分库加载「成分名 → CAS」映射（取每条的第一个 CAS）。"""
    db = SessionLocal()
    try:
        mapping: dict[str, str] = {}
        for row in db.query(IngredientMapping).all():
            try:
                cn_names = json.loads(row.cn_names or "[]")
                cas_numbers = json.loads(row.cas_numbers or "[]")
            except (json.JSONDecodeError, TypeError):
                continue
            cas = (cas_numbers[0] if cas_numbers else "") or ""
            cas = cas.strip()
            if not cas:
                continue
            for name in cn_names or []:
                key = (name or "").strip()
                if key and key not in mapping:
                    mapping[key] = cas
        return mapping
    finally:
        db.close()


def _norm_name(s: str) -> str:
    return re.sub(r"\s+", "", (s or "").strip().lower())


def _lookup_cas(name: str, name_to_cas: dict[str, str]) -> str:
    if not name:
        return ""
    if name in name_to_cas:
        return name_to_cas[name]
    target = _norm_name(name)
    if not target:
        return ""
    for key, cas in name_to_cas.items():
        if _norm_name(key) == target:
            return cas
    return ""


def _fill_segment(segment: str, name_to_cas: dict[str, str]) -> tuple[str, str | None]:
    """补全单个组分片段。已有 CAS 则原样返回。"""
    if not segment or CAS_RE.search(segment):
        return segment, None

    pct = PCT_RE.search(segment)
    name_part = segment[: pct.start()] if pct else segment
    name = re.sub(r"^[\s：:、，,；;+]+|[\s：:、，,；;+]+$", "", name_part).strip()
    if not name:
        return segment, None

    cas = _lookup_cas(name, name_to_cas)
    if not cas:
        return segment, None

    rest = segment[pct.start() :].strip() if pct else ""
    filled = f"{name} {cas} {rest}".strip() if rest else f"{name} {cas}"
    filled = re.sub(r"[ \t]{2,}", " ", filled)
    return filled, name


def fill_missing_cas(
    text: str | None, name_to_cas: dict[str, str] | None = None
) -> tuple[str, list[str]]:
    """
    补全成分文本中缺失的 CAS 号。

    返回 (新文本, 被补全的成分名列表)。查不到 CAS 的组分保持原样。
    已有 CAS 的组分（含括号形式「水（7732-18-5）」）原样保留，不会二次填号。
    """
    if not text or not str(text).strip():
        return text or "", []

    raw = str(text)
    if name_to_cas is None:
        name_to_cas = load_name_to_cas()
    if not name_to_cas:
        return raw, []

    pieces = SPLIT_RE.split(raw)
    filled_names: list[str] = []
    out: list[str] = []
    for piece in pieces:
        if piece is None:
            continue
        # 分隔符原样保留
        if SPLIT_RE.fullmatch(piece):
            out.append(piece)
            continue
        new_piece, filled = _fill_segment(piece, name_to_cas)
        if filled:
            filled_names.append(filled)
        out.append(new_piece)

    return "".join(out), filled_names
