"""
产品品名中英文对照服务。
程序启动时加载，提供中文->英文、英文->中文双向查询。
"""
import json
from pathlib import Path
from typing import Optional

# 全局缓存
_NAME_MAPPING: list[dict] = []
_CN_TO_EN: dict[str, str] = {}
_EN_TO_CN: dict[str, str] = {}


def load_name_mapping() -> None:
    """启动时调用，加载品名对照表到内存"""
    global _NAME_MAPPING, _CN_TO_EN, _EN_TO_CN

    # 项目根目录 / references / products_name_mapping.json
    # __file__ = backend/app/services/name_mapping_service.py
    # parent.parent.parent.parent = 项目根目录
    project_root = Path(__file__).parent.parent.parent.parent
    mapping_file = project_root / "references" / "products_name_mapping.json"

    if mapping_file.exists():
        with open(mapping_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            _NAME_MAPPING = data.get("mappings", [])
            _CN_TO_EN = {item["cn"]: item["en"] for item in _NAME_MAPPING}
            _EN_TO_CN = {item["en"]: item["cn"] for item in _NAME_MAPPING}
            print(f"[name_mapping] Loaded {len(_NAME_MAPPING)} product name mappings")
    else:
        print(f"[name_mapping] File not found: {mapping_file}")


def get_en_name(cn_name: str) -> Optional[str]:
    """根据中文名查找英文名"""
    return _CN_TO_EN.get(cn_name.strip())


def get_cn_name(en_name: str) -> Optional[str]:
    """根据英文名查找中文名"""
    return _EN_TO_CN.get(en_name.strip())


def get_all_mappings() -> list[dict]:
    """返回所有对照数据"""
    return _NAME_MAPPING


# 启动时自动加载
load_name_mapping()