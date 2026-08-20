"""出货抬头 → 英文 SHIPPER 映射表（含公司名+地址+电话）"""

# 完整 SHIPPER 格式：公司名 + 地址 + TEL/FAX
HONGHAO_FULL = (
    "HONGHAO CHEMICAL CO., LTD.\n"
    "COMPREHENSIVE BUILDING,NO.13 CHUANGXIN\n"
    "ROAD,JIANGGU FINE CHEMICAL INDUSTRIAL\n"
    "AREA,JIANGGU,SIHUI,GUANGDONG,CHINA\n"
    "TEL:0086-758-3267663 FAX:0086-758-3115313"
)

MINHAO_FULL = (
    "GUANGZHOU MINHAO NEW MATERIAL CO. LTD.\n"
    "ROOM 202,NO.12 SHIHU SHISI ROAD,DAYUAN STREET,\n"
    "BAIYUN DISTRICT,GUANGZHOU,GUANGDONG,CHINA."
)

# 中文抬头 → 完整 SHIPPER
SHIPPER_MAP: dict[str, str] = {
    "宏昊": HONGHAO_FULL,
    "宏昊化工": HONGHAO_FULL,
    "广东宏昊": HONGHAO_FULL,
    "广东宏昊化工": HONGHAO_FULL,
    "民浩": MINHAO_FULL,
    "民浩化工": MINHAO_FULL,
    "广州民浩": MINHAO_FULL,
    "广州民浩新材料": MINHAO_FULL,
}

# 所有预设 SHIPPER（用于前端下拉选项）
ALL_SHIPPERS = [HONGHAO_FULL, MINHAO_FULL]

# 默认 SHIPPER（当 shipment_title 未匹配时使用）
DEFAULT_SHIPPER = HONGHAO_FULL


def get_shipper(shipment_title: str | None) -> str:
    """根据出货抬头返回完整英文 SHIPPER（含地址+电话），未匹配时返回默认值"""
    if not shipment_title:
        return DEFAULT_SHIPPER
    title = shipment_title.strip()
    # 精确匹配
    if title in SHIPPER_MAP:
        return SHIPPER_MAP[title]
    # 模糊匹配（包含关键字）
    for key, value in SHIPPER_MAP.items():
        if key in title or title in key:
            return value
    return DEFAULT_SHIPPER
