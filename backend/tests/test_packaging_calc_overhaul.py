"""黄金用例 G1–G6：包装计算彻底整改（2026-09-24 口径）"""
import math

import pytest

from app.services.packaging_service import (
    calculate,
    calculate_single_product,
    calculate_order_packaging,
    OrderProductInput,
)


class TestPackagingOverhaul:
    def test_g1_no_pallet_60kg(self):
        """60kg蓝桶 2160kg 不托 → 36件，毛2286，CBM 3.240"""
        r = calculate("60kg蓝桶", 2160, use_pallet=False)
        assert r.drums == 36
        assert r.pallets == 0
        # 2160 + 36*3.5 = 2286
        assert r.total_weight_kg == pytest.approx(2286, abs=0.1)
        assert r.total_cbm == pytest.approx(3.24, abs=0.001)

    def test_g2_partial_fill_with_pallet(self):
        """125胶桶 360kg fill=120 + 1.0板 → 3件1托，毛394，CBM 0.780"""
        r = calculate("125kg新款胶桶", 360, use_pallet=True, pallet_name="1.0*1.0m", actual_fill_kg=120)
        assert r.drums == 3
        assert r.pallets == 1  # ceil(3/4) 含尾板
        assert r.remainder == 3
        assert r.full_pallets == 0
        assert r.total_weight_kg == pytest.approx(394, abs=0.1)  # 360+18+16
        assert r.total_cbm == pytest.approx(0.78, abs=0.001)  # 0.63+0.15

    def test_g3_last_drum_partial_net_exact(self):
        """350kg 标称125 → 净350 不是 375；3件1托毛384"""
        r = calculate("125kg新款胶桶", 350, use_pallet=True, pallet_name="1.0*1.0m")
        assert r.drums == 3
        assert r.total_weight_kg == pytest.approx(384, abs=0.1)  # 350+18+16
        assert r.total_cbm == pytest.approx(0.78, abs=0.001)

    def test_g4_fill_120_25_packages(self):
        """3000kg fill=120 不托 → 25件（不是24），毛3150"""
        r = calculate("125kg新款胶桶", 3000, use_pallet=False, actual_fill_kg=120)
        assert r.drums == 25
        assert r.total_weight_kg == pytest.approx(3150, abs=0.1)  # 3000+150
        assert r.total_cbm == pytest.approx(5.25, abs=0.001)

    def test_g5_pallet_override_zero_no_pallet_terms(self):
        """托数改0 → 毛378=360+18，CBM 0.63，禁止按板位放大"""
        r = calculate("125kg新款胶桶", 360, use_pallet=True, pallet_name="1.0*1.0m", actual_fill_kg=120, pallets_override=0)
        assert r.drums == 3
        assert r.pallets == 0
        assert r.total_weight_kg == pytest.approx(378, abs=0.1)
        assert r.total_cbm == pytest.approx(0.63, abs=0.001)

    def test_g5b_never_use_capacity_slots(self):
        """3桶不得被算成4桶体积毛重（历史 bug：4*131+17=541）"""
        r = calculate("125kg新款胶桶", 360, use_pallet=True, pallet_name="1.0*1.0m", actual_fill_kg=120)
        assert r.total_weight_kg != pytest.approx(541, abs=1)
        assert r.total_cbm != pytest.approx(0.88, abs=0.01)
        # 正确值
        assert r.total_weight_kg == pytest.approx(394, abs=0.1)

    def test_g6_mixed_products_sum(self):
        """9×50细口 + 2×25kg/包 独立开托"""
        products = [
            OrderProductInput(
                product_name="A",
                packaging_name="50kg蓝桶(细口)",
                quantity_kg=450,
                specification_kg=50,
                barrel_type="胶桶",
                pallet_spec="1.1*1.1m",
            ),
            OrderProductInput(
                product_name="B",
                packaging_name="25kg/包",
                quantity_kg=50,
                specification_kg=25,
                barrel_type="胶桶",
                pallet_spec="1.1*1.1m",
            ),
        ]
        result = calculate_order_packaging(products)
        assert result.total_drums == 9 + 2
        # A: ceil(450/50)=9, ceil(9/18)=1 托；B: ceil(50/25)=2, ceil(2/40)=1 托
        assert result.total_pallets == 2
        # 毛 = 500 + (9*2.5+2*0.5) + (1+1)*19 = 500+23.5+38 = 561.5
        assert result.total_weight_kg == pytest.approx(561.5, abs=0.2)
        assert result.total_net_weight_kg == pytest.approx(500, abs=0.1)

    def test_single_product_formula(self):
        r = calculate_single_product(
            "125kg新款胶桶", 350, 125, "胶桶", "1.0*1.0m"
        )
        assert r.drums == 3
        assert r.pallets == 1
        assert r.net_weight_kg == 350
        assert r.gross_weight_kg == pytest.approx(384, abs=0.1)

    def test_ceiling_packages(self):
        assert math.ceil(350 / 125) == 3
        assert math.ceil(3000 / 120) == 25
        assert math.ceil(3 / 4) == 1
