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