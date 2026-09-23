"""清关单据编号：合同号 → 发票号 / 箱单号。

规则对齐 document_service._to_invoice_no，并抽出 PL 版本。
IN/PL 开头必须幂等，禁止二次替换。
"""
from __future__ import annotations

import re

_COMPANY_PREFIXES = ("HT", "HH", "MH")


def _to_prefixed_no(contract_no: str | None, out_prefix: str) -> str:
    if not contract_no:
        return ""
    s = str(contract_no).strip()
    if not s:
        return ""
    if s.startswith(out_prefix):
        return s
    for prefix in _COMPANY_PREFIXES:
        if s.startswith(prefix):
            return out_prefix + s[len(prefix):]
    m = re.search(r"\d", s)
    if m:
        return out_prefix + s[m.start():]
    return out_prefix + s


def to_invoice_no(contract_no: str | None) -> str:
    """HT260720SZ → IN260720SZ；IN 开头原样返回。"""
    return _to_prefixed_no(contract_no, "IN")


def to_packing_no(contract_no: str | None) -> str:
    """HT260720SZ → PL260720SZ；PL 开头原样返回。"""
    return _to_prefixed_no(contract_no, "PL")
