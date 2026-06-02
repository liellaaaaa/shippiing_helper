"""
Transport Service - 运输鉴定报告 PDF 字段提取
"""
import re
import pdfplumber


class TransportService:
    """从运输鉴定报告 PDF 提取关键字段"""

    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        """读取 PDF 所有页文本（支持中文）"""
        texts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    texts.append(text)
        return "\n".join(texts)

    @staticmethod
    def extract_fields(text: str) -> dict:
        """从 PDF 文本中提取关键字段"""
        result = {
            "product_name_cn": "",
            "product_name_en": "",
            "report_no": "",
            "sample_description": "",
        }

        # 中文名：匹配 "产品名称：" 或 "品名："
        cn_patterns = [
            r"产品名称[：:]\s*(.+?)(?:\n|$)",
            r"品名[：:]\s*(.+?)(?:\n|$)",
        ]
        for pattern in cn_patterns:
            match = re.search(pattern, text)
            if match:
                result["product_name_cn"] = match.group(1).strip()
                break

        # 英文名：匹配 "英文名称：" 或 "English Name："
        en_patterns = [
            r"英文名称[：:]\s*(.+?)(?:\n|$)",
            r"English\s*Name[：:]\s*(.+?)(?:\n|$)",
            r"产品名称\(英文\)[：:]\s*(.+?)(?:\n|$)",
        ]
        for pattern in en_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["product_name_en"] = match.group(1).strip()
                break

        # 运输鉴定编号：匹配 "编号：" 或 "报告编号："
        no_patterns = [
            r"编号[：:]\s*([A-Z0-9\-]+)",
            r"报告编号[：:]\s*([A-Z0-9\-]+)",
        ]
        for pattern in no_patterns:
            match = re.search(pattern, text)
            if match:
                result["report_no"] = match.group(1).strip()
                break

        # 样品描述：从外观描述段落提取
        desc_patterns = [
            r"外观[：:]\s*(.+?)(?:\n\n|$)",
            r"样品描述[：:]\s*(.+?)(?:\n\n|$)",
            r"性状[：:]\s*(.+?)(?:\n\n|$)",
        ]
        for pattern in desc_patterns:
            match = re.search(pattern, text)
            if match:
                result["sample_description"] = match.group(1).strip()
                break

        return result