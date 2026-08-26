"""
国家/港口中英文映射 — PI 目的港解析与报关单证生成共用。

原定义位于 document_service.py，为避免 core→services 反向依赖，抽到 core 层。
"""

import re

from app.database import SessionLocal
from app.models.reference_data import TranslationMapping

# CJK 表意文字 + 中文标点（用于从混合值中剔除中文）
_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\u3000-\u303f]")

# 数据库对照覆盖层：启动时从 translation_mappings 加载
# （mapping_type='destination_city' / 'destination_country'），未命中时回退下方内置字典。
_city_db: dict[str, str] = {}
_country_db: dict[str, str] = {}

# 国家名英文→中文翻译表
COUNTRY_CN_MAP: dict[str, str] = {
    "turkey": "土耳其", "turkiye": "土耳其",
    "china": "中国",
    "india": "印度",
    "indonesia": "印度尼西亚",
    "thailand": "泰国",
    "singapore": "新加坡",
    "malaysia": "马来西亚",
    "vietnam": "越南",
    "bangladesh": "孟加拉国",
    "philippines": "菲律宾",
    "korea": "韩国",
    "japan": "日本",
    "taiwan": "台湾",
    "usa": "美国", "united states": "美国",
    "uk": "英国", "united kingdom": "英国",
    "germany": "德国",
    "france": "法国",
    "netherlands": "荷兰",
    "italy": "意大利",
    "spain": "西班牙",
    "australia": "澳大利亚",
    "russia": "俄罗斯",
    "brazil": "巴西",
    "mexico": "墨西哥",
    "canada": "加拿大",
    "egypt": "埃及",
    "south africa": "南非",
    "nigeria": "尼日利亚",
    "kenya": "肯尼亚",
    "pakistan": "巴基斯坦",
    "sri lanka": "斯里兰卡",
    "myanmar": "缅甸",
    "cambodia": "柬埔寨",
    "laos": "老挝",
    "nepal": "尼泊尔",
    "argentina": "阿根廷",
    "chile": "智利",
    "colombia": "哥伦比亚",
    "peru": "秘鲁",
    "ecuador": "厄瓜多尔",
    "saudi arabia": "沙特阿拉伯",
    "uae": "阿联酋", "united arab emirates": "阿联酋",
    "iran": "伊朗",
    "israel": "以色列",
    "poland": "波兰",
    "ukraine": "乌克兰",
    "belgium": "比利时",
    "switzerland": "瑞士",
    "sweden": "瑞典",
    "norway": "挪威",
    "denmark": "丹麦",
    "portugal": "葡萄牙",
    "greece": "希腊",
    "new zealand": "新西兰",
    "uzbekistan": "乌兹别克斯坦",
    "kazakhstan": "哈萨克斯坦",
    "tajikistan": "塔吉克斯坦",
    "kyrgyzstan": "吉尔吉斯斯坦",
    "turkmenistan": "土库曼斯坦",
    "mongolia": "蒙古",
    "afghanistan": "阿富汗",
}

# 反向映射：国家中文→英文（可能有多个英文名对应同一中文，取第一个）
COUNTRY_EN_REVERSE: dict[str, str] = {v: k for k, v in COUNTRY_CN_MAP.items()}

# 城市/港口名英文→中文翻译表
CITY_CN_MAP: dict[str, str] = {
    "izmit": "伊兹米特", "kocaeli": "科贾埃利",
    "istanbul": "伊斯坦布尔",
    "mersin": "梅尔辛",
    "aliaga": "阿利亚加",
    "ambarlı": "安巴利",
    "jakarta": "雅加达",
    "surabaya": "泗水",
    "tanjung priok": "丹戎不碌",
    "bangkok": "曼谷", "tangkok": "曼谷",
    "laem chabang": "林查班",
    "lat krabang": "拉格拉邦",
    "ho chi minh": "胡志明市", "hcmc": "胡志明市",
    "haiphong": "海防",
    "manila": "马尼拉",
    "busan": "釜山",
    "incheon": "仁川",
    "tokyo": "东京",
    "yokohama": "横滨",
    "osaka": "大阪",
    "shanghai": "上海",
    "ningbo": "宁波",
    "qingdao": "青岛",
    "tianjin": "天津",
    "dalian": "大连",
    "xiamen": "厦门",
    "guangzhou": "广州",
    "shenzhen": "深圳",
    "yantian": "盐田",
    "shekou": "蛇口",
    "chiwan": "赤湾",
    "hong kong": "香港", "hkg": "香港",
    "taipei": "台北",
    "kaohsiung": "高雄",
    "keelung": "基隆",
    "singapore port": "新加坡",
    "port of singapore": "新加坡",
    "colombo": "科伦坡",
    "chennai": "金奈",
    "mumbai": "孟买",
    "nhava sheva": "尼赫鲁港",
    "karachi": "卡拉奇",
    "chittagong": "吉大港",
    "port klang": "巴生港",
    "penang": "槟城",
    "dubai": "迪拜",
    "jebel ali": "杰贝阿里",
    "rikushentity": "六横",
    "los angeles": "洛杉矶",
    "long beach": "长滩",
    "new york": "纽约",
    "rotterdam": "鹿特丹",
    "hamburg": "汉堡",
    "antwerp": "安特卫普",
    "gdansk": "格但斯克",
    "london": "伦敦",
    "felixstowe": "费利克斯托",
    "le havre": "勒阿弗尔",
    "barcelona": "巴塞罗那",
    "valencia": "瓦伦西亚",
    "genoa": "热那亚",
    "auckland": "奥克兰",
    "sydney": "悉尼",
    "melbourne": "墨尔本",
    "durresi": "都拉斯",
    "abidjan": "阿比让",
    "mombasa": "蒙巴萨",
    "lagos": "拉各斯",
    "dakar": "达喀尔",
    "casablanca": "卡萨布兰卡",
    "alexandria": "亚历山大",
    "port said": "塞得港",
    "damietta": "达米埃塔",
    "tashkent": "塔什干",
    "almaty": "阿拉木图",
    "astana": "阿斯塔纳",
    "dushanbe": "杜尚别",
    "bishkek": "比什凯克",
    "ashgabat": "阿什哈巴德",
}

# 城市→国家英文名映射：当 destination 只有城市名时，自动推断所属国家
CITY_TO_COUNTRY: dict[str, str] = {
    # Turkey
    "izmit": "turkey", "kocaeli": "turkey", "istanbul": "turkey",
    "mersin": "turkey", "aliaga": "turkey", "ambarlı": "turkey",
    # Indonesia
    "jakarta": "indonesia", "surabaya": "indonesia", "tanjung priok": "indonesia",
    # Thailand
    "bangkok": "thailand", "tangkok": "thailand", "laem chabang": "thailand",
    "lat krabang": "thailand",
    # Vietnam
    "ho chi minh": "vietnam", "hcmc": "vietnam", "haiphong": "vietnam",
    # Philippines
    "manila": "philippines",
    # Korea
    "busan": "korea", "incheon": "korea",
    # Japan
    "tokyo": "japan", "yokohama": "japan", "osaka": "japan",
    # China
    "shanghai": "china", "ningbo": "china", "qingdao": "china",
    "tianjin": "china", "dalian": "china", "xiamen": "china",
    "guangzhou": "china", "shenzhen": "china", "yantian": "china",
    "shekou": "china", "chiwan": "china",
    # Taiwan
    "hong kong": "china", "hkg": "china",
    "taipei": "taiwan", "kaohsiung": "taiwan", "keelung": "taiwan",
    # Singapore
    "singapore port": "singapore", "port of singapore": "singapore",
    # Sri Lanka
    "colombo": "sri lanka",
    # India
    "chennai": "india", "mumbai": "india", "nhava sheva": "india",
    "ahmedabad": "india",
    # Pakistan
    "karachi": "pakistan",
    # Bangladesh
    "chittagong": "bangladesh",
    # Malaysia
    "port klang": "malaysia", "penang": "malaysia",
    # UAE
    "dubai": "uae", "jebel ali": "uae",
    # USA
    "los angeles": "usa", "long beach": "usa", "new york": "usa",
    # Netherlands
    "rotterdam": "netherlands",
    # Germany
    "hamburg": "germany",
    # Belgium
    "antwerp": "belgium",
    # Poland
    "gdansk": "poland",
    # UK
    "london": "uk", "felixstowe": "uk",
    # France
    "le havre": "france",
    # Spain
    "barcelona": "spain", "valencia": "spain",
    # Italy
    "genoa": "italy",
    # New Zealand
    "auckland": "new zealand",
    # Australia
    "sydney": "australia", "melbourne": "australia",
    # Albania
    "durresi": "albania",
    # Ivory Coast
    "abidjan": "ivory coast",
    # Kenya
    "mombasa": "kenya",
    # Nigeria
    "lagos": "nigeria",
    # Senegal
    "dakar": "senegal",
    # Morocco
    "casablanca": "morocco",
    # Egypt
    "alexandria": "egypt", "port said": "egypt", "damietta": "egypt",
    # Uzbekistan
    "tashkent": "uzbekistan", "kokand": "uzbekistan",
    # Kazakhstan
    "almaty": "kazakhstan", "astana": "kazakhstan",
    # Tajikistan
    "dushanbe": "tajikistan",
    # Kyrgyzstan
    "bishkek": "kyrgyzstan",
    # Turkmenistan
    "ashgabat": "turkmenistan",
    # Mexico
    "cdmx airport": "mexico",
}


def _lookup_city(dest_lower: str) -> str | None:
    """尝试匹配城市名的中文翻译（数据库对照优先，内置字典回退）"""
    if dest_lower in _city_db:
        return _city_db[dest_lower]
    for key, val in _city_db.items():
        if key in dest_lower or dest_lower in key:
            return val
    if dest_lower in CITY_CN_MAP:
        return CITY_CN_MAP[dest_lower]
    for key, val in CITY_CN_MAP.items():
        if key in dest_lower or dest_lower in key:
            return val
    return None


def _lookup_country(dest_lower: str) -> str | None:
    """尝试匹配国家名的中文翻译（数据库对照优先，内置字典回退）"""
    if dest_lower in _country_db:
        return _country_db[dest_lower]
    for key, val in _country_db.items():
        if key in dest_lower or dest_lower in key:
            return val
    if dest_lower in COUNTRY_CN_MAP:
        return COUNTRY_CN_MAP[dest_lower]
    for key, val in COUNTRY_CN_MAP.items():
        if key in dest_lower or dest_lower in key:
            return val
    return None


def _lookup_city_country(city_lower: str) -> str | None:
    """根据城市英文名推断所属国家英文名（用于纯城市名场景）"""
    if city_lower in CITY_TO_COUNTRY:
        return CITY_TO_COUNTRY[city_lower]
    for key, val in CITY_TO_COUNTRY.items():
        if key in city_lower or city_lower in key:
            return val
    return None


def load_destination_mapping() -> None:
    """启动时调用：从 translation_mappings 表加载港口/国家对照到内存，覆盖内置字典。"""
    global _city_db, _country_db
    try:
        db = SessionLocal()
        try:
            _city_db = {
                r.en.strip().lower(): r.cn
                for r in db.query(TranslationMapping).filter_by(mapping_type="destination_city").all()
            }
            _country_db = {
                r.en.strip().lower(): r.cn
                for r in db.query(TranslationMapping).filter_by(mapping_type="destination_country").all()
            }
            print(f"[destination_map] Loaded {len(_city_db)} cities, {len(_country_db)} countries from DB")
        finally:
            db.close()
    except Exception as e:
        print(f"[destination_map] DB 对照加载失败，回退内置字典: {e}")


# 启动时自动加载（表不存在/加载失败时静默回退内置字典）
load_destination_mapping()


def parse_destination(dest: str) -> tuple[str, str]:
    """
    将目的港字段（如 "Izmit,Turkiye"）解析为 (指运港中文, 国家中文)。
    策略：
    1. 按逗号分割，分别匹配城市和国家翻译
    2. 无逗号时尝试整个字符串匹配国家表或城市表
    3. 都匹配不到返回原值
    """
    if not dest:
        return ("", "")

    dest_stripped = dest.strip()

    # 策略1：按逗号分割
    if "," in dest_stripped:
        parts = [p.strip() for p in dest_stripped.split(",", 1)]
        city_part = parts[0]
        country_part = parts[1] if len(parts) > 1 else ""

        city_cn = _lookup_city(city_part.lower())
        country_cn = _lookup_country(country_part.lower())

        # 如果逗号前匹配到国家（如 "Turkey, City" 的反向情况），交换
        if not city_cn and not country_cn:
            # 都匹配不到：尝试反向
            city_cn = _lookup_city(country_part.lower())
            country_cn = _lookup_country(city_part.lower())

        # 部分匹配成功时填充缺失方
        if not city_cn:
            # 城市没匹配到，用原城市名英文
            city_cn = city_part
        if not country_cn:
            # 国家没匹配到，用原国家名英文
            country_cn = country_part

        return (city_cn, country_cn)

    # 策略2：无逗号，尝试整体匹配国家表
    country_cn = _lookup_country(dest_stripped.lower())
    if country_cn:
        return (dest_stripped, country_cn)

    # 策略3：无逗号，尝试整体匹配城市表
    city_cn = _lookup_city(dest_stripped.lower())
    if city_cn:
        # 尝试通过城市推断国家
        country_en = _lookup_city_country(dest_stripped.lower())
        if country_en:
            country_cn = _lookup_country(country_en)
            return (city_cn, country_cn or country_en)
        return (city_cn, dest_stripped)

    # 策略3b：城市名不在翻译表中，但可能在 CITY_TO_COUNTRY 中有映射
    country_en = _lookup_city_country(dest_stripped.lower())
    if country_en:
        country_cn = _lookup_country(country_en)
        return (dest_stripped, country_cn or country_en)

    # 都匹配不到，返回原值
    return (dest_stripped, dest_stripped)


def normalize_destination(dest: str | None) -> str | None:
    """
    规范化目的港：能匹配到中文港口/城市名的返回中文名（含 "KEELUNG基隆" 这类中英混合写法），
    "city,country" 形式分别翻译后用逗号拼接；无法翻译则保留原文。
    例: "KEELUNG基隆" → "基隆", "Izmit,Turkiye" → "伊兹米特,土耳其", "Bogota" → "Bogota"
    """
    if not dest or not dest.strip():
        return dest

    dest_stripped = dest.strip()

    if "," in dest_stripped:
        parts = [p.strip() for p in dest_stripped.split(",", 1)]
        city_cn = _lookup_city(parts[0].lower()) or parts[0]
        country_cn = _lookup_country(parts[1].lower()) or parts[1]
        return f"{city_cn},{country_cn}"

    city_cn = _lookup_city(dest_stripped.lower())
    if city_cn:
        return city_cn

    country_cn = _lookup_country(dest_stripped.lower())
    if country_cn:
        return country_cn

    return dest_stripped


def normalize_destination_source(dest: str | None) -> str | None:
    """
    目的港导入规范化（台账源数据规则）：
    汇入是什么就保留什么；仅当值中英混合时取英文部分（订舱单用英文）。
    例: "KEELUNG基隆" → "KEELUNG", "Izmit,土耳其" → "Izmit",
        "基隆" → "基隆", "Izmit,Turkiye" → "Izmit,Turkiye"
    """
    if not dest or not dest.strip():
        return dest

    stripped = dest.strip()
    has_cjk = bool(_CJK_RE.search(stripped))
    has_latin = bool(re.search(r"[A-Za-z]", stripped))

    # 纯中文或纯英文（或纯数字等）：保留原样
    if not (has_cjk and has_latin):
        return stripped

    # 中英混合：剔除中文，清理残留分隔符
    cleaned = _CJK_RE.sub("", stripped)
    cleaned = re.sub(r"\s*,\s*", ",", cleaned)
    cleaned = re.sub(r",+", ",", cleaned)
    return cleaned.strip(" ,")
