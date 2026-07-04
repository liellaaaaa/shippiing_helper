"""
包装计算服务 - 从 references/packaging_data.json 加载包装规格，计算桶数/托数/CBM/毛重/货柜判断
"""
import os
import math
import json
from dataclasses import dataclass, field
from typing import Optional


PACKAGING_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "references", "packaging_data.json")


@dataclass
class PackageSpec:
    name: str
    dims: str
    cbm: float
    tare_kg: float
    gross_kg: float
    net_kg: float
    barrel_type: str
    is_palletizable: bool
    no_pallet_qty: Optional[int]
    pallet_qty_1x1: Optional[int]
    pallet_qty_1_1x1_1: Optional[int]


@dataclass
class PalletSpec:
    name: str
    dims: str
    weight_kg: float
    cbm: float


@dataclass
class ContainerSpec:
    name: str
    max_cbm: float
    max_weight_kg: float


@dataclass
class PackingResult:
    drums: int
    pallets: int
    drums_per_pallet: int
    pallet_type: Optional[str]
    total_cbm: float
    total_weight_kg: float
    fits_20gp: bool
    fits_40gp: bool
    recommended: str
    full_pallets: int = 0  # 整板数 = drums // drums_per_pallet


# === 订单级别汇总计算新增 ===

@dataclass
class OrderProductInput:
    """订单中单个产品的输入"""
    product_name: str
    packaging_name: str          # 如 "125kg新款胶桶"
    quantity_kg: float           # 订单总净重 kg
    specification_kg: float     # 单桶/单袋净重 kg
    barrel_type: str             # "胶桶" / "编织袋" / "IBC"
    pallet_spec: str = "1.1*1.1m"  # 默认卡板规格


@dataclass
class ProductPackagingResult:
    """单个产品的包装计算结果"""
    product_name: str
    packaging_name: str
    specification_kg: float

    drums: int                  # 桶数/袋数
    drums_per_pallet: int       # 每板桶数
    pallets: int                # 整板数 = drums // drums_per_pallet
    pallet_spec: str            # 使用的卡板规格
    full_pallets: int          # 整板数（与 pallets 相同，兼容用）
    remainder: int             # 余数桶数 = drums % drums_per_pallet

    net_weight_kg: float         # 产品净重
    drum_tare_kg: float         # 桶身皮重
    pallet_tare_kg: float       # 卡板皮重
    gross_weight_kg: float     # 总毛重
    drum_cbm: float             # 桶身体积
    pallet_cbm: float           # 卡板体积
    total_volume_cbm: float    # 总体积


@dataclass
class PalletDetail:
    """按卡板尺寸分组的详情"""
    pallet_spec: str
    pallet_count: int
    drums_on_pallets: int
    volume_cbm: float
    weight_kg: float


@dataclass
class OrderPackagingResult:
    """订单级别包装汇总结果"""
    total_drums: int
    total_pallets: int
    total_volume_cbm: float
    total_weight_kg: float
    total_net_weight_kg: float
    pallet_details: list[PalletDetail]  # 按卡板尺寸分组
    product_details: list[ProductPackagingResult]  # 各产品明细
    container_20gp_fit: bool
    container_40hq_fit: bool
    recommended: str
    load_rate_20gp: float
    load_rate_40hq: float


def _load_data() -> dict:
    with open(PACKAGING_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_package_types() -> list[PackageSpec]:
    """返回所有包装种类"""
    data = _load_data()
    return [
        PackageSpec(
            name=p["name"],
            dims=p["dims"],
            cbm=p["cbm"],
            tare_kg=p["tare_kg"],
            gross_kg=p["gross_kg"],
            net_kg=p["net_kg"],
            barrel_type=p["barrel_type"],
            is_palletizable=p["is_palletizable"],
            no_pallet_qty=p.get("no_pallet_qty"),
            pallet_qty_1x1=p.get("pallet_qty_1x1"),
            pallet_qty_1_1x1_1=p.get("pallet_qty_1_1x1_1"),
        )
        for p in data["packages"]
    ]


def get_pallet_types() -> list[PalletSpec]:
    """返回所有托盘种类"""
    data = _load_data()
    return [
        PalletSpec(name=p["name"], dims=p["dims"], weight_kg=p["weight_kg"], cbm=p["cbm"])
        for p in data["pallets"]
    ]


def get_container_specs() -> dict[str, ContainerSpec]:
    """返回货柜规格"""
    data = _load_data()
    return {
        "20GP": ContainerSpec(
            name="20GP",
            max_cbm=data["container_20gp"]["max_cbm"],
            max_weight_kg=data["container_20gp"]["max_weight_kg"],
        ),
        "40GP": ContainerSpec(
            name="40GP",
            max_cbm=data["container_40gp"]["max_cbm"],
            max_weight_kg=data["container_40gp"]["max_weight_kg"],
        ),
    }


def find_package(name: str) -> Optional[PackageSpec]:
    """按名称精确查找包装种类"""
    for p in get_package_types():
        if p.name == name:
            return p
    return None


def find_pallet(name: str) -> Optional[PalletSpec]:
    """按名称精确查找托盘种类"""
    for p in get_pallet_types():
        if p.name == name:
            return p
    return None


def calculate(
    packaging_name: str,
    order_qty_kg: float,
    use_pallet: bool = False,
    pallet_name: Optional[str] = None,
) -> PackingResult:
    """
    核心计算函数

    参数:
        packaging_name: 包装种类名称，如 "125kg新款胶桶"
        order_qty_kg: 订单总净重 kg
        use_pallet: 是否打卡板
        pallet_name: 托盘规格，如 "1.1*1.1m"（use_pallet=True 时必填）

    返回:
        PackingResult
    """
    pkg = find_package(packaging_name)
    if not pkg:
        raise ValueError(f"未找到包装种类: {packaging_name}")

    # 桶数 = ceil(order_qty / net_kg_per_drum)
    drums = math.ceil(order_qty_kg / pkg.net_kg)

    if not use_pallet:
        # 模式A：不打卡板
        pallets = 0
        drums_per_pallet = 0
        pallet_type = None
        full_pallets = 0
        total_cbm = drums * pkg.cbm
        total_weight = drums * pkg.gross_kg
    else:
        # 模式B：打卡板
        if not pallet_name:
            raise ValueError("use_pallet=True 时必须指定 pallet_name")
        pallet = find_pallet(pallet_name)
        if not pallet:
            raise ValueError(f"未找到托盘种类: {pallet_name}")

        # 确定每托盘桶数
        if "1.0*1.0" in pallet_name:
            drums_per_pallet = pkg.pallet_qty_1x1 or 0
        elif "1.1*1.1" in pallet_name:
            drums_per_pallet = pkg.pallet_qty_1_1x1_1 or 0
        else:
            drums_per_pallet = 0

        if drums_per_pallet == 0:
            raise ValueError(f"{packaging_name} 无法使用 {pallet_name} 打卡板")

        full_pallets = drums // drums_per_pallet
        remainder_val = drums - full_pallets * drums_per_pallet
        # pallets 存整板数，remainder = drums - pallets*per_pallet（可正可负）
        pallets = full_pallets
        pallet_type = pallet_name

        total_cbm = drums * pkg.cbm + pallets * pallet.cbm
        total_weight = drums * pkg.gross_kg + pallets * pallet.weight_kg

    # 货柜判断
    specs = get_container_specs()
    spec_20gp = specs["20GP"]
    spec_40gp = specs["40GP"]

    fits_20gp = total_cbm <= spec_20gp.max_cbm and total_weight <= spec_20gp.max_weight_kg
    fits_40gp = total_cbm <= spec_40gp.max_cbm and total_weight <= spec_40gp.max_weight_kg

    if fits_20gp:
        recommended = "20GP"
    elif fits_40gp:
        recommended = "40GP"
    else:
        recommended = "超出40GP限制"

    return PackingResult(
        drums=drums,
        pallets=pallets,
        drums_per_pallet=drums_per_pallet,
        pallet_type=pallet_type,
        total_cbm=round(total_cbm, 3),
        total_weight_kg=round(total_weight, 1),
        fits_20gp=fits_20gp,
        fits_40gp=fits_40gp,
        recommended=recommended,
        full_pallets=full_pallets,
    )


def calculate_all_schemes(
    packaging_name: str,
    order_qty_kg: float,
) -> list[PackingResult]:
    """
    计算所有可用方案（不打卡板 + 两种托盘）
    用于展示多个方案供用户选择
    """
    results = []

    # 不打卡板
    try:
        r = calculate(packaging_name, order_qty_kg, use_pallet=False)
        results.append(r)
    except Exception:
        pass

    # 打卡板（1.0*1.0 和 1.1*1.1）
    for pallet_name in ["1.0*1.0m", "1.1*1.1m"]:
        try:
            r = calculate(packaging_name, order_qty_kg, use_pallet=True, pallet_name=pallet_name)
            results.append(r)
        except Exception:
            pass

    return results


def calculate_single_product(
    packaging_name: str,
    quantity_kg: float,
    specification_kg: float,
    barrel_type: str,
    pallet_spec: str = "1.1*1.1m",
) -> ProductPackagingResult:
    """
    计算单个产品的包装需求

    Args:
        packaging_name: 包装类型名称，如 "125kg新款胶桶"
        quantity_kg: 订单总净重 kg
        specification_kg: 单桶/单袋净重 kg
        barrel_type: 包装方式: "胶桶" / "纸桶" / "编织袋" / "IBC"
        pallet_spec: 卡板规格

    Returns:
        ProductPackagingResult: 单产品包装计算结果
    """
    pkg = find_package(packaging_name)
    if not pkg:
        raise ValueError(f"未找到包装种类: {packaging_name}")

    # 桶数 = ceil(order_qty / net_kg_per_drum)
    drums = math.ceil(quantity_kg / specification_kg)

    # 确定每托盘桶数
    if "1.0*1.0" in pallet_spec:
        drums_per_pallet = pkg.pallet_qty_1x1 or 0
    elif "1.1*1.1" in pallet_spec:
        drums_per_pallet = pkg.pallet_qty_1_1x1_1 or 0
    else:
        drums_per_pallet = 0

    if drums_per_pallet == 0:
        # 编织袋类产品不需要卡板
        full_pallets = 0
        remainder = quantity_kg  # 全是待处理（不打卡板）
        pallets = 0
        drum_tare = drums * pkg.tare_kg
        pallet_tare = 0
        drum_cbm = drums * pkg.cbm
        pallet_cbm = 0
    else:
        full_pallets = drums // drums_per_pallet
        remainder = drums - full_pallets * drums_per_pallet  # 可正可负
        pallets = full_pallets
        pallet = find_pallet(pallet_spec)
        drum_tare = drums * pkg.tare_kg
        pallet_tare = pallets * pallet.weight_kg if pallet else 0
        drum_cbm = drums * pkg.cbm
        pallet_cbm = pallets * pallet.cbm if pallet else 0

    total_volume = drum_cbm + pallet_cbm
    gross_weight = drums * pkg.gross_kg + (pallets * find_pallet(pallet_spec).weight_kg if pallets > 0 and pallet_spec in ["1.0*1.0m", "1.1*1.1m"] else 0)

    return ProductPackagingResult(
        product_name=packaging_name,
        packaging_name=packaging_name,
        specification_kg=specification_kg,
        drums=drums,
        drums_per_pallet=drums_per_pallet,
        pallets=pallets,
        pallet_spec=pallet_spec,
        full_pallets=full_pallets,
        remainder=remainder,
        net_weight_kg=quantity_kg,
        drum_tare_kg=round(drum_tare, 1),
        pallet_tare_kg=round(pallet_tare, 1),
        gross_weight_kg=round(gross_weight, 1),
        drum_cbm=round(drum_cbm, 4),
        pallet_cbm=round(pallet_cbm, 4),
        total_volume_cbm=round(total_volume, 4),
    )


def calculate_order_packaging(products: list[OrderProductInput]) -> OrderPackagingResult:
    """
    订单级别包装汇总计算

    处理逻辑:
    1. 按产品分别计算包装（桶数、卡板数、体积、重量）
    2. 汇总到订单级别，按卡板规格分组输出 pallet_details
    3. 判断货柜适应性(20GP/40HQ)

    Args:
        products: 订单中的产品列表，每个产品包含包装类型、数量、规格等信息

    Returns:
        OrderPackagingResult: 包含汇总结果和各产品明细
    """
    product_details: list[ProductPackagingResult] = []
    total_drums = 0
    total_pallets = 0
    total_net_weight = 0.0
    total_drum_tare = 0.0
    total_pallet_tare = 0.0
    total_drum_cbm = 0.0
    total_pallet_cbm = 0.0

    # 逐产品计算
    for prod in products:
        result = calculate_single_product(
            packaging_name=prod.packaging_name,
            quantity_kg=prod.quantity_kg,
            specification_kg=prod.specification_kg,
            barrel_type=prod.barrel_type,
            pallet_spec=prod.pallet_spec,
        )
        product_details.append(result)
        total_drums += result.drums
        total_pallets += result.pallets
        total_net_weight += result.net_weight_kg
        total_drum_tare += result.drum_tare_kg
        total_pallet_tare += result.pallet_tare_kg
        total_drum_cbm += result.drum_cbm
        total_pallet_cbm += result.pallet_cbm

    total_volume = total_drum_cbm + total_pallet_cbm
    total_weight = total_net_weight + total_drum_tare + total_pallet_tare

    # 按卡板规格分组
    pallet_groups: dict[str, dict] = {}
    for prod_result in product_details:
        if prod_result.pallets > 0:
            spec = prod_result.pallet_spec
            if spec not in pallet_groups:
                pallet_groups[spec] = {"count": 0, "drums": 0, "volume": 0.0, "weight": 0.0}
            pallet_groups[spec]["count"] += prod_result.pallets
            pallet_groups[spec]["drums"] += prod_result.drums
            pallet_groups[spec]["volume"] += prod_result.pallet_cbm
            pallet = find_pallet(spec)
            pallet_groups[spec]["weight"] += prod_result.pallets * (pallet.weight_kg if pallet else 0)

    pallet_details: list[PalletDetail] = []
    for spec, data in pallet_groups.items():
        pallet = find_pallet(spec)
        pallet_details.append(PalletDetail(
            pallet_spec=spec,
            pallet_count=data["count"],
            drums_on_pallets=data["drums"],
            volume_cbm=round(data["volume"], 4),
            weight_kg=round(data["weight"], 1),
        ))

    # 货柜判断
    specs = get_container_specs()
    spec_20gp = specs["20GP"]
    spec_40gp = specs["40GP"]

    fits_20gp = total_volume <= spec_20gp.max_cbm and total_weight <= spec_20gp.max_weight_kg
    fits_40hq = total_volume <= 67.0 and total_weight <= 27000.0  # 40HQ limits

    load_rate_20gp = round(total_volume / spec_20gp.max_cbm * 100, 1) if spec_20gp.max_cbm > 0 else 0
    load_rate_40hq = round(total_volume / 67.0 * 100, 1) if 67.0 > 0 else 0

    if fits_20gp:
        recommended = "20GP"
    elif fits_40hq:
        recommended = "40HQ"
    else:
        recommended = "超限"

    return OrderPackagingResult(
        total_drums=total_drums,
        total_pallets=total_pallets,
        total_volume_cbm=round(total_volume, 3),
        total_weight_kg=round(total_weight, 1),
        total_net_weight_kg=round(total_net_weight, 1),
        pallet_details=pallet_details,
        product_details=product_details,
        container_20gp_fit=fits_20gp,
        container_40hq_fit=fits_40hq,
        recommended=recommended,
        load_rate_20gp=load_rate_20gp,
        load_rate_40hq=load_rate_40hq,
    )


def calculate_remainder_contribution(
    remainder_drums: int,
    packaging_name: str,
    pallet_spec: str,
    mode: str,  # "full_pallet_merge" | "full_pallet_independent" | "no_pallet"
) -> tuple:
    """
    计算余数桶对总体积/总重量的贡献。

    mode:
      - full_pallet_merge:       所有余数合并到1块共享余数板（体积=1块板CBM，重量=板重+各行余数桶皮重）
      - full_pallet_independent: 每个有余数的行各自开1块余数板
      - no_pallet:               无托盘装载，只加余数桶自身体积和毛重
    """
    if remainder_drums <= 0:
        return 0.0, 0.0

    pkg = find_package(packaging_name)
    if not pkg:
        return 0.0, 0.0

    pallet = find_pallet(pallet_spec) if pallet_spec else None

    if mode in ("full_pallet_merge", "full_pallet_independent"):
        extra_volume = pallet.cbm if pallet else 0.0
        extra_weight = (remainder_drums * pkg.tare_kg) + (pallet.weight_kg if pallet else 0.0)
    else:  # no_pallet
        extra_volume = remainder_drums * pkg.cbm
        extra_weight = remainder_drums * pkg.gross_kg  # 毛重，不再是净重

    return round(extra_volume, 4), round(extra_weight, 1)