"""
申报要素服务 — 按 HS Code 查找产品的申报要素（用途/成分/是否溶于水/外观/出口享惠情况等）

数据来源: references/申报要素.json（由 申报要素.xlsx 转换）
"""

import json
import os
from typing import Optional


class CustomsDeclarationService:
    """
    申报要素查询服务（单例）。

    用法:
        svc = CustomsDeclarationService.get_instance()
        entry = svc.lookup("3910000000")
        # entry = {"申报名称": "有机硅柔软剂", "申报要素": {"用途": "...", "成分": "...", ...}}
    """

    _instance: Optional["CustomsDeclarationService"] = None

    def __init__(self, json_path: str):
        self.json_path = json_path
        with open(json_path, encoding="utf-8") as f:
            self.data: dict[str, dict] = json.load(f)

    @classmethod
    def get_instance(cls, json_path: Optional[str] = None) -> "CustomsDeclarationService":
        if cls._instance is None:
            if json_path is None:
                base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
                json_path = os.path.join(base, "references", "申报要素.json")
            cls._instance = cls(json_path)
        return cls._instance

    @classmethod
    def reset(cls):
        """清除缓存实例，下次 get_instance() 会重新加载 JSON。"""
        cls._instance = None

    def lookup(self, hs_code: str) -> Optional[dict]:
        """
        按 HS Code（前6位或完整10位）查找申报要素条目。

        优先精确匹配10位，再匹配前6位。
        """
        if not hs_code:
            return None

        hs = hs_code.strip()
        # 精确匹配
        if hs in self.data:
            return self.data[hs]

        # 6位前缀匹配
        if len(hs) >= 6:
            prefix = hs[:6]
            for key in self.data:
                if key.startswith(prefix):
                    return self.data[key]

        return None

    def get_elements(self, hs_code: str) -> dict[str, str]:
        """
        直接返回申报要素字典，方便填充模板。

        返回结构:
            {
              "用途": "用于纺织工业柔软工艺处理",
              "成分": "八甲基环四硅氧烷50%,水50％",
              "是否溶于水": "不溶于水",
              "外观": "液体",
              "出口享惠情况": "受惠",
              ...
            }
        """
        entry = self.lookup(hs_code)
        if entry:
            return entry.get("申报要素", {})
        return {}

    def get_declaration_name(self, hs_code: str) -> Optional[str]:
        """返回申报名称（如：有机硅柔软剂）"""
        entry = self.lookup(hs_code)
        if entry:
            return entry.get("申报名称")
        return None
