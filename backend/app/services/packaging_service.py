"""
包装计算服务 - 从数据库加载包装规格，计算桶数/托数/CBM/毛重/货柜判断
"""
import math
from dataclasses import dataclass, field
from typing import Optional

from app.database import SessionLocal
from app.models.order import PackagingType
from app.models.reference_data import Pallet, ContainerSpec as ContainerSpecModel


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
    remainder: int = 0  # 尾板件数（仅展示，托数已含尾板）


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
    actual_fill_kg: Optional[float] = None  # 每桶实际装入量，None时用specification_kg


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
    """从数据库加载包装规格，返回与 packaging_data.json 相同的结构"""
    db = SessionLocal()
    try:
        packages = [
            {
                "name": p.name,
                "dims": p.dims,
                "cbm": p.cbm,
                "tare_kg": p.tare_kg,
                "gross_kg": p.gross_kg,
                "net_kg": p.net_kg,
                "barrel_type": p.barrel_type,
                "is_palletizable": bool(p.is_palletizable),
                "no_pallet_qty": p.no_pallet_qty,
                "pallet_qty_1x1": p.pallet_qty_1x1,
                "pallet_qty_1_1x1_1": p.pallet_qty_1_1x1_1,
            }
            for p in db.query(PackagingType).all()
        ]
        pallets = [
            {"name": p.name, "dims": p.dims, "weight_kg": p.weight_kg, "cbm": p.cbm}
            for p in db.query(Pallet).all()
        ]
        specs = {s.name: s for s in db.query(ContainerSpecModel).all()}
        return {
            "packages": packages,
            "pallets": pallets,
            "container_20gp": {
                "max_cbm": specs["20GP"].max_cbm,
                "max_weight_kg": specs["20GP"].max_weight_kg,
            },
            "container_40gp": {
                "max_cbm": specs["40GP"].max_cbm,
                "max_weight_kg": specs["40GP"].max_weight_kg,
            },
        }
    finally:
        db.close()


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


def _fill_kg(pkg_net: float, actual_fill_kg: Optional[float]) -> float:
    if actual_fill_kg is not None and actual_fill_kg > 0:
        return float(actual_fill_kg)
    return float(pkg_net)


def _packages(quantity_kg: float, fill_kg: float) -> int:
    if quantity_kg <= 0 or fill_kg <= 0:
        return 0
    return math.ceil(quantity_kg / fill_kg)


def _pallets_for(drums: int, drums_per_pallet: int) -> tuple[int, int, int]:
    """返回 (总托数含尾板, 整板数, 尾板件数)"""
    if drums <= 0 or drums_per_pallet <= 0:
        return 0, 0, 0
    full = drums // drums_per_pallet
    remainder = drums % drums_per_pallet
    total = full + (1 if remainder else 0)
    return total, full, remainder


def calculate(
    packaging_name: str,
    order_qty_kg: float,
    use_pallet: bool = False,
    pallet_name: Optional[str] = None,
    actual_fill_kg: Optional[float] = None,
    pallets_override: Optional[int] = None,
) -> PackingResult:
    """
    核心计算（全系统唯一公式）

        fill     = actual_fill_kg ?? 标称净重
        packages = ceil(qty / fill)
        net      = qty
        pallets  = ceil(packages / 每板件数)   # 可被 pallets_override 覆盖
        gross    = net + packages*tare + pallets*托重
        volume   = packages*桶CBM + pallets*托CBM
    """
    pkg = find_package(packaging_name)
    if not pkg:
        raise ValueError(f"未找到包装种类: {packaging_name}")

    fill_kg = _fill_kg(pkg.net_kg, actual_fill_kg)
    drums = _packages(order_qty_kg, fill_kg)
    net = float(order_qty_kg or 0)
    drum_tare = drums * pkg.tare_kg

    if not use_pallet:
        pallets = 0
        drums_per_pallet = 0
        pallet_type = None
        full_pallets = 0
        remainder_val = 0
        pallet_tare = 0.0
        pallet_cbm = 0.0
    else:
        if not pallet_name:
            raise ValueError("use_pallet=True 时必须指定 pallet_name")
        pallet = find_pallet(pallet_name)
        if not pallet:
            raise ValueError(f"未找到托盘种类: {pallet_name}")

        if "1.0*1.0" in pallet_name:
            drums_per_pallet = pkg.pallet_qty_1x1 or 0
        elif "1.1*1.1" in pallet_name:
            drums_per_pallet = pkg.pallet_qty_1_1x1_1 or 0
        else:
            drums_per_pallet = 0

        if drums_per_pallet == 0:
            raise ValueError(f"{packaging_name} 无法使用 {pallet_name} 打卡板")

        auto_pallets, full_pallets, remainder_val = _pallets_for(drums, drums_per_pallet)
        pallets = auto_pallets if pallets_override is None else max(0, int(pallets_override))
        pallet_type = pallet_name
        pallet_tare = pallets * pallet.weight_kg
        pallet_cbm = pallets * pallet.cbm

    total_cbm = drums * pkg.cbm + pallet_cbm
    # 毛重 = 净含量 + 桶皮 + 托盘
    total_weight = net + drum_tare + pallet_tare

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
        full_pallets=full_pallets if use_pallet else 0,
        remainder=remainder_val if use_pallet else 0,
    )


def calculate_all_schemes(
    packaging_name: str,
    order_qty_kg: float,
    actual_fill_kg: Optional[float] = None,
) -> list[PackingResult]:
    """
    计算所有可用方案（不打卡板 + 两种托盘）
    用于展示多个方案供用户选择
    """
    results = []

    # 不打卡板
    try:
        r = calculate(packaging_name, order_qty_kg, use_pallet=False, actual_fill_kg=actual_fill_kg)
        results.append(r)
    except Exception:
        pass

    # 打卡板（1.0*1.0 和 1.1*1.1）
    for pallet_name in ["1.0*1.0m", "1.1*1.1m"]:
        try:
            r = calculate(packaging_name, order_qty_kg, use_pallet=True, pallet_name=pallet_name, actual_fill_kg=actual_fill_kg)
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
    actual_fill_kg: Optional[float] = None,
    pallets_override: Optional[int] = None,
) -> ProductPackagingResult:
    """
    单产品包装：packages=ceil(qty/fill)，pallets=ceil(packages/cap)，
    gross=qty+packages*tare+pallets*托重，volume=packages*cbm+pallets*托cbm
    """
    pkg = find_package(packaging_name)
    if not pkg:
        raise ValueError(f"未找到包装种类: {packaging_name}")

    fill_kg = _fill_kg(specification_kg or pkg.net_kg, actual_fill_kg)
    drums = _packages(quantity_kg, fill_kg)
    net = float(quantity_kg or 0)
    drum_tare = drums * pkg.tare_kg
    drum_cbm = drums * pkg.cbm

    if not pallet_spec or not pkg.is_palletizable:
        return ProductPackagingResult(
            product_name=packaging_name,
            packaging_name=packaging_name,
            specification_kg=specification_kg,
            drums=drums,
            drums_per_pallet=0,
            pallets=0,
            pallet_spec="",
            full_pallets=0,
            remainder=0,
            net_weight_kg=net,
            drum_tare_kg=round(drum_tare, 1),
            pallet_tare_kg=0,
            gross_weight_kg=round(net + drum_tare, 1),
            drum_cbm=round(drum_cbm, 4),
            pallet_cbm=0,
            total_volume_cbm=round(drum_cbm, 4),
        )

    if "1.0*1.0" in pallet_spec:
        drums_per_pallet = pkg.pallet_qty_1x1 or 0
    elif "1.1*1.1" in pallet_spec:
        drums_per_pallet = pkg.pallet_qty_1_1x1_1 or 0
    else:
        drums_per_pallet = 0

    if drums_per_pallet == 0:
        return ProductPackagingResult(
            product_name=packaging_name,
            packaging_name=packaging_name,
            specification_kg=specification_kg,
            drums=drums,
            drums_per_pallet=0,
            pallets=0,
            pallet_spec=pallet_spec,
            full_pallets=0,
            remainder=0,
            net_weight_kg=net,
            drum_tare_kg=round(drum_tare, 1),
            pallet_tare_kg=0,
            gross_weight_kg=round(net + drum_tare, 1),
            drum_cbm=round(drum_cbm, 4),
            pallet_cbm=0,
            total_volume_cbm=round(drum_cbm, 4),
        )

    auto_pallets, full_pallets, remainder = _pallets_for(drums, drums_per_pallet)
    pallets = auto_pallets if pallets_override is None else max(0, int(pallets_override))
    pallet = find_pallet(pallet_spec)
    pallet_tare = pallets * pallet.weight_kg if pallet else 0
    pallet_cbm = pallets * pallet.cbm if pallet else 0
    total_volume = drum_cbm + pallet_cbm
    # 毛重 = 净含量 + 桶皮 + 托盘
    gross_weight = net + drum_tare + pallet_tare

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
        net_weight_kg=net,
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
            actual_fill_kg=prod.actual_fill_kg,
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
    # 毛重 = 净含量 + 桶皮 + 托盘（与单品 gross_weight_kg 同源）
    total_weight = total_net_weight + total_drum_tare + total_pallet_tare

    # 按卡板规格分组
    pallet_groups: dict[str, dict] = {}
    for prod_result in product_details:
        if prod_result.pallets > 0 and prod_result.pallet_spec:
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
    仅用于「合板」场景：把未计入行托数的尾板合并时的额外托贡献。
    行上的 gross/volume 已含全部件数的桶皮/桶体积，这里**不得**再加桶皮。

    mode:
      - full_pallet_merge:       合并尾板 → +N 块托的体积/托重
      - full_pallet_independent: 每行独立尾板 → +1 块托（若行托数未含）
      - no_pallet:               无额外贡献（货载体积毛重已在行内）
    """
    if remainder_drums <= 0 or mode == "no_pallet":
        return 0.0, 0.0

    pallet = find_pallet(pallet_spec) if pallet_spec else None
    if not pallet:
        return 0.0, 0.0

    if mode == "full_pallet_independent":
        extra_volume = pallet.cbm
        extra_weight = pallet.weight_kg
    else:  # full_pallet_merge 由调用方传入合并后的托数语义：1 次调用算 1 组
        extra_volume = pallet.cbm
        extra_weight = pallet.weight_kg

    return round(extra_volume, 4), round(extra_weight, 1)