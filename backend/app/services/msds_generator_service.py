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
        """
        # 直接用 Document 解析
        doc = Document(file_path)

        # 1. 提取产品名称（从段落中找"产品名称："）
        product_name = ""
        for para in doc.paragraphs:
            if "产品名称：" in para.text:
                product_name = para.text.split("产品名称：")[-1].strip()
                break

        # 2. 提取成分表格（直接访问 docx table 对象）
        composition = []
        for table in doc.tables:
            if table.rows:
                first_row_text = "".join(c.text for c in table.rows[0].cells)
                # 检查是否是成分表格（表头包含"组分"或"成分"）
                if "组分" in first_row_text or "成分" in first_row_text:
                    for row in table.rows[1:]:  # 跳过表头
                        if len(row.cells) >= 3:
                            composition.append({
                                "component_cn": row.cells[0].text.strip(),
                                "cas": row.cells[1].text.strip(),
                                "percentage": row.cells[2].text.strip(),
                            })
                    break

        # 3. 提取理化特性（从段落中解析 key-value）
        physicochemical = {}
        import re
        for para in doc.paragraphs:
            text = para.text
            if "外观与性状：" in text:
                physicochemical["physical_form"] = text.split("外观与性状：")[-1].strip()
            elif "离子性：" in text:
                physicochemical["ion_type"] = text.split("离子性：")[-1].strip()
            elif "离子型：" in text:
                physicochemical["ion_type"] = text.split("离子型：")[-1].strip()
            elif re.search(r'[pP][Hh][值]?[:：]\s*([\d±.]+)', text):
                m = re.search(r'[pP][Hh][值]?[:：]\s*([\d±.]+)', text)
                if m:
                    physicochemical["ph"] = m.group(1)
            elif "熔点：" in text:
                physicochemical["melting_point"] = text.split("：")[-1].strip()
            elif "沸点" in text and "：" in text:
                physicochemical["boiling_point"] = text.split("：")[-1].strip()
            elif "相对密度：" in text:
                physicochemical["density"] = text.split("相对密度：")[-1].strip()
            elif "闪点：" in text:
                physicochemical["flash_point"] = text.split("闪点：")[-1].strip()
            elif "溶解性：" in text:
                physicochemical["solubility"] = text.split("溶解性：")[-1].strip()

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
        """更新文档中的产品名称。保留原始段落格式和字体属性。"""
        from docx.shared import Pt, Pt as PtType
        from copy import copy

        for para in doc.paragraphs:
            if "产品名称：" in para.text:
                full_text = para.text
                idx = full_text.find("产品名称：")
                prefix = full_text[:idx]

                # 保存原始段落格式（line_spacing 等）
                pf = para.paragraph_format
                saved_line_spacing = pf.line_spacing
                saved_first_indent = pf.first_line_indent
                saved_left_indent = pf.left_indent

                # 保存原始 run 的字体属性（取第一个 run 的字体）
                first_run = para.runs[0] if para.runs else None
                orig_font_name = first_run.font.name if first_run else None
                orig_font_size = first_run.font.size if first_run else None

                # 清空所有 run 并重建
                for run in para.runs:
                    run.text = ""
                para.clear()

                new_run = para.add_run(prefix + f"产品名称：{new_name}")
                # 保持与原始一致的字体（继承而非显式设置）
                if orig_font_name:
                    new_run.font.name = orig_font_name
                elif orig_font_size:
                    # 原始有字号但无显式字体名，保持字号继承
                    new_run.font.size = orig_font_size

                # 恢复段落格式
                pf.line_spacing = saved_line_spacing
                pf.first_line_indent = saved_first_indent
                pf.left_indent = saved_left_indent
                break

    def _update_composition_table(self, doc: Document, composition: list):
        """更新成分表格，保留原有字体。"""
        from docx.shared import Pt

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

        # 获取原始单元格的字体样式（从第一行数据行获取）
        sample_row = comp_table.rows[1] if len(comp_table.rows) > 1 else None
        sample_fonts = []
        if sample_row and len(sample_row.cells) >= 3:
            for cell in sample_row.cells:
                if cell.paragraphs and cell.paragraphs[0].runs:
                    first_run = cell.paragraphs[0].runs[0]
                    sample_fonts.append({
                        "name": first_run.font.name,
                        "size": first_run.font.size,
                    })
                else:
                    sample_fonts.append({"name": None, "size": None})

        # 更新每一行
        for i, item in enumerate(composition):
            row_idx = i + 1  # 跳过表头
            if row_idx >= len(comp_table.rows):
                break

            row = comp_table.rows[row_idx]
            if len(row.cells) >= 3:
                new_values = [
                    item.get("component_cn", ""),
                    item.get("cas", ""),
                    item.get("percentage", ""),
                ]
                for col_idx, new_val in enumerate(new_values):
                    if col_idx >= len(row.cells):
                        continue
                    cell = row.cells[col_idx]
                    # 直接修改现有 run 的文本，保留字体
                    if cell.paragraphs and cell.paragraphs[0].runs:
                        # 只修改第一个 run 的文本，清空其余 run
                        para = cell.paragraphs[0]
                        for r_idx, run in enumerate(para.runs):
                            if r_idx == 0:
                                run.text = new_val
                            else:
                                run.text = ""
                        # 如果没有 run，创建一个
                        if not para.runs:
                            new_run = para.add_run(new_val)
                            if col_idx < len(sample_fonts) and sample_fonts[col_idx]["name"]:
                                new_run.font.name = sample_fonts[col_idx]["name"]
                            if col_idx < len(sample_fonts) and sample_fonts[col_idx]["size"]:
                                new_run.font.size = sample_fonts[col_idx]["size"]
                    else:
                        # 没有段落，创建一个
                        para = cell.paragraphs[0] if cell.paragraphs else cell.add_paragraph()
                        new_run = para.add_run(new_val)
                        if col_idx < len(sample_fonts) and sample_fonts[col_idx]["name"]:
                            new_run.font.name = sample_fonts[col_idx]["name"]
                        if col_idx < len(sample_fonts) and sample_fonts[col_idx]["size"]:
                            new_run.font.size = sample_fonts[col_idx]["size"]

    def _update_physicochemical(self, doc: Document, physicochemical: dict):
        """
        更新理化特性，保留原始段落格式和字体。
        格式：{"外观与性状": "蓝色透明液体", "离子性": "阴离子", "PH值": "3±1", ...}
        """
        from docx.shared import Pt

        # 映射前端字段名到文档中实际存在的 key
        key_map = {
            'appearance': '外观与性状',
            'ion_type': '离子性',
            'ph': 'PH值',
            'melting_point': '熔点',
            'boiling_point': '沸点',
            'density': '相对密度',
            'flash_point': '闪点',
            'solubility': '溶解性',
        }

        for para in doc.paragraphs:
            text = para.text
            for field_key, value in physicochemical.items():
                if not value:
                    continue
                # 找到文档中对应的 key
                doc_key = key_map.get(field_key, field_key)
                # 大小写敏感匹配
                if f"{doc_key}：" not in text:
                    continue

                # 找到冒号位置（用 doc_key 本身在文本中的位置）
                colon_idx = text.find(doc_key)
                if colon_idx == -1:
                    continue
                colon_idx = text.find("：", colon_idx)
                if colon_idx == -1:
                    continue
                prefix = text[:colon_idx + 1]  # 保留原始 key 大小写
                new_text = f"{prefix}{value}"

                # 保存原始段落格式
                pf = para.paragraph_format
                saved_line_spacing = pf.line_spacing
                saved_first_indent = pf.first_line_indent
                saved_left_indent = pf.left_indent

                # 保存原始 run 的字体属性
                first_run = para.runs[0] if para.runs else None
                orig_font_name = first_run.font.name if first_run else None
                orig_font_size = first_run.font.size if first_run else None

                # 清空所有 run 并重建
                for run in para.runs:
                    run.text = ""
                para.clear()

                new_run = para.add_run(new_text)
                # 保持与原始一致的字体
                if orig_font_name:
                    new_run.font.name = orig_font_name
                elif orig_font_size:
                    new_run.font.size = orig_font_size

                # 恢复段落格式
                pf.line_spacing = saved_line_spacing
                pf.first_line_indent = saved_first_indent
                pf.left_indent = saved_left_indent
                break
