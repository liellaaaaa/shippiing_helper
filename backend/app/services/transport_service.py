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

                # 从英文名查品名对照表，得到中文名
                en_name = fields.get("product_name_en", "")
                cn_name = ""
                if en_name:
                    from app.services.name_mapping_service import get_cn_name
                    cn_name = get_cn_name(en_name) or ""

                record = {
                    "filename": filename,
                    "file_path": file_path,
                    "file_format": "pdf",
                    "loaded": 1,
                    "report_no": fields.get("report_no", ""),
                    "product_name_cn": cn_name,
                    "product_name_en": en_name,
                    "sample_desc_cn": fields.get("sample_desc_cn", ""),
                    "sample_desc_en": fields.get("sample_desc_en", ""),
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
        """从 PDF 文本中提取关键字段。

        PDF 第3页结构（以 NACCWX25033580 为例）：
          样品名称
          Name of Goods OIL REMOVING AGENT      ← pdfplumber 中文乱码，英文可靠
          广东宏昊化工有限公司

          样品描述
          无色液体，稍有气味                      ← pdfplumber 中文乱码
          Colorless liquid, weak odor
          properties

        策略：英文名/英文描述直接提取；中文名通过品名映射表反推。
        """
        result = {
            "report_no": "",
            "product_name_cn": "",
            "product_name_en": "",
            "sample_desc_cn": "",
            "sample_desc_en": "",
        }

        # ── 报告编号：No. 前缀 ──────────────────────────────────
        m = re.search(r"No\.([A-Z0-9\-]+)", text, re.IGNORECASE)
        if m:
            result["report_no"] = m.group(1).strip()

        # ── 英文名：从 "Name of Goods XXXX" 行提取 ───────────────
        # pdfplumber 中文乱码，英文可靠
        # 冒号可能是全角（：），英文名在该行开头，取到行尾即可
        m = re.search(r"Name of Goods[：:\s]+(.+)", text)
        if m:
            result["product_name_en"] = m.group(1).strip()

        # ── 样品描述：跳过标签行，取实际内容行 ─────────────────
        # PDF 结构：样品描述 → 中文内容 → Appearance & → 英文内容 → properties
        # 逐行解析，跳过标签行和结论行
        skip_labels = {"Appearance &", "properties", ""}
        stop_starts = ("鉴定", "Conclusion", "建议", "Suggestion", "备注", "Note",
                       "运输信息", "Transportation", "鉴定依据", "Criteria")
        aidx = text.find("样品描述")
        if aidx != -1:
            lines = text[aidx:].split("\n")
            content_lines = []
            for l in lines[1:]:
                l_stripped = l.strip()
                if l_stripped in skip_labels:
                    continue
                if l_stripped.startswith(stop_starts):
                    break
                if l_stripped:
                    content_lines.append(l_stripped)
            if len(content_lines) >= 1:
                result["sample_desc_cn"] = content_lines[0]
            if len(content_lines) >= 2:
                result["sample_desc_en"] = content_lines[1]

        # ── 中文相关字段：通过品名映射表从英文名反推 ──────────────
        # 英文名已知时，通过 name_mapping_service 查中文名
        # （中文描述 pdfplumber 无法正确提取，跳过）
        # 具体查表逻辑放在 scan_directory() 扫描后统一处理

        return result