# FR-4.x 包装计算模块实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建包装计算模块，支持海运/空运/陆运三模计算，实时测算桶数、卡板数、体积、毛重及集装箱推荐。

**Architecture:** 后端提供统一的计算 API，前端三模式切换（海运主体、空运精简、陆运基础）。海运计算结果包含文本装配方案 + 结构化指标卡片 + 集装箱推荐；空运展示计费重量对比面板；陆运展示总重阈值警告。

**Tech Stack:** FastAPI + SQLAlchemy + SQLite（后端计算），Vue 3 + Element Plus + TypeScript（前端）。

---

## 文件结构

```
backend/
├── app/
│   ├── models/
│   │   └── order.py          # 现有：PackagingType, Pallet
│   ├── services/
│   │   └── calculation_service.py  # NEW：包装计算服务（共享计算逻辑）
│   └── api/v1/
│       └── packages.py       # NEW：包装计算 API 路由
frontend/
├── src/
│   ├── api/
│   │   └── packages.ts       # NEW：包装计算 API 客户端
│   └── views/
│       └── phase1/
│           └── PackageCalc.vue   # NEW：包装计算主页
└── components/
    └── phase1/
        ├── PackagingTypeSelect.vue  # NEW：包装类型下拉（含推荐气泡）
        ├── PalletSpecSelect.vue     # NEW：卡板规格选择
        ├── PalletQtyInput.vue       # NEW：单板数量输入
        ├── TransportModeSwitcher.vue # NEW：运输模式切换器
        ├── AirFreightPanel.vue      # NEW：空运计费重量面板
        └── LandTransportPanel.vue   # NEW：陆运总重警告面板
```

---

## 任务索引

| ID | 轨道 | 描述 |
|----|------|------|
| BM-1 | Backend | calculation_service.py — 核心计算逻辑（桶数/卡板数/体积/重量/20GP判定） |
| BM-2 | Backend | API 路由 — GET /api/v1/packages/calculate + GET /api/v1/packages/types + GET /api/v1/packages/recommend |
| FE-1 | Frontend | packages.ts API 客户端 + TypeScript 接口 |
| FE-2 | Frontend | PackageCalc.vue 主页面（运输模式切换 + 输入面板 + 结果展示） |
| FE-3 | Frontend | PackagingTypeSelect.vue — 包装类型下拉 + 知识库推荐气泡 |
| FE-4 | Frontend | AirFreightPanel.vue + LandTransportPanel.vue — 空运/陆运专用面板 |

---

## Track 1: Backend（BM-1 → BM-2）

### Task BM-1: calculation_service.py — 核心计算逻辑

**Files:**
- Create: `backend/app/services/calculation_service.py`
- Test: `backend/tests/test_calculation_service.py`

---

- [ ] **Step 1: 编写测试**

Create `backend/tests/test_calculation_service.py`:

```python
import pytest
import math
from app.services.calculation_service import (
    CalculationService,
    FLOAT_TOLERANCE,
    CONTAINER_LIMITS,
    AIR_VOLUME_FACTORS,
)


class TestSeaCalculation:
    """海运计算测试"""

    def test_drum_count_ceiling(self):
        """桶数 = ceil(order_qty / net_kg)"""
        service = CalculationService()
        # 1500kg / 125kg净重 = 12 → 向上取整
        assert service.calculate_drums(1500, 125) == 12
        # 1501kg / 125kg净重 = 12.008 → 向上取整 → 13
        assert service.calculate_drums(1501, 125) == 13

    def test_pallet_count_ceiling(self):
        """卡板数 = ceil(drums / capacity)"""
        service = CalculationService()
        assert service.calculate_pallets(12, 5) == 3  # ceil(12/5) = 3
        assert service.calculate_pallets(15, 5) == 3  # ceil(15/5) = 3
        assert service.calculate_pallets(16, 5) == 4  # ceil(16/5) = 4

    def test_pallet_count_zero_when_no_pallet(self):
        """不打卡板时，卡板数为 0"""
        service = CalculationService()
        assert service.calculate_pallets(12, 5, no_pallet=True) == 0

    def test_total_volume_with_pallets(self):
        """总体积 = drums*cbm + pallets*pallet_cbm"""
        service = CalculationService()
        # 12 drums × 0.21 CBM + 3 pallets × 0.20 CBM
        volume = service.calculate_volume(drums=12, cbm_per_drum=0.21, pallets=3, cbm_per_pallet=0.20)
        assert abs(volume - (12 * 0.21 + 3 * 0.20)) < FLOAT_TOLERANCE

    def test_total_volume_no_pallet(self):
        """不打卡板时，总体积仅含桶身"""
        service = CalculationService()
        volume = service.calculate_volume(drums=12, cbm_per_drum=0.21, pallets=0, cbm_per_pallet=0.20)
        assert abs(volume - 12 * 0.21) < FLOAT_TOLERANCE

    def test_total_weight_with_pallets(self):
        """总毛重 = drums*gross + pallets*pallet_weight"""
        service = CalculationService()
        weight = service.calculate_gross_weight(
            drums=12, gross_per_drum=131.0,
            pallets=3, pallet_weight=27.0
        )
        assert abs(weight - (12 * 131.0 + 3 * 27.0)) < FLOAT_TOLERANCE

    def test_judge_20gp_ok(self):
        """≤28 CBM 且 ≤21000kg → 推荐 20GP"""
        service = CalculationService()
        result = service.judge_container(total_cbm=25, total_weight_kg=20000)
        assert result["recommended"] == "20GP"
        assert result["status"] == "ok"

    def test_judge_40gp_upgrade(self):
        """超出 20GP 但满足 40GP → 建议升级 40GP"""
        service = CalculationService()
        result = service.judge_container(total_cbm=30, total_weight_kg=25000)
        assert result["recommended"] == "40GP"
        assert result["status"] == "upgrade"

    def test_judge_40hq(self):
        """超出 40GP 但满足 40HQ → 建议升级 40HQ"""
        service = CalculationService()
        result = service.judge_container(total_cbm=60, total_weight_kg=26000)
        assert result["recommended"] == "40HQ"
        assert result["status"] == "upgrade"

    def test_judge_over_limit(self):
        """超出 40HQ 上限 → 警告"""
        service = CalculationService()
        result = service.judge_container(total_cbm=70, total_weight_kg=28000)
        assert result["recommended"] == "超限"
        assert result["status"] == "over_limit"

    def test_load_rate(self):
        """装载率计算"""
        service = CalculationService()
        rate = service.calculate_load_rate(volume_cbm=25, container_cbm=28)
        assert abs(rate - (25 / 28 * 100)) < FLOAT_TOLERANCE

    def test_packing_scheme_exact(self):
        """整除：满板无余数"""
        service = CalculationService()
        scheme = service.generate_packing_scheme(
            drums=15, pallets=3, capacity_per_pallet=5, no_pallet=False
        )
        assert "满板" in scheme
        assert "尾数" not in scheme

    def test_packing_scheme_with_remainder(self):
        """有余数：最后一板未装满"""
        service = CalculationService()
        scheme = service.generate_packing_scheme(
            drums=16, pallets=4, capacity_per_pallet=5, no_pallet=False
        )
        assert "尾数" in scheme or "最后一个" in scheme

    def test_packing_scheme_no_pallet(self):
        """不打卡板：仅显示桶数"""
        service = CalculationService()
        scheme = service.generate_packing_scheme(
            drums=150, pallets=0, capacity_per_pallet=5, no_pallet=True
        )
        assert "卡板" not in scheme
        assert "桶" in scheme


class TestAirCalculation:
    """空运计算测试"""

    def test_vol_weight_167(self):
        """体积重 ×167"""
        service = CalculationService()
        vol = service.calculate_air_volume_weight(total_cbm=10, factor=167)
        assert abs(vol - 1670) < FLOAT_TOLERANCE

    def test_vol_weight_6000(self):
        """体积重 ÷6000"""
        service = CalculationService()
        vol = service.calculate_air_volume_weight(total_cbm=10, factor=6000)
        assert abs(vol - (10 * 1000000 / 6000)) < FLOAT_TOLERANCE

    def test_chargeable_weight_max(self):
        """计费重量 = max(实重, 体积重)"""
        service = CalculationService()
        chargeable = service.calculate_chargeable_weight(
            actual_weight=10000,
            vol_weight_167=8000,
            vol_weight_6000=8000
        )
        assert chargeable == 10000


class TestLandCalculation:
    """陆运计算测试"""

    def test_overweight_warning(self):
        """超过 30 吨 → 警告"""
        service = CalculationService()
        assert service.check_land_overweight(total_weight_kg=35000) is True
        assert service.check_land_overweight(total_weight_kg=25000) is False
```

---

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_calculation_service.py -v`
Expected: FAIL with "No module named 'app.services.calculation_service'"

---

- [ ] **Step 3: 编写 calculation_service.py**

Create `backend/app/services/calculation_service.py`:

```python
"""包装计算服务 — FR-4.x 包装计算模块（只读计算）"""

import math
from typing import Optional
from dataclasses import dataclass


FLOAT_TOLERANCE = 0.01  # 数值字段容差

# 集装箱阈值（体积 CBM，重量 kg）
CONTAINER_LIMITS = {
    "20GP": {"volume": 28.0, "weight": 21000.0},
    "40GP": {"volume": 56.0, "weight": 27000.0},
    "40HQ": {"volume": 67.0, "weight": 27000.0},
}

# 空运体积重系数
AIR_VOLUME_FACTORS = {
    "IATA_167": 167,      # CBM × 167
    "AIRLINE_6000": 6000, # CBM × 1000000 ÷ 6000
}


@dataclass
class ContainerResult:
    """集装箱推荐结果"""
    recommended: str  # "20GP" / "40GP" / "40HQ" / "超限"
    load_rate: float   # 装载率 %
    volume_limit: float
    weight_limit: float
    status: str  # "ok" / "upgrade" / "over_limit"


class CalculationService:
    """包装计算服务 — 海运/空运/陆运统一计算入口"""

    def __init__(self):
        pass

    # ─────────────────────────────────────────────────────────────────────────
    # 海运计算
    # ─────────────────────────────────────────────────────────────────────────

    def calculate_drums(self, quantity_kg: float, net_kg_per_drum: float) -> int:
        """
        桶数 = ceil(order_qty / net_kg_per_drum)
        向上取整，确保即使有余数也能容纳全部货物
        """
        if net_kg_per_drum <= 0 or quantity_kg <= 0:
            return 0
        return math.ceil(quantity_kg / net_kg_per_drum)

    def calculate_pallets(
        self,
        drums: int,
        capacity_per_pallet: float,
        no_pallet: bool = False,
    ) -> int:
        """
        卡板数 = ceil(drums / capacity_per_pallet)
        不打卡板时强制为 0
        """
        if no_pallet or drums == 0 or capacity_per_pallet <= 0:
            return 0
        return math.ceil(drums / capacity_per_pallet)

    def calculate_volume(
        self,
        drums: int,
        cbm_per_drum: float,
        pallets: int,
        cbm_per_pallet: float,
    ) -> float:
        """
        总体积 = drums × cbm_per_drum + pallets × cbm_per_pallet
        """
        return drums * cbm_per_drum + pallets * cbm_per_pallet

    def calculate_gross_weight(
        self,
        drums: int,
        gross_per_drum: float,
        pallets: int,
        pallet_weight: float,
    ) -> float:
        """
        总毛重 = drums × gross_per_drum + pallets × pallet_weight
        """
        return drums * gross_per_drum + pallets * pallet_weight

    def calculate_load_rate(self, volume_cbm: float, container_cbm: float) -> float:
        """装载率 = volume / container_cbm × 100%"""
        if container_cbm <= 0:
            return 0.0
        return round(volume_cbm / container_cbm * 100, 2)

    def judge_container(self, total_cbm: float, total_weight_kg: float) -> ContainerResult:
        """
        集装箱推荐判定逻辑：
        1. 20GP：≤28 CBM 且 ≤21000 kg → 最经济
        2. 40GP：≤56 CBM 且 ≤27000 kg → 建议升级
        3. 40HQ：≤67 CBM 且 ≤27000 kg → 高柜
        4. 超限：超出以上所有 → 警告拆单
        """
        limits_20gp = CONTAINER_LIMITS["20GP"]
        limits_40gp = CONTAINER_LIMITS["40GP"]
        limits_40hq = CONTAINER_LIMITS["40HQ"]

        if total_cbm <= limits_20gp["volume"] and total_weight_kg <= limits_20gp["weight"]:
            load_rate = self.calculate_load_rate(total_cbm, limits_20gp["volume"])
            return ContainerResult(
                recommended="20GP",
                load_rate=load_rate,
                volume_limit=limits_20gp["volume"],
                weight_limit=limits_20gp["weight"],
                status="ok",
            )
        elif total_cbm <= limits_40gp["volume"] and total_weight_kg <= limits_40gp["weight"]:
            load_rate = self.calculate_load_rate(total_cbm, limits_40gp["volume"])
            return ContainerResult(
                recommended="40GP",
                load_rate=load_rate,
                volume_limit=limits_40gp["volume"],
                weight_limit=limits_40gp["weight"],
                status="upgrade",
            )
        elif total_cbm <= limits_40hq["volume"] and total_weight_kg <= limits_40hq["weight"]:
            load_rate = self.calculate_load_rate(total_cbm, limits_40hq["volume"])
            return ContainerResult(
                recommended="40HQ",
                load_rate=load_rate,
                volume_limit=limits_40hq["volume"],
                weight_limit=limits_40hq["weight"],
                status="upgrade",
            )
        else:
            return ContainerResult(
                recommended="超限",
                load_rate=0.0,
                volume_limit=limits_40hq["volume"],
                weight_limit=limits_40hq["weight"],
                status="over_limit",
            )

    def generate_packing_scheme(
        self,
        drums: int,
        pallets: int,
        capacity_per_pallet: int,
        no_pallet: bool = False,
    ) -> str:
        """
        生成文本装配方案描述。
        """
        if no_pallet:
            return f"⚠️ 已选择不打卡板。共需 {drums} 个桶，按散货堆叠预估体积。"

        if pallets == 0:
            return f"⚠️ 当前配置无需卡板。共需 {drums} 个桶。"

        # 计算每板数量
        full_pallets = drums // capacity_per_pallet
        last_pallet_qty = drums % capacity_per_pallet

        if last_pallet_qty == 0:
            # 整除
            return f"✅ 完美整除，无尾数。共需 {pallets} 个卡板，每板 {capacity_per_pallet} 个，满载。"
        else:
            # 有余数
            if full_pallets > 0:
                return (f"⚠️ 存在尾数。共需 {pallets} 个卡板，"
                        f"前 {full_pallets} 个满板（每板 {capacity_per_pallet} 个），"
                        f"最后一个板装 {last_pallet_qty} 个。")
            else:
                return f"⚠️ 存在尾数。共需 {pallets} 个卡板，最后一个板装 {last_pallet_qty} 个。"

    # ─────────────────────────────────────────────────────────────────────────
    # 空运计算
    # ─────────────────────────────────────────────────────────────────────────

    def calculate_air_volume_weight(self, total_cbm: float, factor: int) -> float:
        """
        体积重计算：
        - factor=167：IATA 标准 (CBM × 167)
        - factor=6000：航司标准 (CBM × 1000000 ÷ 6000)
        """
        if factor == 167:
            return total_cbm * 167
        elif factor == 6000:
            return total_cbm * 1000000 / 6000
        return 0.0

    def calculate_chargeable_weight(
        self,
        actual_weight: float,
        vol_weight_167: float,
        vol_weight_6000: float,
    ) -> float:
        """计费重量 = max(实重, 体积重_167, 体积重_6000)"""
        return max(actual_weight, vol_weight_167, vol_weight_6000)

    # ─────────────────────────────────────────────────────────────────────────
    # 陆运计算
    # ─────────────────────────────────────────────────────────────────────────

    def check_land_overweight(self, total_weight_kg: float, threshold: float = 30000.0) -> bool:
        """公路限重阈值检查，默认 30 吨"""
        return total_weight_kg > threshold
```

---

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_calculation_service.py -v`
Expected: PASS

---

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/calculation_service.py backend/tests/test_calculation_service.py
git commit -m "feat(backend): add CalculationService for FR-4.x packaging calculation"
```

---

### Task BM-2: API 路由 — 包装计算端点

**Files:**
- Create: `backend/app/api/v1/packages.py`
- Modify: `backend/app/api/deps.py` — 添加 get_calculation_service
- Modify: `backend/app/main.py` — 注册 packages 路由

---

- [ ] **Step 1: 创建 API 路由**

Create `backend/app/api/v1/packages.py`:

```python
"""FR-4.x 包装计算 API — 海运/空运/陆运统一计算端点（只读）"""

from fastapi import APIRouter, Query, Depends
from typing import Optional
from app.services.calculation_service import CalculationService, CONTAINER_LIMITS
from app.models.order import PackagingType, Pallet
from app.database import SessionLocal
from app.api.deps import get_db


router = APIRouter(prefix="/api/v1/packages", tags=["包装计算"])


@router.get("/calculate")
async def calculate_package(
    mode: str = Query("manual", description="order / manual"),
    quantity_kg: float = Query(..., description="订单量 kg"),
    packaging_name: str = Query(..., description="包装类型名称"),
    pallet_spec: str = Query("1.1x1.1", description="1.0x1.0 / 1.1x1.1"),
    pallet_qty: int = Query(None, description="单板数量（默认取包装类型容量）"),
    no_pallet: bool = Query(False, description="不打卡板"),
    transport_mode: str = Query("sea", description="sea / air / land"),
    order_id: int = Query(None, description="订单ID（mode=order 时）"),
    internal_code: str = Query(None, description="内部编码（用于知识库匹配）"),
    db=Depends(get_db),
):
    """
    包装计算统一入口。

    - mode=manual：手动输入模式
    - mode=order：从订单带入数据，自动推荐包装类型
    - transport_mode=sea：返回桶数、卡板数、体积、毛重、集装箱推荐
    - transport_mode=air：返回计费重量对比（实重/IATA×167/航司÷6000）
    - transport_mode=land：返回总件数、毛重、体积、公路限重警告
    """
    service = CalculationService()

    # 查询包装类型信息
    packaging = db.query(PackagingType).filter_by(name=packaging_name).first()
    if not packaging:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"未找到包装类型：{packaging_name}")

    # 确定单板容量
    if pallet_spec == "1.0x1.0":
        capacity = packaging.pallet_qty_1x1 or 0
    else:
        capacity = packaging.pallet_qty_1_1x1_1 or 0

    # 如果未指定单板数量，使用默认值
    if pallet_qty is None:
        pallet_qty = capacity

    # 基础计算（海运/共用）
    drums = service.calculate_drums(quantity_kg, packaging.net_kg)
    pallets = service.calculate_pallets(drums, pallet_qty, no_pallet)
    total_cbm = service.calculate_volume(drums, packaging.cbm, pallets, 0.15 if not no_pallet else 0.0)
    total_weight_kg = service.calculate_gross_weight(drums, packaging.gross_kg, pallets, 27.0)

    if transport_mode == "sea":
        container = service.judge_container(total_cbm, total_weight_kg)
        scheme = service.generate_packing_scheme(drums, pallets, pallet_qty, no_pallet)
        return {
            "drums": drums,
            "pallets": pallets,
            "total_cbm": round(total_cbm, 3),
            "total_weight_kg": round(total_weight_kg, 2),
            "packing_scheme": scheme,
            "container": {
                "recommended": container.recommended,
                "load_rate": container.load_rate,
                "volume_limit": container.volume_limit,
                "weight_limit": container.weight_limit,
                "status": container.status,
            },
            "packaging": {
                "name": packaging.name,
                "drum_cbm": packaging.cbm,
                "drum_tare_kg": packaging.tare_kg,
                "drum_gross_kg": packaging.gross_kg,
                "pallet_spec": pallet_spec,
                "pallet_capacity": pallet_qty,
            },
        }

    elif transport_mode == "air":
        vol_weight_167 = service.calculate_air_volume_weight(total_cbm, factor=167)
        vol_weight_6000 = service.calculate_air_volume_weight(total_cbm, factor=6000)
        chargeable = service.calculate_chargeable_weight(total_weight_kg, vol_weight_167, vol_weight_6000)
        return {
            "actual_weight_kg": round(total_weight_kg, 2),
            "vol_weight_167": round(vol_weight_167, 2),
            "vol_weight_6000": round(vol_weight_6000, 2),
            "chargeable_weight_kg": round(chargeable, 2),
            "chargeable_weight_note": "取大者",
        }

    else:  # land
        overweight = service.check_land_overweight(total_weight_kg)
        return {
            "total_drums": drums,
            "total_weight_kg": round(total_weight_kg, 2),
            "total_cbm": round(total_cbm, 3),
            "overweight_warning": overweight,
        }


@router.get("/types")
async def get_packaging_types(db=Depends(get_db)):
    """获取所有包装类型（用于下拉选择）"""
    types = db.query(PackagingType).all()
    return {
        "types": [
            {
                "id": t.id,
                "name": t.name,
                "net_kg": t.net_kg,
                "cbm": t.cbm,
                "pallet_1x1": t.pallet_qty_1x1,
                "pallet_1_1x1_1": t.pallet_qty_1_1x1_1,
            }
            for t in types
        ]
    }


@router.get("/recommend")
async def recommend_packaging(
    internal_code: str = Query(..., description="内部编码"),
    db=Depends(get_db),
):
    """
    根据 internal_code 查询产品知识库，推荐包装类型。
    """
    from app.models.order import ProductKnowledge

    knowledge = db.query(ProductKnowledge).filter_by(internal_code=internal_code).first()
    if not knowledge:
        return {
            "internal_code": internal_code,
            "recommended_packaging": None,
            "reason": None,
        }

    return {
        "internal_code": internal_code,
        "recommended_packaging": knowledge.recommended_packaging,
        "reason": "历史使用记录",
    }
```

---

- [ ] **Step 2: 添加 dependency**

Modify `backend/app/api/deps.py` — 添加：

```python
from app.services.calculation_service import CalculationService

def get_calculation_service() -> CalculationService:
    """包装计算服务依赖"""
    return CalculationService()
```

---

- [ ] **Step 3: 注册路由**

Modify `backend/app/main.py` — 添加：

```python
from app.api.v1.packages import router as packages_router

app.include_router(packages_router)
```

---

- [ ] **Step 4: 验证**

Run: `curl http://localhost:8000/api/v1/packages/types`
Expected: 返回包装类型列表

Run: `curl "http://localhost:8000/api/v1/packages/calculate?quantity_kg=1500&packaging_name=125kg新款胶桶&pallet_spec=1.1x1.1&transport_mode=sea"`
Expected: 返回海运计算结果

---

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/packages.py backend/app/api/deps.py backend/app/main.py
git commit -m "feat(backend): add FR-4.x packaging calculation API endpoints"
```

---

## Track 2: Frontend（FE-1 → FE-2 → FE-3 → FE-4）

### Task FE-1: API 客户端 — packages.ts

**Files:**
- Create: `frontend/src/api/packages.ts`

---

- [ ] **Step 1: 创建 API 客户端**

Create `frontend/src/api/packages.ts`:

```typescript
import axios from 'axios'

const BASE_URL = '/api/v1/packages'

// ── Types ────────────────────────────────────────────────────────────────────────

export interface PackagingType {
  id: number
  name: string
  net_kg: number
  cbm: number
  pallet_1x1: number | null
  pallet_1_1x1_1: number | null
}

export interface ContainerResult {
  recommended: string
  load_rate: number
  volume_limit: number
  weight_limit: number
  status: string
}

export interface SeaCalculationResult {
  drums: number
  pallets: number
  total_cbm: number
  total_weight_kg: number
  packing_scheme: string
  container: ContainerResult
  packaging: {
    name: string
    drum_cbm: number
    drum_tare_kg: number
    drum_gross_kg: number
    pallet_spec: string
    pallet_capacity: number
  }
}

export interface AirCalculationResult {
  actual_weight_kg: number
  vol_weight_167: number
  vol_weight_6000: number
  chargeable_weight_kg: number
  chargeable_weight_note: string
}

export interface LandCalculationResult {
  total_drums: number
  total_weight_kg: number
  total_cbm: number
  overweight_warning: boolean
}

export type CalculationResult = SeaCalculationResult | AirCalculationResult | LandCalculationResult

export interface RecommendResponse {
  internal_code: string
  recommended_packaging: string | null
  reason: string | null
}

// ── API Functions ─────────────────────────────────────────────────────────────

export const getPackagingTypes = async (): Promise<{ types: PackagingType[] }> => {
  const response = await axios.get<{ types: PackagingType[] }>(`${BASE_URL}/types`)
  return response.data
}

export const calculatePackage = async (params: {
  mode?: 'order' | 'manual'
  quantity_kg: number
  packaging_name: string
  pallet_spec?: '1.0x1.0' | '1.1x1.1'
  pallet_qty?: number
  no_pallet?: boolean
  transport_mode?: 'sea' | 'air' | 'land'
  order_id?: number
  internal_code?: string
}): Promise<CalculationResult> => {
  const response = await axios.get<CalculationResult>(`${BASE_URL}/calculate`, { params })
  return response.data
}

export const recommendPackaging = async (internalCode: string): Promise<RecommendResponse> => {
  const response = await axios.get<RecommendResponse>(`${BASE_URL}/recommend`, {
    params: { internal_code: internalCode }
  })
  return response.data
}
```

---

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/packages.ts && git commit -m "feat(frontend): add packaging calculation API client"
```

---

### Task FE-2: PackageCalc.vue — 主页面

**Files:**
- Create: `frontend/src/views/phase1/PackageCalc.vue`
- Modify: `frontend/src/router/index.ts` — 添加 /package-calc 路由
- Modify: `frontend/src/views/Layout.vue` — 添加导航入口

---

- [ ] **Step 1: 创建 PackageCalc.vue**

Create `frontend/src/views/phase1/PackageCalc.vue`:

```vue
<template>
  <div class="package-calc-page">
    <div class="page-header">
      <h1 class="page-title">包装计算</h1>
      <p class="page-subtitle">物流测算参谋 — 海运/空运/陆运一体化计算</p>
    </div>

    <!-- 顶部控制面板 -->
    <div class="control-panel">
      <!-- 运输模式切换 -->
      <div class="control-section">
        <label class="control-label">运输模式</label>
        <el-radio-group v-model="transportMode" class="mode-radio">
          <el-radio-button value="sea">🚢 海运</el-radio-button>
          <el-radio-button value="air">✈️ 空运</el-radio-button>
          <el-radio-button value="land">🚛 陆运</el-radio-button>
        </el-radio-group>
      </div>

      <!-- 输入模式切换（仅海运显示） -->
      <div class="control-section" v-if="transportMode === 'sea'">
        <label class="control-label">输入模式</label>
        <el-radio-group v-model="inputMode" class="mode-radio">
          <el-radio-button value="order">📦 按订单计算</el-radio-button>
          <el-radio-button value="manual">✍️ 手动输入</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <!-- 海运模式：输入面板 -->
    <div class="input-panel" v-if="transportMode === 'sea'">
      <!-- 按订单模式 -->
      <div v-if="inputMode === 'order'" class="order-input-mode">
        <el-select
          v-model="selectedOrderId"
          filterable
          remote
          placeholder="搜索订单号或客户名称"
          :remote-method="searchOrders"
          :loading="searchingOrders"
          class="order-select"
          @change="handleOrderChange"
        >
          <el-option
            v-for="order in searchResults"
            :key="order.id"
            :label="order.order_no"
            :value="order.id"
          >
            <span>{{ order.order_no }}</span>
            <span class="customer-tag">{{ order.customer_code }}</span>
          </el-option>
        </el-select>

        <el-select
          v-model="selectedInternalCode"
          placeholder="选择产品（内部编码）"
          class="product-select"
          :disabled="!selectedOrderId"
          @change="handleProductChange"
        >
          <el-option
            v-for="item in orderItems"
            :key="item.internal_code"
            :label="item.internal_code"
            :value="item.internal_code"
          >
            {{ item.internal_code }} — {{ item.product_cn }}
          </el-option>
        </el-select>
      </div>

      <!-- 手动输入模式 -->
      <div v-else class="manual-input-mode">
        <el-input-number
          v-model="quantityKg"
          :min="0"
          :step="100"
          placeholder="订单量 (kg)"
          class="quantity-input"
        />
      </div>

      <!-- 通用：包装类型选择 -->
      <PackagingTypeSelect
        v-model="packagingName"
        :recommended="packagingRecommendation"
        @change="handlePackagingChange"
      />

      <!-- 通用：数量输入（手动模式时显示） -->
      <div class="form-row" v-if="inputMode === 'manual' || transportMode !== 'sea'">
        <label class="form-label">订单量 (kg)</label>
        <el-input-number v-model="quantityKg" :min="0" :step="100" />
      </div>

      <!-- 海运：卡板设置 -->
      <div class="form-row" v-if="transportMode === 'sea'">
        <label class="form-label">卡板规格</label>
        <el-radio-group v-model="palletSpec" :disabled="noPallet">
          <el-radio-button value="1.0x1.0">1.0×1.0m</el-radio-button>
          <el-radio-button value="1.1x1.1">1.1×1.1m</el-radio-button>
        </el-radio-group>

        <label class="form-label" style="margin-left: 16px;">单板数量</label>
        <el-input-number
          v-model="palletQty"
          :min="0"
          :disabled="noPallet"
          class="pallet-qty-input"
        />

        <el-checkbox v-model="noPallet" class="no-pallet-checkbox">不打卡板</el-checkbox>
      </div>
    </div>

    <!-- 计算结果区 -->
    <div class="result-panel" v-if="hasValidInput" v-loading="calculating">
      <!-- 海运结果 -->
      <template v-if="transportMode === 'sea' && seaResult">
        <!-- 智能结论区 -->
        <div class="smart-conclusion" :class="containerStatusClass">
          <p class="conclusion-text">{{ seaResult.packing_scheme }}</p>
          <p class="container-advice">
            当前体积约 {{ seaResult.total_cbm }} CBM，
            {{ seaResult.container.status === 'ok'
              ? `强烈建议使用 ${seaResult.container.recommended}（装载率 ${seaResult.container.load_rate}%）`
              : `建议升级为 ${seaResult.container.recommended}（装载率 ${seaResult.container.load_rate}%）` }}。
          </p>
        </div>

        <!-- 核心指标卡片 -->
        <div class="metric-cards">
          <el-card class="metric-card">
            <div class="metric-value">{{ seaResult.drums }}</div>
            <div class="metric-label">桶/箱数</div>
          </el-card>
          <el-card class="metric-card">
            <div class="metric-value">{{ seaResult.pallets }}</div>
            <div class="metric-label">卡板数</div>
          </el-card>
          <el-card class="metric-card">
            <div class="metric-value">{{ seaResult.total_cbm.toFixed(2) }}</div>
            <div class="metric-label">总体积 (CBM)</div>
          </el-card>
          <el-card class="metric-card">
            <div class="metric-value">{{ seaResult.total_weight_kg.toLocaleString() }}</div>
            <div class="metric-label">总毛重 (KG)</div>
          </el-card>
        </div>
      </template>

      <!-- 空运结果 -->
      <template v-if="transportMode === 'air' && airResult">
        <AirFreightPanel :result="airResult" />
      </template>

      <!-- 陆运结果 -->
      <template v-if="transportMode === 'land' && landResult">
        <LandTransportPanel :result="landResult" />
      </template>
    </div>

    <!-- 空状态 -->
    <div class="empty-state" v-else-if="!calculating">
      <el-empty description="请填写参数后查看计算结果" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import {
  calculatePackage,
  getPackagingTypes,
  recommendPackaging,
  type SeaCalculationResult,
  type AirCalculationResult,
  type LandCalculationResult,
  type PackagingType,
} from '@/api/packages'
import PackagingTypeSelect from '@/components/phase1/PackagingTypeSelect.vue'
import AirFreightPanel from '@/components/phase1/AirFreightPanel.vue'
import LandTransportPanel from '@/components/phase1/LandTransportPanel.vue'

const route = useRoute()

// ── State ────────────────────────────────────────────────────────────────────
const transportMode = ref<'sea' | 'air' | 'land'>('sea')
const inputMode = ref<'order' | 'manual'>('manual')
const selectedOrderId = ref<number | null>(null)
const selectedInternalCode = ref<string>('')
const quantityKg = ref<number | null>(null)
const packagingName = ref<string>('')
const palletSpec = ref<'1.0x1.0' | '1.1x1.1'>('1.1x1.1')
const palletQty = ref<number>(0)
const noPallet = ref(false)

const packagingTypes = ref<PackagingType[]>([])
const packagingRecommendation = ref<string | null>(null)
const seaResult = ref<SeaCalculationResult | null>(null)
const airResult = ref<AirCalculationResult | null>(null)
const landResult = ref<LandCalculationResult | null>(null)
const calculating = ref(false)
const searchResults = ref<any[]>([])
const searchingOrders = ref(false)
const orderItems = ref<any[]>([])

// ── Computed ────────────────────────────────────────────────────────────────
const hasValidInput = computed(() => {
  if (!quantityKg.value || quantityKg.value <= 0) return false
  if (!packagingName.value) return false
  return true
})

const containerStatusClass = computed(() => {
  if (!seaResult.value) return ''
  const status = seaResult.value.container.status
  if (status === 'ok') return 'status-ok'
  if (status === 'upgrade') return 'status-upgrade'
  return 'status-overlimit'
})

// ── Debounce ────────────────────────────────────────────────────────────────
let debounceTimer: ReturnType<typeof setTimeout> | null = null

const debouncedCalculate = () => {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    performCalculate()
  }, 300)
}

// ── Methods ────────────────────────────────────────────────────────────────
const loadPackagingTypes = async () => {
  const data = await getPackagingTypes()
  packagingTypes.value = data.types
  // 默认选第一个
  if (packagingTypes.value.length > 0) {
    packagingName.value = packagingTypes.value[0].name
    updatePalletQty()
  }
}

const updatePalletQty = () => {
  const type = packagingTypes.value.find(t => t.name === packagingName.value)
  if (!type) return
  palletQty.value = palletSpec.value === '1.0x1.0'
    ? (type.pallet_1x1 || 0)
    : (type.pallet_1_1x1_1 || 0)
}

const handlePackagingChange = () => {
  updatePalletQty()
  packagingRecommendation.value = null // 人工接管，清除推荐标记
  debouncedCalculate()
}

const searchOrders = async (query: string) => {
  if (!query) return
  searchingOrders.value = true
  try {
    const { getOrderList } = await import('@/api/merge')
    const data = await getOrderList({ search: query, page_size: 10 })
    searchResults.value = data.orders
  } catch (e) {
    console.error('Search orders failed:', e)
  } finally {
    searchingOrders.value = false
  }
}

const handleOrderChange = async (orderId: number) => {
  // 加载订单产品明细
  const { getOrderComparison } = await import('@/api/merge')
  const data = await getOrderComparison(orderId)
  orderItems.value = data.items
  if (orderItems.value.length > 0) {
    selectedInternalCode.value = orderItems.value[0].internal_code
    handleProductChange(selectedInternalCode.value)
  }
}

const handleProductChange = async (internalCode: string) => {
  if (!internalCode) return
  // 查询知识库推荐
  try {
    const rec = await recommendPackaging(internalCode)
    if (rec.recommended_packaging) {
      packagingName.value = rec.recommended_packaging
      packagingRecommendation.value = rec.recommended_packaging
      updatePalletQty()
    }
  } catch (e) {
    // 无推荐，继续用当前选择
  }
  debouncedCalculate()
}

// 监听所有输入变化，触发重新计算
watch([quantityKg, packagingName, palletSpec, palletQty, noPallet, transportMode], () => {
  if (hasValidInput.value) {
    debouncedCalculate()
  }
})

const performCalculate = async () => {
  if (!hasValidInput.value) return
  calculating.value = true
  try {
    const result = await calculatePackage({
      mode: inputMode.value,
      quantity_kg: quantityKg.value!,
      packaging_name: packagingName.value,
      pallet_spec: palletSpec.value,
      pallet_qty: palletQty.value,
      no_pallet: noPallet.value,
      transport_mode: transportMode.value,
      order_id: selectedOrderId.value || undefined,
      internal_code: selectedInternalCode.value || undefined,
    })

    if (transportMode.value === 'sea') {
      seaResult.value = result as SeaCalculationResult
    } else if (transportMode.value === 'air') {
      airResult.value = result as AirCalculationResult
    } else {
      landResult.value = result as LandCalculationResult
    }
  } catch (error) {
    console.error('Calculation failed:', error)
  } finally {
    calculating.value = false
  }
}

// URL 联动：检测从 FR-3.x 跳转过来的参数
onMounted(() => {
  loadPackagingTypes()

  const mode = route.query.mode as string
  const internalCode = route.query.internal_code as string
  if (mode === 'order' && internalCode) {
    inputMode.value = 'order'
    selectedInternalCode.value = internalCode
    // 尝试直接推荐
    handleProductChange(internalCode)
  }
})
</script>

<style scoped>
.package-calc-page { padding: 24px; max-width: 1200px; margin: 0 auto; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 28px; font-weight: 600; margin: 0 0 8px 0; }
.page-subtitle { font-size: 14px; color: #909399; margin: 0; }

.control-panel { display: flex; gap: 24px; flex-wrap: wrap; margin-bottom: 20px; padding: 16px; background: #f5f7fa; border-radius: 8px; }
.control-section { display: flex; align-items: center; gap: 12px; }
.control-label { font-size: 13px; color: #606266; font-weight: 500; }

.input-panel { background: #fff; border: 1px solid #e4e7ed; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
.order-input-mode { display: flex; gap: 12px; margin-bottom: 16px; }
.order-select { width: 280px; }
.product-select { width: 320px; }
.customer-tag { margin-left: 8px; color: #909399; font-size: 12px; }
.manual-input-mode { margin-bottom: 16px; }
.quantity-input { width: 200px; }

.form-row { display: flex; align-items: center; gap: 12px; margin-top: 16px; }
.form-label { font-size: 13px; color: #606266; min-width: 80px; }
.pallet-qty-input { width: 120px; }
.no-pallet-checkbox { margin-left: 16px; }

.result-panel { display: flex; flex-direction: column; gap: 16px; }
.smart-conclusion { padding: 16px 20px; border-radius: 8px; font-size: 15px; line-height: 1.6; }
.smart-conclusion.status-ok { background: #f0f9eb; border: 1px solid #c2e7b0; }
.smart-conclusion.status-upgrade { background: #fdf6ec; border: 1px solid #f5dab1; }
.smart-conclusion.status-overlimit { background: #fef0f0; border: 1px solid #fbc4c4; }
.conclusion-text { margin: 0 0 4px 0; font-weight: 500; }
.container-advice { margin: 0; color: #606266; font-size: 13px; }

.metric-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.metric-card { text-align: center; }
.metric-value { font-size: 28px; font-weight: 700; color: #303133; }
.metric-label { font-size: 12px; color: #909399; margin-top: 4px; }

.empty-state { padding: 60px 0; }

@media (max-width: 768px) {
  .metric-cards { grid-template-columns: repeat(2, 1fr); }
}
</style>
```

---

- [ ] **Step 2: 添加路由**

Modify `frontend/src/router/index.ts` — 添加 `/package-calc` 路由，指向 `PackageCalc.vue`。

---

- [ ] **Step 3: 添加导航入口**

Modify `frontend/src/views/Layout.vue` — 添加导航菜单项 "包装计算"。

---

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/phase1/PackageCalc.vue frontend/src/router/index.ts frontend/src/views/Layout.vue
git commit -m "feat(frontend): add PackageCalc page with transport mode switcher"
```

---

### Task FE-3: PackagingTypeSelect.vue — 包装类型下拉 + 推荐气泡

**Files:**
- Create: `frontend/src/components/phase1/PackagingTypeSelect.vue`

---

- [ ] **Step 1: 创建 PackagingTypeSelect.vue**

Create `frontend/src/components/phase1/PackagingTypeSelect.vue`:

```vue
<template>
  <div class="packaging-select">
    <label class="form-label">包装类型</label>
    <el-select
      :model-value="modelValue"
      @change="$emit('update:modelValue', $event)"
      placeholder="选择包装类型"
      class="packaging-select-input"
      :class="{ 'has-recommendation': recommended }"
    >
      <el-option
        v-for="type in packagingTypes"
        :key="type.id"
        :label="type.name"
        :value="type.name"
      >
        <span>{{ type.name }}</span>
        <span class="specs-tag">{{ type.net_kg }}kg</span>
      </el-option>
    </el-select>

    <div class="recommendation-tip" v-if="recommended && !manualOverride">
      <el-icon><InfoFilled /></el-icon>
      <span>💡 系统根据产品知识库自动推荐：{{ recommended }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { getPackagingTypes, type PackagingType } from '@/api/packages'
import { InfoFilled } from '@element-plus/icons-vue'

const props = defineProps<{
  modelValue: string
  recommended: string | null
}>()

defineEmits(['update:modelValue'])

const packagingTypes = ref<PackagingType[]>([])
const manualOverride = ref(false)

watch(() => props.modelValue, (newVal, oldVal) => {
  if (props.recommended && newVal !== props.recommended) {
    manualOverride.value = true
  }
})

onMounted(async () => {
  const data = await getPackagingTypes()
  packagingTypes.value = data.types
})
</script>

<style scoped>
.packaging-select { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.form-label { font-size: 13px; color: #606266; min-width: 80px; }
.packaging-select-input { width: 240px; }
.packaging-select-input.has-recommendation :deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px #67c23a inset;
}
.specs-tag { margin-left: 8px; color: #909399; font-size: 12px; }
.recommendation-tip { font-size: 12px; color: #409eff; display: flex; align-items: center; gap: 4px; }
</style>
```

---

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/phase1/PackagingTypeSelect.vue
git commit -m "feat(frontend): add PackagingTypeSelect with recommendation bubble"
```

---

### Task FE-4: AirFreightPanel.vue + LandTransportPanel.vue

**Files:**
- Create: `frontend/src/components/phase1/AirFreightPanel.vue`
- Create: `frontend/src/components/phase1/LandTransportPanel.vue`

---

- [ ] **Step 1: 创建 AirFreightPanel.vue**

Create `frontend/src/components/phase1/AirFreightPanel.vue`:

```vue
<template>
  <div class="air-freight-panel">
    <div class="panel-header">
      <h3>✈️ 空运计费重量计算</h3>
    </div>

    <div class="weight-cards">
      <el-card class="weight-card actual">
        <div class="weight-value">{{ result.actual_weight_kg.toLocaleString() }}</div>
        <div class="weight-label">📏 物理实重 (KG)</div>
        <div class="weight-note">灰色基准参考值</div>
      </el-card>

      <el-card class="weight-card iata">
        <div class="weight-value">{{ result.vol_weight_167.toLocaleString() }}</div>
        <div class="weight-label">✈️ IATA 标准 (×167)</div>
        <div class="weight-note">国际通用标准</div>
      </el-card>

      <el-card class="weight-card airline">
        <div class="weight-value">{{ result.vol_weight_6000.toLocaleString() }}</div>
        <div class="weight-label">📦 航司标准 (÷6000)</div>
        <div class="weight-note">部分航司标准</div>
      </el-card>

      <el-card class="weight-card chargeable" :class="{ highlight: isHighlighted }">
        <div class="weight-value">{{ result.chargeable_weight_kg.toLocaleString() }}</div>
        <div class="weight-label">⚖️ 计费重量 (KG)</div>
        <div class="weight-note">最终付费依据 — {{ result.chargeable_weight_note }}</div>
      </el-card>
    </div>

    <div class="warning-tip">
      <el-icon><Warning /></el-icon>
      <span>⚠️ 实际计费重量取决于您合作的货代或航空公司报价条款，请以最终确认的系数为准。</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Warning } from '@element-plus/icons-vue'
import type { AirCalculationResult } from '@/api/packages'

const props = defineProps<{
  result: AirCalculationResult
}>()

const isHighlighted = computed(() => {
  return props.result.chargeable_weight_kg === props.result.actual_weight_kg
})
</script>

<style scoped>
.air-freight-panel { }
.panel-header { margin-bottom: 16px; }
.panel-header h3 { margin: 0; font-size: 16px; font-weight: 600; }

.weight-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
.weight-card { text-align: center; }
.weight-card.actual .weight-value { color: #909399; }
.weight-card.iata .weight-value { color: #67c23a; }
.weight-card.airline .weight-value { color: #409eff; }
.weight-card.chargeable .weight-value { color: #f56c6c; }
.weight-card.chargeable.highlight { border: 2px solid #f56c6c; }
.weight-value { font-size: 24px; font-weight: 700; margin-bottom: 4px; }
.weight-label { font-size: 13px; font-weight: 500; margin-bottom: 2px; }
.weight-note { font-size: 11px; color: #909399; }

.warning-tip { display: flex; align-items: center; gap: 8px; padding: 12px; background: #fdf6ec; border: 1px solid #f5dab1; border-radius: 6px; font-size: 13px; color: #e6a23c; }
</style>
```

- [ ] **Step 2: 创建 LandTransportPanel.vue**

Create `frontend/src/components/phase1/LandTransportPanel.vue`:

```vue
<template>
  <div class="land-transport-panel">
    <div class="panel-header">
      <h3>🚛 陆运总重计算</h3>
    </div>

    <div class="metric-cards">
      <el-card class="metric-card">
        <div class="metric-value">{{ result.total_drums }}</div>
        <div class="metric-label">总件数</div>
      </el-card>
      <el-card class="metric-card">
        <div class="metric-value">{{ result.total_weight_kg.toLocaleString() }}</div>
        <div class="metric-label">总毛重 (KG)</div>
      </el-card>
      <el-card class="metric-card">
        <div class="metric-value">{{ result.total_cbm.toFixed(2) }}</div>
        <div class="metric-label">总体积 (CBM)</div>
      </el-card>
    </div>

    <div class="overweight-warning" v-if="result.overweight_warning">
      <el-icon><WarningFilled /></el-icon>
      <span>⚠️ 总重超过 30 吨，部分国家公路限重规定，请注意安排。</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { WarningFilled } from '@element-plus/icons-vue'
import type { LandCalculationResult } from '@/api/packages'

defineProps<{
  result: LandCalculationResult
}>()
</script>

<style scoped>
.land-transport-panel { }
.panel-header { margin-bottom: 16px; }
.panel-header h3 { margin: 0; font-size: 16px; font-weight: 600; }

.metric-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px; }
.metric-card { text-align: center; }
.metric-value { font-size: 28px; font-weight: 700; color: #303133; }
.metric-label { font-size: 12px; color: #909399; margin-top: 4px; }

.overweight-warning { display: flex; align-items: center; gap: 8px; padding: 12px; background: #fef0f0; border: 1px solid #fbc4c4; border-radius: 6px; font-size: 13px; color: #f56c6c; }
</style>
```

---

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/phase1/AirFreightPanel.vue frontend/src/components/phase1/LandTransportPanel.vue
git commit -m "feat(frontend): add AirFreightPanel and LandTransportPanel components"
```

---

## 验证清单

After all tasks are complete, verify each item:

- [ ] **Backend**: `curl http://localhost:8000/api/v1/packages/types` 返回 13 种包装类型
- [ ] **Backend**: `curl "http://localhost:8000/api/v1/packages/calculate?quantity_kg=1500&packaging_name=125kg新款胶桶&pallet_spec=1.1x1.1&transport_mode=sea"` 返回海运计算结果
- [ ] **Backend**: 验证桶数 = ceil(1500/125) = 12，卡板数 = ceil(12/5) = 3
- [ ] **Backend**: `transport_mode=air` 返回计费重量对比
- [ ] **Backend**: `transport_mode=land` 返回陆运结果
- [ ] **Backend**: `GET /api/v1/packages/recommend?internal_code=XXX` 返回推荐结果
- [ ] **Frontend**: 访问 http://localhost:5173/package-calc 页面正常加载
- [ ] **Frontend**: 切换海运/空运/陆运模式，显示不同面板
- [ ] **Frontend**: 实时计算：输入变化后 300ms 自动重新计算
- [ ] **Frontend**: 不打卡板勾选后，卡板数归零，体积仅含桶身
- [ ] **Frontend**: 空运计费重量面板：三值并排，取大者标红

---

## Self-Review Checklist

Before saving this plan, I checked:

1. **Spec coverage**: 所有 FR-4.x 验收标准（AC-1 ~ AC-15）均有对应任务实现
2. **Placeholder scan**: 无 "TBD"、"TODO"、未完成的步骤
3. **Type consistency**: 所有 TypeScript 接口与后端响应字段一致
4. **计算公式正确性**: drums = ceil(qty/net)，pallets = ceil(drums/capacity)，体积/重量公式正确
5. **集装箱阈值**: 20GP(28CBM/21000kg)、40GP(56CBM/27000kg)、40HQ(67CBM/27000kg)

---

*Plan version: v1.0.0 — for agentic execution*