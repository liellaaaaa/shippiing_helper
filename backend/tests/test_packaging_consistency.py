"""批次3 一致性测试：packages.calculate 与 packaging.calculate 同源同值；
pallets_override=0 时 remainder 合理；product_name 透传。"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.packaging_service import (
    calculate,
    calculate_single_product,
    calculate_order_packaging,
    OrderProductInput,
)


client = TestClient(app)


def api_calculate(params: dict) -> dict:
    resp = client.get("/api/v1/packages/calculate", params=params)
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestApiMatchesPackagingService:
    """同一输入：packages.calculate 响应数值 == packaging_service.calculate"""

    def test_sea_no_pallet_60kg(self):
        """60kg蓝桶 2160kg 不托：API 与 packaging_service 一致（末桶不满按净重+桶皮）"""
        r = calculate("60kg蓝桶", 2160, use_pallet=False)
        api = api_calculate({
            "quantity_kg": 2160,
            "packaging_name": "60kg蓝桶",
            "no_pallet": True,
            "transport_mode": "sea",
        })
        assert api["drums"] == r.drums == 36
        assert api["pallets"] == r.pallets == 0
        assert api["total_cbm"] == pytest.approx(r.total_cbm, abs=0.001)
        assert api["total_weight_kg"] == pytest.approx(r.total_weight_kg, abs=0.1)
        # 禁止旧公式 drums*gross_kg（36*63.5=2286 与 2160+36*3.5=2286 本例巧合相等，
        # 用 CBM 校验走的是新路径：无托时 CBM=36*0.09=3.24，无 0.15 魔数托盘项）
        assert api["total_cbm"] == pytest.approx(3.24, abs=0.001)

    def test_sea_pallet_partial_fill(self):
        """125胶桶 360kg + 1.0板：API 与 packaging_service 一致（API 按标称 125）"""
        # API 无 actual_fill_kg 参数 → 与 calculate(..., actual_fill_kg=None) 比
        r_nominal = calculate(
            "125kg新款胶桶", 360, use_pallet=True, pallet_name="1.0*1.0m"
        )
        api = api_calculate({
            "quantity_kg": 360,
            "packaging_name": "125kg新款胶桶",
            "pallet_spec": "1.0x1.0",
            "no_pallet": False,
            "transport_mode": "sea",
        })
        assert api["drums"] == r_nominal.drums == 3
        assert api["pallets"] == r_nominal.pallets == 1
        assert api["total_cbm"] == pytest.approx(r_nominal.total_cbm, abs=0.001)
        assert api["total_weight_kg"] == pytest.approx(r_nominal.total_weight_kg, abs=0.1)
        # 托盘 CBM/皮重来自 DB（16/0.15），禁止 27.0 魔数
        # 3*0.21 + 1*0.15 = 0.78；360 + 3*6 + 1*16 = 394
        assert api["total_cbm"] == pytest.approx(0.78, abs=0.001)
        assert api["total_weight_kg"] == pytest.approx(394, abs=0.1)

    def test_sea_pallet_last_drum_partial_gross(self):
        """350kg 标称125 → 净350 不是 375（末桶不满）；毛 350+18+16=384"""
        api = api_calculate({
            "quantity_kg": 350,
            "packaging_name": "125kg新款胶桶",
            "pallet_spec": "1.0x1.0",
            "transport_mode": "sea",
        })
        assert api["drums"] == 3
        assert api["total_weight_kg"] == pytest.approx(384, abs=0.1)
        # 旧公式 drums*gross_kg + pallets*27 会得 3*131+27=420，禁止
        assert api["total_weight_kg"] != pytest.approx(420, abs=1)

    def test_sea_pallet_1_1_uses_db_pallet(self):
        """1.1*1.1 托盘：托重 19 / 托 CBM 0.1815（DB），不是 27 / 0.15"""
        api = api_calculate({
            "quantity_kg": 2160,
            "packaging_name": "60kg蓝桶",
            "pallet_spec": "1.1x1.1",
            "transport_mode": "sea",
        })
        # 60kg蓝桶 1.1*1.1 每板 16 件 → 36/16 → 3 托
        # 毛 = 2160 + 36*3.5 + 3*19 = 2343；CBM = 36*0.09 + 3*0.1815 = 3.7845
        assert api["pallets"] == 3
        assert api["total_weight_kg"] == pytest.approx(2343, abs=0.2)
        assert api["total_cbm"] == pytest.approx(3.7845, abs=0.002)

    def test_sea_pallet_1_0_capacity_override(self):
        """pallet_qty 自定义每板件数：与 calculate(drums_per_pallet=...) 一致"""
        r = calculate(
            "125kg新款胶桶", 1000,
            use_pallet=True, pallet_name="1.0*1.0m", drums_per_pallet=2,
        )
        api = api_calculate({
            "quantity_kg": 1000,
            "packaging_name": "125kg新款胶桶",
            "pallet_spec": "1.0x1.0",
            "pallet_qty": 2,
            "transport_mode": "sea",
        })
        assert api["drums"] == r.drums == 8
        assert api["pallets"] == r.pallets == 4  # ceil(8/2)
        assert api["total_cbm"] == pytest.approx(r.total_cbm, abs=0.001)
        assert api["total_weight_kg"] == pytest.approx(r.total_weight_kg, abs=0.1)

    def test_air_mode_uses_same_totals(self):
        """air 模式的实重与 packaging_service 毛重一致"""
        r = calculate("125kg新款胶桶", 350, use_pallet=True, pallet_name="1.0*1.0m")
        api = api_calculate({
            "quantity_kg": 350,
            "packaging_name": "125kg新款胶桶",
            "pallet_spec": "1.0x1.0",
            "transport_mode": "air",
        })
        assert api["actual_weight_kg"] == pytest.approx(r.total_weight_kg, abs=0.1)

    def test_land_mode_uses_same_totals(self):
        """land 模式的毛重/体积与 packaging_service 一致"""
        r = calculate("60kg蓝桶", 2160, use_pallet=False)
        api = api_calculate({
            "quantity_kg": 2160,
            "packaging_name": "60kg蓝桶",
            "no_pallet": True,
            "transport_mode": "land",
        })
        assert api["total_drums"] == r.drums
        assert api["total_weight_kg"] == pytest.approx(r.total_weight_kg, abs=0.1)
        assert api["total_cbm"] == pytest.approx(r.total_cbm, abs=0.001)


class TestPalletsOverrideRemainder:
    """pallets_override 覆盖后 full_pallets/remainder 与实际托数一致"""

    def test_override_zero_remainder_zero(self):
        """override=0 → pallets=0 且 remainder=0（不残留自动尾板）"""
        r = calculate(
            "125kg新款胶桶", 360,
            use_pallet=True, pallet_name="1.0*1.0m",
            actual_fill_kg=120, pallets_override=0,
        )
        assert r.pallets == 0
        assert r.full_pallets == 0
        assert r.remainder == 0
        # 托盘项为 0：毛 360+18=378，CBM 0.63
        assert r.total_weight_kg == pytest.approx(378, abs=0.1)
        assert r.total_cbm == pytest.approx(0.63, abs=0.001)

    def test_override_zero_on_single_product(self):
        """calculate_single_product 同样：override=0 → remainder=0"""
        r = calculate_single_product(
            "125kg新款胶桶", 360, 120, "胶桶", "1.0*1.0m",
            pallets_override=0,
        )
        assert r.pallets == 0
        assert r.full_pallets == 0
        assert r.remainder == 0

    def test_override_more_than_auto(self):
        """override > 自动托数：full/remainder 按实际托数重算，不超托"""
        # 3 桶 cap=4 → 自动 1 托（full=0, rem=3）；override=2 → 仍有 1 尾板
        r = calculate(
            "125kg新款胶桶", 360,
            use_pallet=True, pallet_name="1.0*1.0m",
            actual_fill_kg=120, pallets_override=2,
        )
        assert r.pallets == 2
        assert r.full_pallets + (1 if r.remainder else 0) <= r.pallets
        assert r.remainder == 3  # 3 件尾板占用 1 托，另一托为空

    def test_override_fewer_than_auto(self):
        """override < 自动托数：full ≤ pallets，托数不够时 remainder 归 0"""
        # 1100kg/125=9 件 cap=4 → 自动 3 托（full=2, rem=1）；override=2 → 2 整板装 8，余 1 装不下
        r = calculate(
            "125kg新款胶桶", 1100,
            use_pallet=True, pallet_name="1.0*1.0m",
            pallets_override=2,
        )
        assert r.drums == 9
        assert r.pallets == 2
        assert r.full_pallets == 2
        assert r.remainder == 0
        assert r.full_pallets + (1 if r.remainder else 0) <= r.pallets

    def test_override_exact_full_boards(self):
        """整除时 override=自动托数：remainder=0"""
        # 8 桶 cap=4 → 2 整板无尾
        r = calculate(
            "125kg新款胶桶", 1000,
            use_pallet=True, pallet_name="1.0*1.0m",
            drums_per_pallet=2, pallets_override=4,
        )
        assert r.drums == 8
        assert r.pallets == 4
        assert r.full_pallets == 4
        assert r.remainder == 0

    def test_auto_without_override_unchanged(self):
        """不传 override 时 full/remainder 仍按含尾板口径（G2 回归）"""
        r = calculate(
            "125kg新款胶桶", 360,
            use_pallet=True, pallet_name="1.0*1.0m", actual_fill_kg=120,
        )
        assert r.pallets == 1
        assert r.full_pallets == 0
        assert r.remainder == 3


class TestProductNamePassthrough:
    """product_name 透传真实产品名，不再写成 packaging_name"""

    def test_single_product_name(self):
        r = calculate_single_product(
            "125kg新款胶桶", 350, 125, "胶桶", "1.0*1.0m",
            product_name="甲产品",
        )
        assert r.product_name == "甲产品"
        assert r.packaging_name == "125kg新款胶桶"

    def test_single_product_name_fallback(self):
        """不传 product_name 时回退包装名（兼容旧调用）"""
        r = calculate_single_product("125kg新款胶桶", 350, 125, "胶桶", "1.0*1.0m")
        assert r.product_name == "125kg新款胶桶"

    def test_order_product_details_names(self):
        """订单级 product_details.product_name 用真实产品名"""
        products = [
            OrderProductInput(
                product_name="柠檬酸",
                packaging_name="25kg/包",
                quantity_kg=50,
                specification_kg=25,
                barrel_type="胶桶",
                pallet_spec="1.1*1.1m",
            ),
            OrderProductInput(
                product_name="甘油",
                packaging_name="125kg新款胶桶",
                quantity_kg=350,
                specification_kg=125,
                barrel_type="胶桶",
                pallet_spec="1.0*1.0m",
            ),
        ]
        result = calculate_order_packaging(products)
        names = [p.product_name for p in result.product_details]
        assert names == ["柠檬酸", "甘油"]
        pkgs = [p.packaging_name for p in result.product_details]
        assert pkgs == ["25kg/包", "125kg新款胶桶"]


class TestResponseShapePreserved:
    """API 对外响应字段形状不变（调用方不炸）"""

    def test_sea_shape(self):
        api = api_calculate({
            "quantity_kg": 2160,
            "packaging_name": "60kg蓝桶",
            "no_pallet": True,
            "transport_mode": "sea",
        })
        for key in ("drums", "pallets", "total_cbm", "total_weight_kg",
                    "packing_scheme", "container", "packaging"):
            assert key in api, key
        for key in ("recommended", "load_rate", "volume_limit", "weight_limit", "status"):
            assert key in api["container"], key
        for key in ("name", "drum_cbm", "drum_tare_kg", "drum_gross_kg",
                    "pallet_spec", "pallet_capacity"):
            assert key in api["packaging"], key

    def test_air_shape(self):
        api = api_calculate({
            "quantity_kg": 2160,
            "packaging_name": "60kg蓝桶",
            "no_pallet": True,
            "transport_mode": "air",
        })
        for key in ("actual_weight_kg", "vol_weight_167", "vol_weight_6000",
                    "chargeable_weight_kg", "chargeable_weight_note"):
            assert key in api, key

    def test_land_shape(self):
        api = api_calculate({
            "quantity_kg": 2160,
            "packaging_name": "60kg蓝桶",
            "no_pallet": True,
            "transport_mode": "land",
        })
        for key in ("total_drums", "total_weight_kg", "total_cbm", "overweight_warning"):
            assert key in api, key
