"""
MSDS 自动化生成服务。

从 customs_codes.json 获取产品数据，从旧 MSDS 文件生成新 MSDS。
"""
import json
import re
import os
from pathlib import Path
from typing import Optional
from docx import Document
from docx.shared import Pt, RGBColor
from io import BytesIO

from app.core.config import CUSTOMS_CODES_JSON, MSDS_DIR


# 项目根目录
ROOT = Path(__file__).parent.parent.parent.parent
INGREDIENT_MAPPING_JSON = str(ROOT / "references" / "ingredient_mapping.json")
APPEARANCE_COLOR_MAPPING_JSON = str(ROOT / "references" / "appearance_color_mapping.json")
PRODUCTS_NAME_MAPPING_JSON = str(ROOT / "references" / "products_name_mapping.json")


class MSDSGeneratorService:
    def __init__(self):
        self._customs_codes: list[dict] = []
        self._ingredient_map: list[dict] = []
        self._appearance_map: dict[str, str] = {}
        self._products_name_map: dict[str, str] = {}
        self._load_data()

    def _load_data(self):
        """加载所有数据文件"""
        # 加载 customs_codes.json
        if Path(CUSTOMS_CODES_JSON).exists():
            with open(CUSTOMS_CODES_JSON, "r", encoding="utf-8") as f:
                self._customs_codes = json.load(f)

        # 加载 ingredient_mapping.json
        if Path(INGREDIENT_MAPPING_JSON).exists():
            with open(INGREDIENT_MAPPING_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._ingredient_map = data.get("mappings", [])

        # 加载 appearance_color_mapping.json
        if Path(APPEARANCE_COLOR_MAPPING_JSON).exists():
            with open(APPEARANCE_COLOR_MAPPING_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("mappings", []):
                    self._appearance_map[item["cn"]] = item["en"]

        # 加载 products_name_mapping.json
        if Path(PRODUCTS_NAME_MAPPING_JSON).exists():
            with open(PRODUCTS_NAME_MAPPING_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("mappings", []):
                    self._products_name_map[item["cn"]] = item["en"]

    def parse_msds_file(self, file_path: str) -> dict:
        """
        从旧 MSDS 文件解析出产品信息、成分、理化特性。
        直接从文档解析，不查 customs_codes.json。
        返回：{
            "product_name": str,
            "composition": [{"component_cn": "", "cas": "", "percentage": ""}, ...],
            "physicochemical": {"physical_form": "", "ion_type": "", "ph": "", ...},
        }
        """
        from app.services.msds_service import MSDSService
        msds_svc = MSDSService()

        # 提取文本
        text = msds_svc.extract_text(file_path)

        # 提取成分表格
        composition = msds_svc.extract_composition_table(text)

        # 提取理化特性
        physicochemical = msds_svc.extract_physical_props(text)

        # 从文本中提取产品名称（找"产品名称："开头的行）
        product_name = ""
        for line in text.split("\n"):
            if "产品名称：" in line:
                product_name = line.split("产品名称：")[-1].strip()
                break

        return {
            "product_name": product_name,
            "composition": composition,
            "physicochemical": physicochemical,
        }

    def search_msds(self, keyword: str) -> list[dict]:
        """
        从 references/MSDS/ 搜索匹配的旧 MSDS 文件。
        返回：[{"name": "xxx.docx", "path": "..."}, ...]
        """
        if not keyword or len(keyword) < 1:
            return []

        keyword_lower = keyword.lower()
        results = []
        msds_path = Path(MSDS_DIR)

        if not msds_path.exists():
            return results

        for f in msds_path.iterdir():
            if f.is_file() and keyword_lower in f.name.lower():
                # 跳过临时文件和 test 文件
                name_lower = f.name.lower()
                if name_lower.startswith('~$') or name_lower.startswith('test'):
                    continue
                results.append({
                    "name": f.name,
                    "path": str(f)
                })

        return results

    def get_product_data(self, product_name: str) -> Optional[dict]:
        """
        从 customs_codes.json 获取产品数据（按 customs_name 匹配）。
        返回：{"internal_code": "", "customs_name": "", "components": "", "product_appearance": "", ...}
        """
        if not product_name:
            return None

        # 精确匹配 customs_name
        for item in self._customs_codes:
            if item.get("customs_name", "") == product_name:
                return item

        # 模糊匹配
        product_name_lower = product_name.lower()
        for item in self._customs_codes:
            if product_name_lower in item.get("customs_name", "").lower():
                return item

        return None

    def search_products(self, keyword: str) -> list[dict]:
        """
        从 customs_codes.json 搜索产品。
        返回匹配的產品列表（去重）。
        """
        if not keyword or len(keyword) < 1:
            return []

        keyword_lower = keyword.lower()
        results = []
        seen = set()

        for item in self._customs_codes:
            name = item.get("customs_name", "")
            if keyword_lower in name.lower():
                if name not in seen:
                    seen.add(name)
                    results.append({
                        "customs_name": name,
                        "internal_code": item.get("internal_code", ""),
                        "product_appearance": item.get("product_appearance", ""),
                        "components": item.get("components", ""),
                    })

        return results

    def parse_components(self, components_str: str) -> list[dict]:
        """
        解析 components 字段，生成成分表格数据。
        输入示例："柔软吸湿排汗整理剂9016-88-0：90％+水：10％"
        返回：[{"component_cn": "", "cas": "", "percentage": "", "verified": bool}, ...]
        """
        if not components_str:
            return []

        results = []
        # 按 + 拆分多个组分
        parts = components_str.split("+")

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # 按 ：或 : 拆分成分名和含量
            # 格式可能是 "成分名CAS号：含量%" 或 "成分名：含量%"
            # CAS号格式：连续数字加连字符，如 9016-88-0

            # 先尝试提取 CAS 号
            cas_match = re.search(r"(\d{4,7}-\d{2}-\d)", part)
            cas = ""
            component_name = part

            if cas_match:
                cas = cas_match.group(1)
                # 去掉 CAS 号部分，得到成分名
                component_name = part[:cas_match.start()].strip()

            # 提取含量（最后一个出现的百分比）
            pct_match = re.search(r"(\d+(?:\.\d+)?)\s*％", part)
            percentage = ""
            if pct_match:
                percentage = pct_match.group(1) + "%"

            # 验证成分名是否在对照表中
            verified = self._verify_ingredient(component_name)

            results.append({
                "component_cn": component_name,
                "cas": cas,
                "percentage": percentage,
                "verified": verified,
            })

        return results

    def _verify_ingredient(self, ingredient_cn: str) -> bool:
        """验证成分名是否在 ingredient_mapping 中"""
        if not ingredient_cn or not self._ingredient_map:
            return False

        for item in self._ingredient_map:
            if ingredient_cn in item.get("cn_names", []):
                return True
        return False

    def translate_ingredient(self, ingredient_cn: str) -> Optional[str]:
        """翻译成分名为英文"""
        for item in self._ingredient_map:
            if ingredient_cn in item.get("cn_names", []):
                en_names = item.get("en_names", [])
                if en_names:
                    return en_names[0]
        return None

    def translate_appearance(self, appearance_cn: str) -> Optional[str]:
        """翻译外观描述为英文"""
        return self._appearance_map.get(appearance_cn)

    def translate_product_name(self, product_name_cn: str) -> Optional[str]:
        """翻译产品名为英文"""
        return self._products_name_map.get(product_name_cn)

    def generate_msds(
        self,
        msds_file_path: str,
        product_data: dict,
        edits: dict
    ) -> tuple[bytes, str]:
        """
        基于旧 MSDS 文件，应用编辑内容，生成新 MSDS docx。

        Args:
            msds_file_path: 旧 MSDS 文件路径
            product_data: 从 customs_codes.json 获取的产品数据
            edits: 用户编辑的内容 {
                "product_name": str,
                "composition": [{"component_cn": "", "cas": "", "percentage": ""}, ...],
                "physicochemical": {"外观与性状": "", "离子性": "", ...}
            }

        Returns:
            (docx_bytes, doc_key)
        """
        # 读取旧 MSDS 文件
        doc = Document(msds_file_path)

        # 1. 修改产品名称（如果编辑了）
        if edits.get("product_name"):
            self._update_product_name(doc, edits["product_name"])

        # 2. 修改成分表格
        if edits.get("composition"):
            self._update_composition_table(doc, edits["composition"])

        # 3. 修改理化特性
        if edits.get("physicochemical"):
            self._update_physicochemical(doc, edits["physicochemical"])

        # 保存到 BytesIO
        buf = BytesIO()
        doc.save(buf)
        content = buf.getvalue()

        # 生成 doc_key
        import time
        product_name = edits.get("product_name", product_data.get("customs_name", "unknown"))
        doc_key = f"msds_{product_name}_{int(time.time())}"

        return content, doc_key

    def _update_product_name(self, doc: Document, new_name: str):
        """更新文档中的产品名称"""
        for para in doc.paragraphs:
            if "产品名称：" in para.text:
                # 替换整行
                for run in para.runs:
                    if "产品名称：" in run.text:
                        run.text = run.text.replace(
                            run.text.split("产品名称：")[1].strip(), new_name
                        )
                        # 只改第一个
                        break
                break

        # 也更新文档标题（通常是第一个段落）
        if doc.paragraphs:
            first_para = doc.paragraphs[0]
            if "化学品安全资料说明书" in first_para.text:
                # 标题不变，但第二个段落是产品名
                if len(doc.paragraphs) > 1 and doc.paragraphs[1].text.strip():
                    # 替换第二段
                    pass

    def _update_composition_table(self, doc: Document, composition: list):
        """更新成分表格"""
        tables = doc.tables
        if not tables:
            return

        # 找到成分表格（第一行包含"组分"或"成分"）
        comp_table = None
        for table in tables:
            if table.rows:
                first_row_text = "".join(c.text for c in table.rows[0].cells)
                if "组分" in first_row_text or "成分" in first_row_text:
                    comp_table = table
                    break

        if not comp_table:
            return

        # 更新每一行
        for i, item in enumerate(composition):
            row_idx = i + 1  # 跳过表头
            if row_idx >= len(comp_table.rows):
                break

            row = comp_table.rows[row_idx]
            if len(row.cells) >= 3:
                row.cells[0].text = item.get("component_cn", "")
                row.cells[1].text = item.get("cas", "")
                row.cells[2].text = item.get("percentage", "")

    def _update_physicochemical(self, doc: Document, physicochemical: dict):
        """
        更新理化特性。
        格式：{"外观与性状": "蓝色透明液体", "离子性": "阴离子", "PH值": "3±1", ...}
        """
        for para in doc.paragraphs:
            text = para.text
            for key, value in physicochemical.items():
                if not value:  # 跳过空值
                    continue
                if key in text:
                    # 找到对应的行，替换值
                    # 格式："外观与性状：蓝色透明液体"
                    import re
                    pattern = rf"({re.escape(key)}[：:]\s*)([^\n]+)"
                    match = re.search(pattern, text)
                    if match:
                        # 替换冒号后面的值
                        old_value = match.group(2)
                        new_text = text.replace(old_value, value, 1)
                        # 重建 paragraph runs
                        if para.runs:
                            first_run_text = para.runs[0].text
                            para.runs[0].text = first_run_text.replace(text, new_text)
                        break
