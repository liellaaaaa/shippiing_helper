"""
包装计算服务 - 从 references/packaging_data.json 加载包装规格，计算桶数/托数/CBM/毛重/货柜判断
"""
import os
import math
import json
from dataclasses import dataclass
from typing import Optional


PACKAGING_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "references", "packaging_data.json")


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

        pallets = math.ceil(drums / drums_per_pallet)
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