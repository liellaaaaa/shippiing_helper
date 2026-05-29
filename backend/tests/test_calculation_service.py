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
        assert result.recommended == "20GP"
        assert result.status == "ok"

    def test_judge_40gp_upgrade(self):
        """超出 20GP 但满足 40GP → 建议升级 40GP"""
        service = CalculationService()
        result = service.judge_container(total_cbm=30, total_weight_kg=25000)
        assert result.recommended == "40GP"
        assert result.status == "upgrade"

    def test_judge_40hq(self):
        """超出 40GP 但满足 40HQ → 建议升级 40HQ"""
        service = CalculationService()
        result = service.judge_container(total_cbm=60, total_weight_kg=26000)
        assert result.recommended == "40HQ"
        assert result.status == "upgrade"

    def test_judge_over_limit(self):
        """超出 40HQ 上限 → 警告"""
        service = CalculationService()
        result = service.judge_container(total_cbm=70, total_weight_kg=28000)
        assert result.recommended == "超限"
        assert result.status == "over_limit"

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
        assert "满载" in scheme
        assert "无尾数" in scheme
        # 确保不是"存在尾数"的情况
        assert "存在尾数" not in scheme

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
        assert "个桶" in scheme
        # Should not say "共需 X 个卡板" - that phrasing implies pallets are needed
        # "不打卡板" may contain the word "卡板" but in a different context
        assert "共需" not in scheme or "个卡板" not in scheme


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