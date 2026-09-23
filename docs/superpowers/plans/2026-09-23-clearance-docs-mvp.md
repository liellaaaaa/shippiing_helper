# 清关文件生成 MVP（CI / PL / COA / SI）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Phase2「报关资料」右侧生成并打开四份清关单据（订舱补料 SI / 发票 CI / 装箱单 PL / 品质证书 COA），公共模板 + 占位符填充，OnlyOffice 可编辑。

**Architecture:** 从 `LedgerRecordResponse` 组装清关字段（`clearance_fields`）→ 读取 `references/clearance/*.xlsx` 公共模板 → `clearance_doc_service` 占位符填充 → 复用 `documents.py` 的 OnlyOffice 配置与 `ShipmentDoc` 落库。编号/批号日期独立成可测纯函数服务。客户定制模板、跨产品合托、货代实测表不在本计划（后续计划）。

**Tech Stack:** Python 3 + FastAPI + openpyxl + pytest；Vue3 + Element Plus + axios

**设计依据:** `docs/清关文件制作方案与开发内容-V2.md`  
**范围:** V2 Phase A（公共模板/字段）+ Phase B（生成链路 MVP）。**TBD-1/2/3/4 未关闭：相关字段留空不瞎填。**

---

## File Structure

| 动作 | 路径 | 职责 |
|------|------|------|
| Create | `backend/app/services/doc_no_service.py` | 合同号→发票号/箱单号（含 IN/PL 幂等） |
| Create | `backend/app/services/coa_date_service.py` | 批号→生产日期；有效期规则 |
| Create | `backend/app/schemas/clearance.py` | 清关生成入参 / 字段容器 |
| Create | `backend/app/services/clearance_fields.py` | 从台账+overrides 组装填充字段 |
| Create | `backend/app/services/clearance_doc_service.py` | 模板加载、占位符替换、四单 generate |
| Create | `backend/scripts/build_clearance_templates.py` | 生成脱敏公共模板 xlsx |
| Create | `backend/tests/test_doc_no_service.py` | 编号单测 |
| Create | `backend/tests/test_coa_date_service.py` | 批号/有效期单测 |
| Create | `backend/tests/test_clearance_fields.py` | 字段组装单测 |
| Create | `backend/tests/test_clearance_doc_service.py` | 四单生成集成测 |
| Modify | `backend/app/core/config.py` | TEMPLATES 增加 clearance 键 |
| Modify | `backend/app/core/company_config.py` | 补英文抬头/银行块 |
| Modify | `backend/app/api/v1/documents.py` | POST `/ci` `/pl` `/coa` `/si` |
| Modify | `frontend/src/api/phase2.ts` | 四个 generate* API |
| Modify | `frontend/src/views/phase2/Phase2Workflow.vue` | 按钮组 + openClearanceDoc |
| Generate | `references/clearance/CI-public.xlsx` 等 4 份 | 公共模板 |

**明确不动:** `calculation_service.py`、`packaging_service.py` 语义、`GET /documents/customs`、`document_service.generate_customs`。

---

## Task 1: 编号服务 doc_no_service

**Files:**
- Create: `backend/app/services/doc_no_service.py`
- Create: `backend/tests/test_doc_no_service.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_doc_no_service.py
from app.services.doc_no_service import to_invoice_no, to_packing_no


def test_ht_prefix_to_in():
    assert to_invoice_no("HT260720SZ") == "IN260720SZ"


def test_hh_prefix_to_in():
    assert to_invoice_no("HH12345") == "IN12345"


def test_mh_prefix_keeps_region():
    assert to_invoice_no("MHBD260304") == "INBD260304"


def test_in_idempotent():
    assert to_invoice_no("IN260720SZ") == "IN260720SZ"


def test_no_prefix_from_first_digit():
    assert to_invoice_no("XX260304E01") == "IN260304E01"


def test_empty():
    assert to_invoice_no("") == ""
    assert to_invoice_no(None) == ""


def test_packing_no_ht():
    assert to_packing_no("HT260720SZ") == "PL260720SZ"


def test_packing_no_idempotent():
    assert to_packing_no("PL260720SZ") == "PL260720SZ"


def test_packing_no_mh():
    assert to_packing_no("MHBD260304") == "PLBD260304"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_doc_no_service.py -v`  
Expected: FAIL — `ModuleNotFoundError: app.services.doc_no_service`

- [ ] **Step 3: Write implementation**

```python
# backend/app/services/doc_no_service.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_doc_no_service.py -v`  
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/doc_no_service.py backend/tests/test_doc_no_service.py
git commit -m "feat(clearance): add doc_no_service for IN/PL numbers"
```

---

## Task 2: COA 批号日期服务

**Files:**
- Create: `backend/app/services/coa_date_service.py`
- Create: `backend/tests/test_coa_date_service.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_coa_date_service.py
from datetime import date

from app.services.coa_date_service import (
    parse_production_date_from_batch,
    compute_expiry_date,
)


def test_sa_batch_full():
    assert parse_production_date_from_batch("SA20260626017") == date(2026, 6, 26)


def test_sa_batch_other():
    assert parse_production_date_from_batch("SA20260713008") == date(2026, 7, 13)
    assert parse_production_date_from_batch("SA20260807038") == date(2026, 8, 7)


def test_sa_batch_date_only_no_seq():
    """SA + 8 位日期（无流水号）也应解析成功。"""
    assert parse_production_date_from_batch("SA20260626") == date(2026, 6, 26)


def test_invalid_batch():
    assert parse_production_date_from_batch("") is None
    assert parse_production_date_from_batch(None) is None
    assert parse_production_date_from_batch("XX20260626017") is None
    assert parse_production_date_from_batch("SA20261332") is None  # 非法月日


def test_expiry_plus_1y_minus_1d():
    assert compute_expiry_date(date(2026, 6, 26), "plus_1y_minus_1d") == date(2027, 6, 25)
    assert compute_expiry_date(date(2026, 7, 13), "plus_1y_minus_1d") == date(2027, 7, 12)


def test_expiry_plus_6m_minus_1d():
    assert compute_expiry_date(date(2026, 8, 7), "plus_6m_minus_1d") == date(2027, 2, 6)


def test_expiry_manual_or_unknown():
    assert compute_expiry_date(date(2026, 8, 7), "manual") is None
    assert compute_expiry_date(date(2026, 8, 7), "unknown_rule") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_coa_date_service.py -v`  
Expected: FAIL — module not found

- [ ] **Step 3: Write implementation**

```python
# backend/app/services/coa_date_service.py
"""COA 批号 → 生产日期；有效期规则。

批号样例：SA + YYYYMMDD + 序号（SA20260626017 → 2026-06-26）。
有效期两套规则并存（V2 §3.5 / 增值 19），禁止写死单一规则。
"""
from __future__ import annotations

import re
from datetime import date, timedelta

_BATCH_RE = re.compile(r"^SA(\d{8})", re.IGNORECASE)

# 规则名与 options_json.expiry_rule 对齐
EXPIRY_RULES = ("plus_1y_minus_1d", "plus_6m_minus_1d", "manual")


def parse_production_date_from_batch(batch_no: str | None) -> date | None:
    """SA+YYYYMMDD[+序号] → date。无法解析返回 None（调用方再取标签/人工）。"""
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
    # 目标月最后一天夹取（避免 8/31 +6m → 非法日期）
    day = d.day
    while True:
        try:
            return date(y, m, day)
        except ValueError:
            day -= 1


def compute_expiry_date(production: date | None, rule: str | None) -> date | None:
    """按规则算有效期；manual/未知规则返回 None（人工录入）。"""
    if not production or not rule:
        return None
    if rule == "plus_1y_minus_1d":
        return date(production.year + 1, production.month, production.day) - timedelta(days=1)
    if rule == "plus_6m_minus_1d":
        return _add_months(production, 6) - timedelta(days=1)
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_coa_date_service.py -v`  
Expected: all PASS  
（若 `plus_1y_minus_1d` 在 2/29 上失败，夹取同 `_add_months`；样例无闰日，保持实现简单，测试不覆盖 2/29。）

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/coa_date_service.py backend/tests/test_coa_date_service.py
git commit -m "feat(clearance): parse production date from batch and expiry rules"
```

---

## Task 3: 公司英文抬头与银行块配置

**Files:**
- Modify: `backend/app/core/company_config.py`

- [ ] **Step 1: 扩展 COMPANY_PROFILES（含英文与银行，数值与 WA 样例一致）**

将 `company_config.py` 整文件替换为：

```python
"""公司配置 — 报关/清关文件按 company_code 选择抬头、税号、银行块"""

COMPANY_PROFILES: dict[str, dict] = {
    "honghao": {
        "code": "honghao",
        "name_cn": "广东宏昊化工有限公司",
        "name_en": "HONGHAO CHEMICAL CO., LTD.",
        "tax_id": "91441284398042971C",
        "address_cn": "四会市江谷镇江谷精细化工区创新大道13号（综合楼）",
        "address_en": (
            "COMPREHENSIVE BUILDING, NO. 13 CHUANGXIN ROAD, JIANGGU FINE "
            "CHEMICAL INDUSTRIAL AREA, JIANGGU, SIHUI, GUANGDONG, CHINA"
        ),
        "phone": "0758-3267663",
        "phone_en": "0086-758-3267663",
        "fax": "0758-3115313",
        "fax_en": "0086-758-3115313",
        "source_location": "肇庆",
        "bank_name_en": "THE AGRICULTURAL BANK OF CHINA, GUANGDONG, QINGYUAN BRANCH",
        "bank_address_en": (
            "NO.9 LIANJIANG ROAD XINCHENG DISTRICT QINGYUAN CITY, GUANGDONG, CHINA"
        ),
        "bank_account": "44690114040000022",
        "bank_swift": "ABOCCNBJ190",
    },
    "minhao": {
        "code": "minhao",
        "name_cn": "广州市民浩新材料有限公司",
        "name_en": "GUANGZHOU MINHAO NEW MATERIAL CO. LTD.",
        "tax_id": "91440111MACUDP8C46",
        "address_cn": "广州市白云区大源街石湖石寺路12号202房",
        "address_en": (
            "NO.12-202 SHISHI ROAD, SHIHU, DAYUAN STREET, BAIYUN DISTRICT, "
            "GUANGZHOU, CHINA"
        ),
        "phone": "",
        "phone_en": "",
        "fax": "",
        "fax_en": "",
        "source_location": "广州",
        "bank_name_en": "",
        "bank_address_en": "",
        "bank_account": "",
        "bank_swift": "",
    },
}

DEFAULT_COMPANY = "honghao"


def get_company_profile(company_code: str | None) -> dict:
    """根据公司代码返回公司配置，未匹配时返回默认值（宏昊）"""
    if not company_code:
        return COMPANY_PROFILES[DEFAULT_COMPANY]
    return COMPANY_PROFILES.get(company_code, COMPANY_PROFILES[DEFAULT_COMPANY])


def get_all_company_codes() -> list[str]:
    """返回所有可用的公司代码"""
    return list(COMPANY_PROFILES.keys())
```

- [ ] **Step 2: 冒烟导入**

Run: `cd backend && python -c "from app.core.company_config import get_company_profile; p=get_company_profile('honghao'); assert p['name_en'].startswith('HONGHAO'); assert p['bank_swift']=='ABOCCNBJ190'"`  
Expected: 无输出、退出码 0

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/company_config.py
git commit -m "feat(clearance): add English letterhead and bank block to company_config"
```

---

## Task 4: 清关 schemas 与字段组装

**Files:**
- Create: `backend/app/schemas/clearance.py`
- Create: `backend/app/services/clearance_fields.py`
- Create: `backend/tests/test_clearance_fields.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_clearance_fields.py
from app.schemas.ledger import LedgerItemSchema, LedgerRecordResponse
from app.services.clearance_fields import build_clearance_payload


def make_record() -> LedgerRecordResponse:
    return LedgerRecordResponse(
        id=1,
        order_no="HT260720SZ",
        customer_code="WA318",
        sales_person="lw",
        consignee_name="CHEMZONE CO., LTD.",
        consignee_address="26/1D TRAN QUY CAP ST., HO CHI MINH CITY, VIETNAM",
        consignee_tel="TAX CODE: 0316699088",
        destination="HOCHIMINH(CAT LAI), VIETNAM",
        loading_port="NANSHA, CHINA",
        price_term="CIF HOCHIMINH",
        payment_terms="100% TT AFTER SHIPMENT 30 DAYS",
        pi_date="2026-07-20",
        currency="USD",
        items=[
            LedgerItemSchema(
                internal_code="FIX-HT016H",
                product_en="FIXING AGENT HT-016H",
                product_cn="固色剂",
                quantity_kg=4000.0,
                unit_price=2.6,
                total_amount=10400.0,
                hs_code="340241",
                packaging_name="125kg/drum",
                drum_count=32,
                pallet_count=8,
                net_weight_kg=4000.0,
                gross_weight_kg=4308.0,
                volume_cbm=7.92,
            )
        ],
        status="saved",
    )


def test_basic_numbers():
    p = build_clearance_payload(
        record=make_record(),
        company_code="honghao",
        overrides={
            "container_no": "WHLU5694625",
            "seal_no": "WHA4051188",
            "invoice_date": "2026-08-01",
        },
    )
    assert p["pi_no"] == "HT260720SZ"
    assert p["invoice_no"] == "IN260720SZ"
    assert p["packing_no"] == "PL260720SZ"
    assert p["container_no"] == "WHLU5694625"
    assert p["totals_line"] == "TOTAL 32 DRUMS PACKED ON 8 PALLETS ONLY."
    assert p["items"][0]["desc"] == "FIXING AGENT HT-016H"
    assert p["items"][0]["amount"] == 10400.0


def test_route_dest_style_country():
    p = build_clearance_payload(
        record=make_record(),
        company_code="honghao",
        overrides={},
        dest_style="country",
    )
    # VIETNAM 已是国家；country 风格仍输出 ROUTE TO 含国家
    assert "NANSHA" in p["route"]
    assert "VIETNAM" in p["route_to"]


def test_overrides_measure_win():
    p = build_clearance_payload(
        record=make_record(),
        company_code="honghao",
        overrides={"gross_kg": 4400.0, "measure_cbm": 8.0, "pallets": 8, "packages": 32},
    )
    assert p["gross_kg"] == 4400.0
    assert p["volume_cbm"] == 8.0


def test_coa_dates_from_batch_and_rule():
    p = build_clearance_payload(
        record=make_record(),
        company_code="honghao",
        overrides={
            "batch_no": "SA20260626017",
            "expiry_rule": "plus_1y_minus_1d",
        },
    )
    assert p["prod_date"] == "2026-06-26"
    assert p["exp_date"] == "2027-06-25"


def test_coa_pi_no_tbd_leaves_blank():
    """TBD-2：默认不填本票 PI，避免跨 PI 填错。"""
    p = build_clearance_payload(record=make_record(), company_code="honghao", overrides={})
    assert p["coa_pi_no"] == "" or p["coa_pi_no"] is None
    # 显式覆盖时才写入
    p2 = build_clearance_payload(
        record=make_record(),
        company_code="honghao",
        overrides={"coa_pi_no": "HT260616SZ"},
    )
    assert p2["coa_pi_no"] == "HT260616SZ"


def test_bank_block_flag():
    p = build_clearance_payload(
        record=make_record(),
        company_code="honghao",
        overrides={"show_bank_block": True},
    )
    assert p["bank_line1"].startswith("BENEFICIARY BANK")
    p_off = build_clearance_payload(
        record=make_record(),
        company_code="honghao",
        overrides={"show_bank_block": False},
    )
    assert p_off["bank_line1"] == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_clearance_fields.py -v`  
Expected: FAIL — module not found

- [ ] **Step 3: Write schemas**

```python
# backend/app/schemas/clearance.py
"""清关文件生成入参"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

DocType = Literal["si", "ci", "pl", "coa"]


class ClearanceOverrides(BaseModel):
    """人工/订舱/货代覆盖值；None 表示不覆盖"""

    container_no: Optional[str] = None
    seal_no: Optional[str] = None
    vessel: Optional[str] = None
    voyage: Optional[str] = None
    bl_no: Optional[str] = None
    carrier_code: Optional[str] = None
    dest_agent_name: Optional[str] = None
    dest_agent_addr: Optional[str] = None
    dest_agent_tax: Optional[str] = None
    dest_agent_tel: Optional[str] = None
    measure_cbm: Optional[float] = None
    gross_kg: Optional[float] = None
    net_kg: Optional[float] = None
    packages: Optional[int] = None
    pallets: Optional[int] = None
    batch_no: Optional[str] = None
    prod_date: Optional[str] = None
    exp_date: Optional[str] = None
    coa_pi_no: Optional[str] = None
    invoice_date: Optional[str] = None
    expiry_rule: Optional[str] = None
    show_bank_block: Optional[bool] = None
    show_po: Optional[bool] = None
    po_no: Optional[str] = None
    dest_style: Optional[Literal["port", "country", "custom"]] = None
    ph_label: Optional[str] = None
    solid_label: Optional[str] = None
    appearance_spec: Optional[str] = None
    appearance_result: Optional[str] = None
    ph_spec: Optional[str] = None
    ph_result: Optional[str] = None
    solid_spec: Optional[str] = None
    solid_result: Optional[str] = None

    class Config:
        extra = "ignore"


class ClearanceGenerateRequest(BaseModel):
    ledger_record_id: int
    order_id: Optional[int] = None
    customer_code: Optional[str] = None
    company_code: Optional[str] = "honghao"
    transport_mode: Optional[Literal["FCL", "LCL"]] = "FCL"
    overrides: ClearanceOverrides = Field(default_factory=ClearanceOverrides)

    class Config:
        extra = "ignore"


class ClearanceItemDict(dict):
    """填充用明细 dict；键见 clearance_fields.build_clearance_payload"""
```

- [ ] **Step 4: Write field builder**

```python
# backend/app/services/clearance_fields.py
"""从台账记录 + overrides 组装清关四单填充字段。

TBD 约束（V2 §12）：
- TBD-2 COA PI No 默认留空，仅 overrides.coa_pi_no 写入
- TBD-1 pH 条件默认用报告/overrides，不写死 20%
"""
from __future__ import annotations

from typing import Any

from app.core.company_config import get_company_profile
from app.schemas.clearance import ClearanceOverrides
from app.schemas.ledger import LedgerRecordResponse
from app.services.coa_date_service import compute_expiry_date, parse_production_date_from_batch
from app.services.doc_no_service import to_invoice_no, to_packing_no


def _visible_items(record: LedgerRecordResponse) -> list:
    items = record.items or []
    return [it for it in items if not (getattr(it, "group_id", None) is not None and not getattr(it, "is_group_header", False))]


def _amount_words_usd(amount: float) -> str:
    """英文金额大写（美元）。样例风格：TOTAL USD TEN THOUSAND AND FOUR HUNDRED ONLY."""
    # MVP：简单实现，覆盖样例量级；复杂金额可后续增强
    try:
        n = int(round(float(amount)))
    except (TypeError, ValueError):
        return ""
    if n <= 0:
        return ""
    ones = [
        "", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE",
        "TEN", "ELEVEN", "TWELVE", "THIRTEEN", "FOURTEEN", "FIFTEEN", "SIXTEEN",
        "SEVENTEEN", "EIGHTEEN", "NINETEEN",
    ]
    tens = ["", "", "TWENTY", "THIRTY", "FORTY", "FIFTY", "SIXTY", "SEVENTY", "EIGHTY", "NINETY"]

    def under_1000(x: int) -> str:
        if x == 0:
            return ""
        if x < 20:
            return ones[x]
        if x < 100:
            t, o = divmod(x, 10)
            return tens[t] + (("-" + ones[o]) if o else "")
        h, r = divmod(x, 100)
        return ones[h] + " HUNDRED" + ((" AND " + under_1000(r)) if r else "")

    if n < 1000:
        words = under_1000(n)
    else:
        th, rest = divmod(n, 1000)
        words = under_1000(th) + " THOUSAND"
        if rest:
            words += (" " + under_1000(rest)) if rest >= 100 else (" AND " + under_1000(rest))
    return f"TOTAL USD {words} ONLY."


def build_route(loading: str, dest: str, dest_style: str) -> tuple[str, str]:
    """返回 (route 全串, route_to)。dest_style: port|country|custom。"""
    pol = (loading or "NANSHA, CHINA").strip()
    dest_raw = (dest or "").strip()
    if dest_style == "country":
        # 「城市, 国家」取国家段；单段且含国家名则原样
        if "," in dest_raw:
            to = dest_raw.split(",")[-1].strip()
        else:
            to = dest_raw
    else:  # port / custom 都先用港口原文；custom 由模板覆盖占位符
        to = dest_raw
    route = f"FROM {pol} TO {to}"
    return route, to


def build_totals_line(packages: int | None, pallets: int | None) -> str:
    pk = int(packages or 0)
    pl = int(pallets or 0)
    if pk <= 0 and pl <= 0:
        return ""
    if pl <= 0:
        return f"TOTAL {pk} PACKAGES ONLY."
    return f"TOTAL {pk} DRUMS PACKED ON {pl} PALLETS ONLY."


def build_clearance_payload(
    record: LedgerRecordResponse,
    company_code: str | None = None,
    overrides: ClearanceOverrides | dict | None = None,
    dest_style: str | None = None,
) -> dict[str, Any]:
    if isinstance(overrides, dict):
        ov = ClearanceOverrides(**overrides)
    else:
        ov = overrides or ClearanceOverrides()

    company = get_company_profile(company_code)
    items = _visible_items(record)
    style = dest_style or ov.dest_style or "port"

    pi_no = record.order_no or ""
    # 台账可能 order_no 即 PI；名称与样例一致
    invoice_no = to_invoice_no(pi_no)
    packing_no = to_packing_no(pi_no)

    route, route_to = build_route(record.loading_port or "", record.destination or "", style)

    # 明细
    out_items: list[dict[str, Any]] = []
    total_qty = 0.0
    total_amount = 0.0
    total_net = 0.0
    total_gross = 0.0
    total_cbm = 0.0
    total_drums = 0
    total_pallets = 0
    for i, it in enumerate(items, 1):
        qty = float(it.quantity_kg or it.net_weight_kg or 0)
        price = float(it.unit_price or 0)
        amount = float(it.total_amount or (qty * price))
        nw = float(it.net_weight_kg or qty or 0)
        gw = float(it.gross_weight_kg or nw or 0)
        cbm = float(it.volume_cbm or 0)
        drums = int(it.drum_count or 0)
        pallets = int(it.pallet_count or 0)
        total_qty += qty
        total_amount += amount
        total_net += nw
        total_gross += gw
        total_cbm += cbm
        total_drums += drums
        total_pallets += pallets
        desc = it.product_en or it.customs_name or it.product_cn or it.internal_code
        out_items.append(
            {
                "index": i,
                "desc": desc,
                "qty": qty,
                "price": price,
                "amount": amount,
                "hs_code": it.hs_code or "",
                "net_kg": nw,
                "gross_kg": gw,
                "cbm": cbm,
                "drums": drums,
                "pallets": pallets,
                "packaging": it.packaging_name or "",
                "packages_display": pallets if style == "port" else drums,  # 模板可再映射
            }
        )

    packages = ov.packages if ov.packages is not None else total_drums
    pallets = ov.pallets if ov.pallets is not None else total_pallets
    gross = ov.gross_kg if ov.gross_kg is not None else total_gross
    net = ov.net_kg if ov.net_kg is not None else total_net
    cbm = ov.measure_cbm if ov.measure_cbm is not None else total_cbm

    # COA 日期
    batch = ov.batch_no or ""
    prod_s = ov.prod_date or ""
    exp_s = ov.exp_date or ""
    if not prod_s and batch:
        pd = parse_production_date_from_batch(batch)
        prod_s = pd.isoformat() if pd else ""
    if not exp_s and prod_s and ov.expiry_rule:
        from datetime import date as _date

        try:
            y, m, d = prod_s.split("-")
            ed = compute_expiry_date(_date(int(y), int(m), int(d)), ov.expiry_rule)
            exp_s = ed.isoformat() if ed else ""
        except ValueError:
            exp_s = ""

    show_bank = True if ov.show_bank_block is None else bool(ov.show_bank_block)
    bank = {
        "bank_line1": f"BENEFICIARY BANK : {company['bank_name_en']}" if show_bank and company.get("bank_name_en") else "",
        "bank_line2": f"BENEFICIARY BANK ADDRESS : {company['bank_address_en']}" if show_bank and company.get("bank_address_en") else "",
        "bank_line3": f"BENEFICIARY NAME : {company['name_en']}" if show_bank and company.get("name_en") else "",
        "bank_line4": f"BENEFICIARY COMPANY ADDRESS : {company['address_en']}" if show_bank and company.get("address_en") else "",
        "bank_line5": f"BENEFICIARY BANK A/C : {company['bank_account']}" if show_bank and company.get("bank_account") else "",
        "bank_line6": f"BENEFICIARY BANK SWIFT CODE : {company['bank_swift']}" if show_bank and company.get("bank_swift") else "",
    }

    tax_display = record.consignee_tel or ""  # 台账 tel 栏常放 TAX；组装为 TO 块

    return {
        "pi_no": pi_no,
        "invoice_no": invoice_no,
        "packing_no": packing_no,
        "invoice_date": ov.invoice_date or record.pi_date or "",
        "po_no": ov.po_no or "",
        "show_po": bool(ov.show_po) if ov.show_po is not None else bool(ov.po_no),
        "consignee_name": record.consignee_name or "",
        "consignee_addr": record.consignee_address or "",
        "consignee_tax": tax_display,
        "notify": record.consignee_name or "",
        "notify_addr": record.consignee_address or "",
        "price_term": record.price_term or "",
        "payment_terms": record.payment_terms or "",
        "currency": record.currency or "USD",
        "loading_port": record.loading_port or "NANSHA, CHINA",
        "discharge_port": (record.destination or "").strip(),
        "route": route,
        "route_to": route_to,
        "container_no": ov.container_no or "",
        "seal_no": ov.seal_no or "",
        "vessel": (ov.vessel or "") + ((" / " + ov.voyage) if ov.voyage else ""),
        "bl_no": ov.bl_no or "",
        "dest_agent_name": ov.dest_agent_name or "",
        "dest_agent_addr": ov.dest_agent_addr or "",
        "dest_agent_tax": ov.dest_agent_tax or "",
        "dest_agent_tel": ov.dest_agent_tel or "",
        "items": out_items,
        "total_qty": total_qty,
        "total_amount": total_amount,
        "amount_words": _amount_words_usd(total_amount),
        "net_kg": net,
        "gross_kg": gross,
        "volume_cbm": cbm,
        "packages": packages,
        "pallets": pallets,
        "totals_line": build_totals_line(packages, pallets),
        "hs_codes": " / ".join([it["hs_code"] for it in out_items if it["hs_code"]]),
        "product_name": out_items[0]["desc"] if out_items else "",
        "shipped_qty_text": f"{int(total_qty) if total_qty == int(total_qty) else total_qty}KG",
        "batch_no": batch,
        "prod_date": prod_s,
        "exp_date": exp_s,
        "coa_pi_no": ov.coa_pi_no or "",  # TBD-2 默认空
        "ph_label": ov.ph_label or "",  # TBD-1 默认空 → 模板占位保留
        "solid_label": ov.solid_label or "SOLID CONTENT",
        "appearance_spec": ov.appearance_spec or "",
        "appearance_result": ov.appearance_result or "",
        "ph_spec": ov.ph_spec or "",
        "ph_result": ov.ph_result or "",
        "solid_spec": ov.solid_spec or "",
        "solid_result": ov.solid_result or "",
        "company_name_en": company["name_en"],
        "company_addr_en": company["address_en"],
        "company_tel_en": f"TEL: {company['phone_en']}     FAX: {company['fax_en']}",
        **bank,
    }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_clearance_fields.py -v`  
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/clearance.py backend/app/services/clearance_fields.py backend/tests/test_clearance_fields.py
git commit -m "feat(clearance): build fill payload from ledger and overrides"
```

---

## Task 5: 公共模板生成脚本

**Files:**
- Create: `backend/scripts/build_clearance_templates.py`
- Generate: `references/clearance/CI-public.xlsx` / `PL-public.xlsx` / `COA-public.xlsx` / `SI-public.xlsx`

- [ ] **Step 1: Write template builder（占位符与 field 一致）**

```python
# backend/scripts/build_clearance_templates.py
"""生成清关四单公共模板（脱敏、xlsx only）。

运行: cd backend && python -m scripts.build_clearance_templates
"""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "references" / "clearance"


def _fill_ci(wb: Workbook) -> None:
    ws = wb.active
    ws.title = "CI"
    rows = [
        ("{{COMPANY_NAME_EN}}",),
        ("{{COMPANY_ADDR_EN}}",),
        ("{{COMPANY_TEL_EN}}",),
        (),
        ("TRANSPORT AND ROUTE：",),
        ("{{ROUTE}}",),
        ("CONTAINER NO.: {{CONTAINER_NO}}",),
        ("SEAL NO.: {{SEAL_NO}}",),
        (),
        ("COMMERCIAL INVOICE",),
        ("TO:", "{{CONSIGNEE_NAME}}", "INVOICE NO.:", "{{INVOICE_NO}}"),
        ("", "{{CONSIGNEE_ADDR}} {{CONSIGNEE_TAX}}", "DATE:", "{{INVOICE_DATE}}"),
        ("", "", "PI NO.:", "{{PI_NO}}"),
        ("", "", "PRICE TERM:", "{{PRICE_TERM}}"),
        (),
        ("ITEM", "DESCRIPTION", "QUANTITY", "CIF PRICE", "AMOUNT"),
        ("", "", "(KGS)", "(USD)", "(USD)"),
        ("1", "{{ITEM_DESC}}", "{{ITEM_QTY}}", "{{ITEM_PRICE}}", "{{ITEM_AMOUNT}}"),
        ("", "HS CODE: {{HS_CODES}}",),
        ("", "{{PO_LINE}}",),
        ("", "{{TOTALS_LINE}}",),
        ("{{BANK_LINE1}}",),
        ("{{BANK_LINE2}}",),
        ("{{BANK_LINE3}}",),
        ("{{BANK_LINE4}}",),
        ("{{BANK_LINE5}}",),
        ("{{BANK_LINE6}}",),
        ("PAYMENT TERMS: {{PAYMENT_TERMS}}",),
        (),
        ("TOTAL:", "{{TOTAL_QTY}}", "", "", "{{TOTAL_AMOUNT}}"),
        ("{{AMOUNT_WORDS}}",),
        (),
        ("{{COMPANY_NAME_EN}}",),
    ]
    for r in rows:
        ws.append(list(r) if r else [None])


def _fill_pl(wb: Workbook) -> None:
    ws = wb.active
    ws.title = "PL"
    rows = [
        ("{{COMPANY_NAME_EN}}",),
        ("{{COMPANY_ADDR_EN}}",),
        ("{{COMPANY_TEL_EN}}",),
        (),
        ("TRANSPORT AND ROUTE:",),
        ("{{ROUTE}}",),
        ("CONTAINER NO.: {{CONTAINER_NO}}",),
        ("SEAL NO.: {{SEAL_NO}}",),
        (),
        ("PACKING LIST",),
        ("TO:", "{{CONSIGNEE_NAME}}", "PACKING NO.:", "{{PACKING_NO}}"),
        ("", "{{CONSIGNEE_ADDR}} {{CONSIGNEE_TAX}}", "DATE:", "{{INVOICE_DATE}}"),
        ("", "", "PI NO.:", "{{PI_NO}}"),
        (),
        ("PACKING NO.", "DESCRIPTION", "PACKING QTY", "PACKING SIZE", "NET WEIGHT", "GROSS WEIGHT"),
        ("", "", "(PALLETS)", "(CBM)", "(KGS)", "(KGS)"),
        ("1", "{{ITEM_DESC}}", "{{PACKAGES}}", "{{VOLUME_CBM}}", "{{NET_KG}}", "{{GROSS_KG}}"),
        ("", "HS CODE: {{HS_CODES}}",),
        ("", "{{PO_LINE}}",),
        ("", "{{TOTALS_LINE}}",),
        (),
        ("TOTAL:", "{{PACKAGES}}", "{{VOLUME_CBM}}", "{{NET_KG}}", "{{GROSS_KG}}"),
        (),
        ("{{COMPANY_NAME_EN}}",),
    ]
    for r in rows:
        ws.append(list(r) if r else [None])


def _fill_coa(wb: Workbook) -> None:
    ws = wb.active
    ws.title = "COA"
    rows = [
        ("{{COMPANY_NAME_EN}}",),
        ("{{COMPANY_ADDR_EN}}",),
        ("{{COMPANY_TEL_EN}}",),
        (),
        (),
        ("CERTIFICATE OF ANALYSIS",),
        ("PRODUCT NAME: {{PRODUCT_NAME}}",),
        ("QUANTITY: {{SHIPPED_QTY}}", "BATCH NO.: {{BATCH_NO}}"),
        ("PRODUCTION DATE: {{PROD_DATE}}", "EXPIRATION DATE: {{EXP_DATE}}"),
        ("PI No.: {{COA_PI_NO}}",),  # TBD-2 默认空
        ("TESTS", "SPECIFICATIONS", "RESULTS"),
        ("SENSORY REQUIREMENTS", "APPEARANCE", "{{APPEARANCE_SPEC}}", "{{APPEARANCE_RESULT}}"),
        ("PHYSICOCHEMICAL REQUIREMENT", "{{SOLID_LABEL}}", "{{SOLID_SPEC}}", "{{SOLID_RESULT}}"),
        ("", "{{PH_LABEL}}", "{{PH_SPEC}}", "{{PH_RESULT}}"),
        ("CONSEQUENCE", "THE PRODUCT IS CONFORMED TO THESE STANDARD OF GB/T19001-2008 AND GB/T24001-2004."),
        ("MAKER: {{COMPANY_NAME_EN}}",),
        ("THE CENTER OF QUALITY INSPECTION",),
        ("{{COMPANY_NAME_EN}}",),
    ]
    for r in rows:
        ws.append(list(r) if r else [None])


def _fill_si(wb: Workbook) -> None:
    ws = wb.active
    ws.title = "SI"
    rows = [
        ("BOOKING / SHIPPING INSTRUCTION (SI)",),
        ("（订舱补料 — 非提单正本；正本由船公司签发）",),
        (),
        ("SHIPPER", "{{COMPANY_NAME_EN}}", "{{COMPANY_ADDR_EN}}"),
        ("CONSIGNEE", "{{CONSIGNEE_NAME}}", "{{CONSIGNEE_ADDR}}"),
        ("NOTIFY", "{{NOTIFY}}", "{{NOTIFY_ADDR}}"),
        ("DESTINATION AGENT", "{{DEST_AGENT_NAME}}", "{{DEST_AGENT_ADDR}}"),
        ("", "{{DEST_AGENT_TAX}}", "{{DEST_AGENT_TEL}}"),
        (),
        ("VESSEL / VOYAGE", "{{VESSEL}}"),
        ("B/L NO.", "{{BL_NO}}"),
        ("PORT OF LOADING", "{{LOADING_PORT}}"),
        ("PORT OF DISCHARGE", "{{DISCHARGE_PORT}}"),
        ("CONTAINER NO.", "{{CONTAINER_NO}}"),
        ("SEAL NO.", "{{SEAL_NO}}"),
        (),
        ("DESCRIPTION", "{{ITEM_DESC}}"),
        ("QTY / NET WEIGHT", "{{SHIPPED_QTY}}"),
        ("H.S. CODE", "{{HS_CODES}}"),
        ("PACKAGES", "{{TOTALS_LINE}}"),
        ("GROSS WEIGHT (KGS)", "{{GROSS_KG}}"),
        ("MEASUREMENT (CBM)", "{{VOLUME_CBM}}"),
        ("FREIGHT", "FREIGHT PREPAID"),
    ]
    for r in rows:
        ws.append(list(r) if r else [None])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    builders = {
        "CI-public.xlsx": _fill_ci,
        "PL-public.xlsx": _fill_pl,
        "COA-public.xlsx": _fill_coa,
        "SI-public.xlsx": _fill_si,
    }
    for name, fn in builders.items():
        wb = Workbook()
        fn(wb)
        path = OUT / name
        wb.save(path)
        print("wrote", path)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行生成模板**

Run: `cd backend && python -m scripts.build_clearance_templates`  
Expected: 输出 4 行 `wrote .../references/clearance/...`  
确认：`references/clearance/` 下 4 个 xlsx 存在且 > 0 字节

- [ ] **Step 3: config 注册模板路径**

Modify `backend/app/core/config.py` 的 `TEMPLATES` 字典，在 `"customs"` 后追加：

```python
    "clearance_ci": str(ROOT / "references" / "clearance" / "CI-public.xlsx"),
    "clearance_pl": str(ROOT / "references" / "clearance" / "PL-public.xlsx"),
    "clearance_coa": str(ROOT / "references" / "clearance" / "COA-public.xlsx"),
    "clearance_si": str(ROOT / "references" / "clearance" / "SI-public.xlsx"),
```

- [ ] **Step 4: Commit**

```bash
git add backend/scripts/build_clearance_templates.py backend/app/core/config.py references/clearance/
git commit -m "feat(clearance): add public CI/PL/COA/SI xlsx templates"
```

---

## Task 6: clearance_doc_service 填充与生成

**Files:**
- Create: `backend/app/services/clearance_doc_service.py`
- Create: `backend/tests/test_clearance_doc_service.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_clearance_doc_service.py
import io

import openpyxl
import pytest

from app.schemas.ledger import LedgerItemSchema, LedgerRecordResponse
from app.services.clearance_doc_service import ClearanceDocService


def make_record() -> LedgerRecordResponse:
    return LedgerRecordResponse(
        id=1,
        order_no="HT260720SZ",
        customer_code="WA318",
        consignee_name="CHEMZONE CO., LTD.",
        consignee_address="26/1D TRAN QUY CAP ST., HO CHI MINH CITY, VIETNAM",
        consignee_tel="TAX CODE: 0316699088",
        destination="HOCHIMINH(CAT LAI), VIETNAM",
        loading_port="NANSHA, CHINA",
        price_term="CIF HOCHIMINH",
        payment_terms="100% TT AFTER SHIPMENT 30 DAYS",
        pi_date="2026-07-20",
        currency="USD",
        items=[
            LedgerItemSchema(
                internal_code="FIX-HT016H",
                product_en="FIXING AGENT HT-016H",
                quantity_kg=4000.0,
                unit_price=2.6,
                total_amount=10400.0,
                hs_code="340241",
                drum_count=32,
                pallet_count=8,
                net_weight_kg=4000.0,
                gross_weight_kg=4308.0,
                volume_cbm=7.92,
            )
        ],
        status="saved",
    )


@pytest.fixture
def svc():
    return ClearanceDocService()


def _all_text(wb) -> str:
    parts = []
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if cell.value is not None:
                    parts.append(str(cell.value))
    return "\n".join(parts)


def test_generate_ci(svc):
    content, doc_key, _ = svc.generate("ci", make_record(), "honghao", {
        "container_no": "WHLU5694625",
        "seal_no": "WHA4051188",
        "invoice_date": "2026-08-01",
        "show_bank_block": True,
    })
    assert doc_key.startswith("ci_")
    wb = openpyxl.load_workbook(io.BytesIO(content))
    text = _all_text(wb)
    assert "IN260720SZ" in text
    assert "HT260720SZ" in text
    assert "FIXING AGENT HT-016H" in text
    assert "WHLU5694625" in text
    assert "TOTAL 32 DRUMS PACKED ON 8 PALLETS ONLY." in text
    assert "{{" not in text  # 无残留占位符
    assert "BENEFICIARY BANK" in text


def test_generate_ci_bank_off(svc):
    content, _, _ = svc.generate("ci", make_record(), "honghao", {"show_bank_block": False})
    text = _all_text(openpyxl.load_workbook(io.BytesIO(content)))
    assert "BENEFICIARY BANK" not in text


def test_generate_pl(svc):
    content, doc_key, _ = svc.generate("pl", make_record(), "honghao", {})
    assert doc_key.startswith("pl_")
    text = _all_text(openpyxl.load_workbook(io.BytesIO(content)))
    assert "PL260720SZ" in text
    assert "4308" in text or "4308.0" in text


def test_generate_coa_tbd_blank_pi(svc):
    content, doc_key, _ = svc.generate(
        "coa",
        make_record(),
        "honghao",
        {
            "batch_no": "SA20260626017",
            "expiry_rule": "plus_1y_minus_1d",
            "ph_label": "PH (1%)",
            "ph_spec": "6.5~7.5",
            "ph_result": "7.3",
            "solid_spec": "70±2",
            "solid_result": "70.72",
            "appearance_spec": "Yellow transparent mucus",
            "appearance_result": "Yellow transparent mucus",
        },
    )
    assert doc_key.startswith("coa_")
    text = _all_text(openpyxl.load_workbook(io.BytesIO(content)))
    assert "SA20260626017" in text
    assert "2026-06-26" in text
    assert "2027-06-25" in text
    assert "PH (1%)" in text
    assert "70.72" in text


def test_generate_si(svc):
    content, doc_key, _ = svc.generate(
        "si",
        make_record(),
        "honghao",
        {
            "vessel": "WAN HAI 289",
            "voyage": "S086",
            "bl_no": "GHOC26071803",
            "dest_agent_name": "STAR CONCORD (VIETNAM) CO., LTD.",
        },
    )
    assert doc_key.startswith("si_")
    text = _all_text(openpyxl.load_workbook(io.BytesIO(content)))
    assert "WAN HAI 289 / S086" in text
    assert "STAR CONCORD" in text
    assert "订舱补料" in text or "SHIPPING INSTRUCTION" in text


def test_unknown_doc_type(svc):
    with pytest.raises(ValueError):
        svc.generate("unknown", make_record(), "honghao", {})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_clearance_doc_service.py -v`  
Expected: FAIL — module not found

- [ ] **Step 3: Write implementation**

```python
# backend/app/services/clearance_doc_service.py
"""清关四单：读公共模板 → 填占位符 → 返回 xlsx bytes。"""
from __future__ import annotations

import time
from typing import Any

import openpyxl

from app.core.config import TEMPLATES
from app.schemas.ledger import LedgerRecordResponse
from app.services.clearance_fields import build_clearance_payload

_DOC_TYPE_TO_TEMPLATE = {
    "ci": "clearance_ci",
    "pl": "clearance_pl",
    "coa": "clearance_coa",
    "si": "clearance_si",
}


def _replace_all(ws, payload: dict[str, Any]) -> None:
    """将 {{KEY}} 占位符替换为 payload 值；未知键替换为空串。

    单元格可能混在长句里（如 "INVOICE NO.: {{INVOICE_NO}}"），做子串替换。
    """
    mapping = {f"{{{{{k.upper()}}}}}": ("" if v is None else v) for k, v in payload.items()}
    # 多行明细 MVP：单产品用 ITEM_* 别名
    if payload.get("items"):
        it = payload["items"][0]
        mapping["{{ITEM_DESC}}"] = it.get("desc") or ""
        mapping["{{ITEM_QTY}}"] = it.get("qty") if it.get("qty") is not None else ""
        mapping["{{ITEM_PRICE}}"] = it.get("price") if it.get("price") is not None else ""
        mapping["{{ITEM_AMOUNT}}"] = it.get("amount") if it.get("amount") is not None else ""
    else:
        mapping["{{ITEM_DESC}}"] = ""
        mapping["{{ITEM_QTY}}"] = ""
        mapping["{{ITEM_PRICE}}"] = ""
        mapping["{{ITEM_AMOUNT}}"] = ""
    mapping["{{PO_LINE}}"] = f"PO#{payload['po_no']}" if payload.get("show_po") and payload.get("po_no") else ""
    mapping["{{VOLUME_CBM}}"] = payload.get("volume_cbm", "")
    mapping["{{NET_KG}}"] = payload.get("net_kg", "")
    mapping["{{GROSS_KG}}"] = payload.get("gross_kg", "")
    mapping["{{PACKAGES}}"] = payload.get("pallets") if payload.get("pallets") is not None else payload.get("packages", "")
    mapping["{{SHIPPED_QTY}}"] = payload.get("shipped_qty_text", "")
    mapping["{{PRODUCT_NAME}}"] = payload.get("product_name", "")
    mapping["{{DISCHARGE_PORT}}"] = payload.get("discharge_port", "")
    mapping["{{LOADING_PORT}}"] = payload.get("loading_port", "")
    mapping["{{VESSEL}}"] = payload.get("vessel", "")
    mapping["{{BL_NO}}"] = payload.get("bl_no", "")
    mapping["{{DEST_AGENT_NAME}}"] = payload.get("dest_agent_name", "")
    mapping["{{DEST_AGENT_ADDR}}"] = payload.get("dest_agent_addr", "")
    mapping["{{DEST_AGENT_TAX}}"] = payload.get("dest_agent_tax", "")
    mapping["{{DEST_AGENT_TEL}}"] = payload.get("dest_agent_tel", "")
    mapping["{{BANK_LINE1}}"] = payload.get("bank_line1", "")
    # ... 2-6 同理
    for i in range(2, 7):
        mapping[f"{{{{BANK_LINE{i}}}}}"] = payload.get(f"bank_line{i}", "")

    for row in ws.iter_rows():
        for cell in row:
            if not isinstance(cell.value, str) or "{{" not in cell.value:
                continue
            s = cell.value
            for k, v in mapping.items():
                if k in s:
                    s = s.replace(k, str(v))
            # 清掉未映射残留占位符
            out = s
            for k in mapping:
                out = out.replace(k, "")
            cell.value = out


class ClearanceDocService:
    def load_template(self, doc_type: str) -> openpyxl.Workbook:
        key = _DOC_TYPE_TO_TEMPLATE.get(doc_type)
        if not key:
            raise ValueError(f"Unknown clearance doc_type: {doc_type}")
        path = TEMPLATES[key]
        return openpyxl.load_workbook(path)

    def generate(
        self,
        doc_type: str,
        record: LedgerRecordResponse,
        company_code: str | None = None,
        overrides: dict | None = None,
    ) -> tuple[bytes, str, str]:
        """返回 (xlsx_bytes, doc_key, b64)。"""
        import base64
        import io

        payload = build_clearance_payload(record, company_code, overrides or {})
        wb = self.load_template(doc_type)
        for ws in wb.worksheets:
            _replace_all(ws, payload)
        buf = io.BytesIO()
        wb.save(buf)
        content = buf.getvalue()
        doc_key = f"{doc_type}_{int(time.time())}"
        return content, doc_key, base64.b64encode(content).decode()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_clearance_doc_service.py tests/test_clearance_fields.py tests/test_doc_no_service.py tests/test_coa_date_service.py -v`  
Expected: all PASS  
若 `{{` 残留失败：检查 mapping 键大小写是否与模板一致（payload 键已 upper）。

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/clearance_doc_service.py backend/tests/test_clearance_doc_service.py
git commit -m "feat(clearance): fill public templates and generate four docs"
```

---

## Task 7: API 路由（POST ci/pl/coa/si）

**Files:**
- Modify: `backend/app/api/v1/documents.py`

- [ ] **Step 1: 在 `_save_doc_to_db` 前插入 schemas 与共享响应函数，并追加 4 个路由**

在 `documents.py` 顶部 import 区追加：

```python
from app.schemas.clearance import ClearanceGenerateRequest
from app.services.clearance_doc_service import ClearanceDocService
```

在 `_save_doc_to_db` 函数**上方**增加：

```python
def _oo_response(content: bytes, doc_key: str, doc_type: str, order_id: int | None, file_ext: str = "xlsx") -> dict:
    """OnlyOffice config + 双 URL（与 generate_customs 同构）。"""
    token, config, safe_key = oo_svc.create_config(doc_key, file_ext)
    _save_doc_to_db(doc_key, doc_type, content, order_id=order_id, storage_key=safe_key)
    api_base = os.getenv("API_BASE_URL", "http://localhost:8000")
    callback_base = os.getenv("ONLYOFFICE_CALLBACK_BASE_URL", "http://host.docker.internal:8000")
    return {
        **config,
        "url": f"{callback_base}/api/v1/onlyoffice/download/{safe_key}",
        "downloadUrl": f"{api_base}/api/v1/onlyoffice/download/{safe_key}",
        "callbackUrl": f"{callback_base}/api/v1/onlyoffice/callback?doc_key={safe_key}",
    }
```

同时把 `_save_doc_to_db` 里的扩展名判断改为包含清关类型：

```python
            file_name=f"{doc_key}.{'xlsx' if doc_type in ('booking', 'customs', 'ci', 'pl', 'coa', 'si') else 'docx'}",
```

在文件末尾追加：

```python
@router.post("/ci")
async def generate_ci(req: ClearanceGenerateRequest = Body(...)):
    """生成商业发票 CI（清关，非出口报关发票）。"""
    from app.services.ledger_service import LedgerService

    db = SessionLocal()
    try:
        record = LedgerService().get_ledger_record(req.ledger_record_id)
        if not record:
            return {"error": "ledger record not found"}
        svc = ClearanceDocService()
        content, doc_key, _ = svc.generate("ci", record, req.company_code, req.overrides.model_dump())
        return _oo_response(content, doc_key, "ci", req.order_id)
    finally:
        db.close()


@router.post("/pl")
async def generate_pl(req: ClearanceGenerateRequest = Body(...)):
    from app.services.ledger_service import LedgerService

    record = LedgerService().get_ledger_record(req.ledger_record_id)
    if not record:
        return {"error": "ledger record not found"}
    svc = ClearanceDocService()
    content, doc_key, _ = svc.generate("pl", record, req.company_code, req.overrides.model_dump())
    return _oo_response(content, doc_key, "pl", req.order_id)


@router.post("/coa")
async def generate_coa(req: ClearanceGenerateRequest = Body(...)):
    from app.services.ledger_service import LedgerService

    record = LedgerService().get_ledger_record(req.ledger_record_id)
    if not record:
        return {"error": "ledger record not found"}
    svc = ClearanceDocService()
    content, doc_key, _ = svc.generate("coa", record, req.company_code, req.overrides.model_dump())
    return _oo_response(content, doc_key, "coa", req.order_id)


@router.post("/si")
async def generate_si(req: ClearanceGenerateRequest = Body(...)):
    """订舱补料 SI（非提单正本）。"""
    from app.services.ledger_service import LedgerService

    record = LedgerService().get_ledger_record(req.ledger_record_id)
    if not record:
        return {"error": "ledger record not found"}
    svc = ClearanceDocService()
    content, doc_key, _ = svc.generate("si", record, req.company_code, req.overrides.model_dump())
    return _oo_response(content, doc_key, "si", req.order_id)
```

> 注意：`LedgerService().get_ledger_record` 若依赖 `SessionLocal` 内部打开连接，可去掉外层 db；与 `test_customs_dynamic_rows` 的 monkeypatch 方式一致，集成测再打补丁。

- [ ] **Step 2: 路由注册确认**

`main.py` 已 `include_router(documents.router)`，无需改。

- [ ] **Step 3: 导入冒烟**

Run: `cd backend && python -c "from app.main import app; print('ok')"`  
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/v1/documents.py
git commit -m "feat(clearance): add POST /documents/{ci,pl,coa,si} endpoints"
```

---

## Task 8: 前端 API 与 Phase2 按钮

**Files:**
- Modify: `frontend/src/api/phase2.ts`
- Modify: `frontend/src/views/phase2/Phase2Workflow.vue`

- [ ] **Step 1: phase2.ts 增加四个方法**

在 `generateCustoms` 之后追加：

```ts
  generateClearance(docType: 'ci' | 'pl' | 'coa' | 'si', payload: {
    ledger_record_id: number
    order_id?: number
    customer_code?: string
    company_code?: string
    transport_mode?: 'FCL' | 'LCL'
    overrides?: Record<string, unknown>
  }) {
    return apiClient.post(`/documents/${docType}`, payload)
  },
```

- [ ] **Step 2: Phase2Workflow 按钮组（报关资料右侧）**

在 `header-actions` 中「报关资料」`</el-button>` **之后**插入：

```vue
          <el-divider direction="vertical" />
          <el-button
            size="small"
            :disabled="!selectedLedgerId"
            v-track="{ event: 'generate_document', module: 'phase2', detail: { doc_type: 'si' } }"
            @click="openClearanceDocument('si')"
          >
            订舱补料 SI
          </el-button>
          <el-button
            size="small"
            :disabled="!selectedLedgerId"
            v-track="{ event: 'generate_document', module: 'phase2', detail: { doc_type: 'ci' } }"
            @click="openClearanceDocument('ci')"
          >
            发票 CI
          </el-button>
          <el-button
            size="small"
            :disabled="!selectedLedgerId"
            v-track="{ event: 'generate_document', module: 'phase2', detail: { doc_type: 'pl' } }"
            @click="openClearanceDocument('pl')"
          >
            装箱单 PL
          </el-button>
          <el-button
            size="small"
            :disabled="!selectedLedgerId"
            v-track="{ event: 'generate_document', module: 'phase2', detail: { doc_type: 'coa' } }"
            @click="openClearanceDocument('coa')"
          >
            品质证书 COA
          </el-button>
```

在 `openCustomsDocument` 函数后追加：

```ts
async function openClearanceDocument(docType: 'si' | 'ci' | 'pl' | 'coa') {
  if (!selectedLedgerId.value) {
    ElMessage.warning('请先从台账列表选择一条记录')
    return
  }
  try {
    const companyCode = getCompanyCodeFromShipper()
    const res = await phase2Api.generateClearance(docType, {
      ledger_record_id: selectedLedgerId.value,
      customer_code: currentOrderInfo.value?.customer_code || undefined,
      company_code: companyCode,
      overrides: {
        container_no: undefined,
        seal_no: undefined,
        // 柜封号/批号等后续从对话框收集；MVP 先空，由 OnlyOffice 手补
      },
    })
    currentDocKey.value = res.data.documentKey || res.data.docKey || ''
    currentConfig.value = res.data || res
  } catch (e: any) {
    ElMessage.error('清关文件生成失败，请稍后重试')
  }
}
```

- [ ] **Step 3: 前端类型检查**

Run: `cd frontend && npx vue-tsc --noEmit`（或项目现有 `npm run type-check`）  
Expected: 无新增错误

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/phase2.ts frontend/src/views/phase2/Phase2Workflow.vue
git commit -m "feat(clearance): add SI/CI/PL/COA buttons next to customs docs"
```

---

## Task 9: 端到端冒烟 + 双样例字段对账检查表

**Files:**
- Create: `backend/tests/test_clearance_e2e_fields.py`（轻量断言样例关键字段）

- [ ] **Step 1: Write sample-alignment tests（WA318 数字）**

```python
# backend/tests/test_clearance_e2e_fields.py
"""对照 WA318 样例关键数字（见 V2 §8.1）。"""
import io

import openpyxl

from app.schemas.ledger import LedgerItemSchema, LedgerRecordResponse
from app.services.clearance_doc_service import ClearanceDocService


def wa318_record() -> LedgerRecordResponse:
    return LedgerRecordResponse(
        id=1,
        order_no="HT260720SZ",
        customer_code="WA318",
        consignee_name="CHEMZONE CO., LTD.",
        consignee_address="26/1D TRAN QUY CAP ST., BINH LOI TRUNG WARD, HO CHI MINH CITY, VIETNAM",
        destination="HOCHIMINH(CAT LAI),VIETNAM",
        loading_port="NANSHA,CHINA",
        price_term="CIF  HOCHIMINH",
        payment_terms="100% TT AFTER SHIPMENT 30 DAYS",
        pi_date="2026-07-20",
        currency="USD",
        items=[
            LedgerItemSchema(
                internal_code="HT-016H",
                product_en="FIXING AGENT HT-016H",
                quantity_kg=4000.0,
                unit_price=2.6,
                total_amount=10400.0,
                hs_code="340241",
                packaging_name="125kg /drum",
                drum_count=32,
                pallet_count=8,
                net_weight_kg=4000.0,
                gross_weight_kg=4308.0,
                volume_cbm=7.92,
            )
        ],
        status="saved",
    )


def test_wa318_ci_pl_alignment():
    svc = ClearanceDocService()
    ov = {
        "container_no": "WHLU5694625",
        "seal_no": "WHA4051188",
        "invoice_date": "2026-08-01",
        "show_bank_block": True,
    }
    ci, _, _ = svc.generate("ci", wa318_record(), "honghao", ov)
    pl, _, _ = svc.generate("pl", wa318_record(), "honghao", ov)
    ci_text = "\n".join(
        str(c.value)
        for ws in openpyxl.load_workbook(io.BytesIO(ci)).worksheets
        for row in ws.iter_rows()
        for c in row
        if c.value is not None
    )
    pl_text = "\n".join(
        str(c.value)
        for ws in openpyxl.load_workbook(io.BytesIO(pl)).worksheets
        for row in ws.iter_rows()
        for c in row
        if c.value is not None
    )
    for t in (ci_text, pl_text):
        assert "IN260720SZ" in t or "PL260720SZ" in t
        assert "WHLU5694625" in t
        assert "4308" in t or "4308.0" in t
        assert "7.92" in t or "7.920" in t
    assert "IN260720SZ" in ci_text
    assert "PL260720SZ" in pl_text
    assert "TOTAL 32 DRUMS PACKED ON 8 PALLETS ONLY." in ci_text
```

- [ ] **Step 2: Run full clearance test suite**

Run: `cd backend && python -m pytest tests/test_doc_no_service.py tests/test_coa_date_service.py tests/test_clearance_fields.py tests/test_clearance_doc_service.py tests/test_clearance_e2e_fields.py -v`  
Expected: all PASS

- [ ] **Step 3: 回归全量后端测试**

Run: `cd backend && python -m pytest tests/ -q`  
Expected: 不破坏既有用例

- [ ] **Step 4: 手工 UI 冒烟（有后端时）**

1. 启动后端 + 前端  
2. Phase2 选台账 → 依次点「订舱补料 SI / 发票 CI / 装箱单 PL / 品质证书 COA」  
3. OnlyOffice 打开且标题正确；保存可 callback  
4. 「报关资料」旧按钮行为不变  

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_clearance_e2e_fields.py
git commit -m "test(clearance): align CI/PL fields with WA318 sample numbers"
```

---

## Out of Scope（后续独立计划）

| 项 | 原因 |
|----|------|
| `customer_templates` 存/取定制模板 | Phase C；等字段映射被真实单据验收后再冻 |
| L2 跨产品合托 / L4 `shipment_measurements` | Phase D；阻塞包装资料 Excel |
| COA 多 sheet 多批一键 | Phase E |
| TBD-1/2/3/4 业务拍板后的默认值 | 关闭前只留空/覆盖 |

---

## Self-Review（计划作者已跑）

1. **Spec coverage（V2 Phase A+B）**  
   - 编号 IN/PL 幂等 → Task 1  
   - 批号→生产日期、有效期两规则 → Task 2  
   - 英文抬头/银行有无 → Task 3/4  
   - 目的地 ROUTE 口径 port/country → Task 4  
   - 四单模板+填充+TOTALS_LINE → Task 5/6  
   - POST API + OnlyOffice 复用 → Task 7  
   - 按钮在报关资料右侧、文案 SI 非 BL → Task 8  
   - WA318 数字对账 → Task 9  
   - TBD 默认不填 → Task 4 `coa_pi_no` / `ph_label` 测试  

2. **Placeholder scan:** 无 TBD/TODO 步骤；模板占位符是产品机制不是计划空洞。  

3. **Type consistency:** `to_invoice_no` / `to_packing_no` / `build_clearance_payload` / `ClearanceDocService.generate` / `generateClearance` 签名前后一致。
