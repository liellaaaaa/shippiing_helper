"""
Transport Service - 运输鉴定报告 PDF 字段提取
"""
import re
import os
import pdfplumber
from app.database import SessionLocal
from app.models.transport_report import TransportReport


# Module-level global cache: filename -> {text, fields}
_TRANSPORT_CACHE: dict = {}


class TransportService:
    """从运输鉴定报告 PDF 提取关键字段，扫描并索引 references/海运鉴定报告/ 目录"""

    # ------------------------------------------------------------
    # 1. scan_directory — 启动时扫描 references/海运鉴定报告/，Upsert 到 transport_reports 表
    # ------------------------------------------------------------
    def scan_directory(self, dir_path: str, db_session) -> int:
        """
        扫描 dir_path（含子目录），Upsert 每个 .pdf 到 transport_reports 表，
        将文本缓存到 _TRANSPORT_CACHE。
        返回扫描文件数量。
        """
        count = 0
        for root, _dirs, files in os.walk(dir_path):
            for filename in files:
                if not filename.lower().endswith(".pdf"):
                    continue
                file_path = os.path.join(root, filename)
                text = self.extract_text_from_pdf(file_path)
                fields = self.extract_fields(text)
                _TRANSPORT_CACHE[filename] = {"text": text, "fields": fields}

                existing = db_session.query(TransportReport).filter(
                    TransportReport.filename == filename
                ).first()
                record = {
                    "filename": filename,
                    "file_path": file_path,
                    "file_format": "pdf",
                    "loaded": 1,
                }
                if existing:
                    for k, v in record.items():
                        setattr(existing, k, v)
                else:
                    db_session.add(TransportReport(**record))
                count += 1
        db_session.commit()
        return count

    # ------------------------------------------------------------
    # 2. search — 在缓存文本中模糊搜索
    # ------------------------------------------------------------
    def search(self, query: str, db_session) -> list[dict]:
        """在缓存中对 filename / 文本内容做模糊匹配，返回 [{filename, match_type}]"""
        if not query:
            return []
        q_lower = query.lower()
        fn_matches = []
        content_matches = []
        for filename, cached in _TRANSPORT_CACHE.items():
            if q_lower in filename.lower():
                fn_matches.append({"filename": filename, "match_type": "filename"})
            elif q_lower in cached["text"].lower():
                content_matches.append({"filename": filename, "match_type": "content"})
        return fn_matches + content_matches

    # ------------------------------------------------------------
    # 3. get_file_path — 根据 filename 返回 file_path
    # ------------------------------------------------------------
    def get_file_path(self, filename: str, db_session) -> str | None:
        record = db_session.query(TransportReport).filter(
            TransportReport.filename == filename
        ).first()
        return record.file_path if record else None

    # ------------------------------------------------------------
    # 4. get_cached_fields — 根据 filename 返回缓存的字段信息
    # ------------------------------------------------------------
    def get_cached_fields(self, filename: str) -> dict | None:
        cached = _TRANSPORT_CACHE.get(filename)
        if cached:
            return cached["fields"]
        return None

    # ------------------------------------------------------------
    # 4. extract_text_from_pdf — 读取 PDF 所有页文本（支持中文）
    # ------------------------------------------------------------
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