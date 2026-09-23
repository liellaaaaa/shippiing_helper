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
