"""
申报要素服务 — 按 HS Code + 报关名称 查找产品的申报要素

数据来源: references/申报要素.json（由 申报要素.xlsx 转换）
"""

import json
import os
import re
from typing import Optional


class CustomsDeclarationService:
    """
    申报要素查询服务（单例）。

    用法:
        svc = CustomsDeclarationService.get_instance()
        # 按 HS Code + 报关名称查询
        entry = svc.lookup("3910000000", "有机硅柔软剂")
        # entry = {"hs_code": "3910000000", "申报名称": "有机硅柔软剂", "申报要素": "用途：...|成分：...|..."}

        # 获取申报要素字符串
        elements_str = svc.get_elements_str("3910000000", "有机硅柔软剂")
        # elements_str = "用途：...|成分：...|..."
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

    def lookup(self, hs_code: str, customs_name: str = "") -> Optional[dict]:
        """
        按 HS Code + 报关名称查找申报要素条目。

        查询策略：
        1. 精确匹配: hs_code|customs_name
        2. 精确匹配 + 数字后缀: hs_code|customs_name_N
        3. 前缀匹配: hs_code|*（任意报关名称）
        """
        if not hs_code:
            return None

        hs = hs_code.strip()
        name = customs_name.strip() if customs_name else ""

        # 1. 精确匹配: hs_code|customs_name
        if name:
            key = hs + "|" + name
            if key in self.data:
                return self.data[key]

        # 2. 精确匹配 + 数字后缀: hs_code|customs_name_N
        if name:
            for suffix in range(2, 10):
                key = hs + "|" + name + "_" + str(suffix)
                if key in self.data:
                    return self.data[key]

        # 3. 前缀匹配: hs_code|*（任意报关名称）
        prefix = hs + "|"
        for key in self.data:
            if key.startswith(prefix):
                return self.data[key]

        # 4. 6位前缀匹配
        if len(hs) >= 6:
            six_prefix = hs[:6] + "|"
            for key in self.data:
                if key.startswith(six_prefix):
                    return self.data[key]

        return None

    def get_elements_str(self, hs_code: str, customs_name: str = "") -> str:
        """
        返回申报要素字符串（用 | 分隔）。

        返回格式:
            "用途：用于纺织工业柔软工艺处理|成分：八甲基环四硅氧烷50%,水50％|是否溶于水：不溶于水|外观：液体|出口享惠情况：受惠|底料来源：新料|签约日期：2025/11/08"
        """
        entry = self.lookup(hs_code, customs_name)
        if entry:
            return entry.get("申报要素", "")
        return ""

    def get_declaration_name(self, hs_code: str, customs_name: str = "") -> Optional[str]:
        """返回申报名称（如：有机硅柔软剂）"""
        entry = self.lookup(hs_code, customs_name)
        if entry:
            return entry.get("申报名称")
        return None

    @staticmethod
    def replace_ingredient(elements_str: str, new_ingredient: str) -> str:
        """
        替换申报要素字符串中的"成分"字段。

        参数:
            elements_str: 原始申报要素字符串
            new_ingredient: 新的成分值

        返回:
            替换后的字符串
        """
        if not elements_str:
            return new_ingredient if new_ingredient else ""

        # 匹配 成分：xxx 或 成份：xxx（冒号后面到下一个 | 或字符串结尾）
        pattern = r'(成分|成份)：[^|]*'
        replacement = r'\g<1>：' + new_ingredient

        result = re.sub(pattern, replacement, elements_str)
        return result
