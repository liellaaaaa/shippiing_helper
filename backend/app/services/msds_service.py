"""
MSDS 服务层：提取 MSDS 文档文本、成分表、理化特征，建立索引。
"""
import os
import re
import chardet
import zipfile
from typing import Optional

import subprocess

import pdfplumber
from app.database import SessionLocal
from app.models.msds_index import MSDSIndex


class MSDSService:
    """MSDS 文档处理服务"""

    # ------------------------------------------------------------
    # 1. extract_text
    # ------------------------------------------------------------
    def extract_text(self, file_path: str) -> str:
        """
        从 .doc / .docx / .pdf 提取纯文本。
        - .docx  → zipfile + ElementTree 解析 word/document.xml
        - .doc   → chardet 检测编码后读 binary（用 antiword 如果可用）
        - .pdf   → PyPDF2
        """
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".docx":
            return self._extract_docx(file_path)
        elif ext == ".doc":
            return self._extract_doc(file_path)
        elif ext == ".pdf":
            return self._extract_pdf(file_path)
        else:
            return ""

    def _extract_docx(self, file_path: str) -> str:
        """解析 .docx（ZIP + XML）"""
        text_parts: list[str] = []

        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                with zf.open("word/document.xml") as fh:
                    import xml.etree.ElementTree as ET

                    tree = ET.parse(fh)
                    root = tree.getroot()
                    # 收集所有文本节点
                    for elem in root.iter():
                        if elem.text and elem.text.strip():
                            text_parts.append(elem.text.strip())
        except Exception:
            pass

        return "\n".join(text_parts)

    def _extract_doc(self, file_path: str) -> str:
        """解析 .doc（二进制，antiword 或 chardet 回退）"""
        # 优先尝试 antiword
        try:
            result = subprocess.run(
                ["antiword", file_path],
                capture_output=True,
                timeout=30,
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout.decode("utf-8", errors="ignore")
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        # 回退：chardet 检测编码后读 binary
        try:
            with open(file_path, "rb") as f:
                raw = f.read()
            detected = chardet.detect(raw)
            encoding = detected.get("encoding", "latin-1") or "latin-1"
            return raw.decode(encoding, errors="ignore")
        except Exception:
            return ""

    def _extract_pdf(self, file_path: str) -> str:
        """解析 .pdf（支持中文）"""
        try:
            parts = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        parts.append(text)
            return "\n".join(parts)
        except Exception:
            return ""

    # ------------------------------------------------------------
    # 2. extract_composition_table
    # ------------------------------------------------------------
    def extract_composition_table(self, text: str) -> list[dict]:
        """
        解析成分表：查找含"组分"或"成分"的行，提取三列
        （组分、CAS NO.、含量）。
        返回 [{"component": ..., "cas": ..., "percentage": ...}, ...]
        """
        lines = text.split("\n")
        results: list[dict] = []

        # 匹配表头行（包含 组分 + CAS + 含量 的任意组合）
        header_pattern = re.compile(
            r"(组分|成分|cas|no|含量|浓度)", re.IGNORECASE
        )
        # 匹配数据行：至少两列，用空白或 | 分隔
        data_pattern = re.compile(
            r"^\s*([^\s|]+)\s+([^\s|]+)\s+([^\s|]+)"
        )

        in_table = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # 检测表头
            if header_pattern.search(stripped):
                in_table = True
                continue

            if in_table:
                # 简单启发式：逗号或连续空白分隔，至少3段
                parts = re.split(r"[\t|,，；;]+", stripped)
                if len(parts) >= 3:
                    results.append({
                        "component": parts[0].strip(),
                        "cas": parts[1].strip(),
                        "percentage": parts[2].strip(),
                    })
                elif len(parts) == 2:
                    results.append({
                        "component": parts[0].strip(),
                        "cas": parts[1].strip(),
                        "percentage": "",
                    })

        return results

    # ------------------------------------------------------------
    # 3. extract_physical_props
    # ------------------------------------------------------------
    def extract_physical_props(self, text: str) -> dict:
        """
        解析理化特征：
        - 外观与性状 → physical_form
        - 离子型     → ion_type
        - PH值       → ph
        """
        props: dict = {}

        patterns = {
            "physical_form": re.compile(
                r"(?:外观与性状|外观|性状|形态|形式)\s*[:：]\s*(.+?)(?:\n|$)", re.IGNORECASE
            ),
            "ion_type": re.compile(
                r"(?:离子型|离子)\s*[:：]\s*(.+?)(?:\n|$)", re.IGNORECASE
            ),
            "ph": re.compile(
                r"(?:ph|pH值|pH)\s*[:：]\s*([\d.]+)", re.IGNORECASE
            ),
        }

        for key, pat in patterns.items():
            m = pat.search(text)
            if m:
                props[key] = m.group(1).strip()

        return props

    # ------------------------------------------------------------
    # 4. index_msds_directory
    # ------------------------------------------------------------
    def index_msds_directory(self, dir_path: str, db_session) -> int:
        """
        扫描目录（含子目录），找所有 .doc/.docx/.pdf 文件，
        提取文件名中的产品名作为 product_name_cn（去数字前缀），
        调用 extract_text + extract_physical_props，写入 msds_indexes 表
        （upsert by filename）。
        返回索引文件数量。
        """
        extensions = {".doc", ".docx", ".pdf"}
        count = 0

        for root, _dirs, files in os.walk(dir_path):
            for filename in files:
                ext = os.path.splitext(filename)[1].lower()
                if ext not in extensions:
                    continue

                file_path = os.path.join(root, filename)

                # 提取产品名（去数字前缀，如 "001_ABC.doc" → "ABC"）
                name_without_ext = os.path.splitext(filename)[0]
                product_name_cn = re.sub(r"^\d+[-_]*", "", name_without_ext)

                # 提取文本
                text = self.extract_text(file_path)

                # 提取理化特征
                props = self.extract_physical_props(text)

                # Upsert
                existing = db_session.query(MSDSIndex).filter(
                    MSDSIndex.filename == filename
                ).first()

                record_dict = {
                    "filename": filename,
                    "product_name_cn": product_name_cn,
                    "file_path": file_path,
                    "physical_form": props.get("physical_form"),
                    "ion_type": props.get("ion_type"),
                    "ph": props.get("ph"),
                    "loaded": 1,
                }

                if existing:
                    for key, val in record_dict.items():
                        setattr(existing, key, val)
                else:
                    db_session.add(MSDSIndex(**record_dict))

                count += 1

        db_session.commit()
        return count

    # ------------------------------------------------------------
    # 5. get_msds_by_product
    # ------------------------------------------------------------
    def get_msds_by_product(self, product_name_cn: str, db_session) -> Optional[MSDSIndex]:
        """
        按产品名模糊搜索最匹配的一条。
        """
        pattern = f"%{product_name_cn}%"
        records = (
            db_session.query(MSDSIndex)
            .filter(MSDSIndex.product_name_cn.ilike(pattern))
            .order_by(MSDSIndex.id.desc())
            .limit(1)
            .all()
        )
        return records[0] if records else None