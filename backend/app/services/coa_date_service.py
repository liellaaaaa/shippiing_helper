"""COA 批号 → 生产日期；有效期规则。

批号样例：SA + YYYYMMDD + 序号（SA20260626017 → 2026-06-26）。
有效期两套规则并存，禁止写死单一规则。
"""
import re
from datetime import date, timedelta
from typing import Optional

_BATCH_RE = re.compile(r"^SA(\d{8})", re.IGNORECASE)

EXPIRY_RULES = ("plus_1y_minus_1d", "plus_6m_minus_1d", "manual")


def parse_production_date_from_batch(batch_no: Optional[str]) -> Optional[date]:
    if not batch_no:
        return None
    m = _BATCH_RE.match(str(batch_no).strip())
    if not m:
        return None
    raw = m.group(1)
    try:
        return date(int(raw[0:4]), int(raw[4:6]), int(raw[6:8]))
    except ValueError:
        return None


def _add_months(d: date, months: int) -> date:
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    day = d.day
    while True:
        try:
            return date(y, m, day)
        except ValueError:
            day -= 1


def compute_expiry_date(production: Optional[date], rule: Optional[str]) -> Optional[date]:
    if not production or not rule:
        return None
    if rule == "plus_1y_minus_1d":
        return date(production.year + 1, production.month, production.day) - timedelta(days=1)
    if rule == "plus_6m_minus_1d":
        return _add_months(production, 6) - timedelta(days=1)
    return None
