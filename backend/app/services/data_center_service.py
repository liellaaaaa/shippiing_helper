"""
数据中心服务：MSDS 参考文件的搜索、预览、修正上传。
搜索采用"文件名 > 品名 > 全文"三级优先级。
修正上传采用时间戳版本策略，永不覆盖原文件。
"""
import logging
import os
import re
from datetime import datetime
from typing import Optional

from app.database import SessionLocal
from app.models.msds_index import MSDSIndex
from app.models.msds_correction import MSDSCorrection
from app.services.msds_service import MSDSService


# Module-level global index cache — shared across all DataCenterService instances
_INDEX_CACHE: dict = {}

class DataCenterService:

    def __init__(self):
        self._msds = MSDSService()

    # ------------------------------------------------------------
    # 1. scan_msds_directory — 启动时全量扫描，建立内存索引
    # ------------------------------------------------------------
    def scan_msds_directory(self, dir_path: str, db_session) -> int:
        """
        扫描 dir_path（含子目录），Upsert 每个 .doc/.docx/.pdf 到 msds_indexes，
        并将文本摘要缓存到内存索引。
        返回索引文件数量。
        """
        extensions = {".doc", ".docx", ".pdf"}
        count = 0

        # 第一遍：扫描所有文件，记录去后缀名 → 文件的映射（优先.docx）
        name_to_file = {}  # name_without_ext → (filename, file_path, ext)
        for root, _dirs, files in os.walk(dir_path):
            for filename in files:
                ext = os.path.splitext(filename)[1].lower()
                if ext not in extensions:
                    continue
                name_without_ext = os.path.splitext(filename)[0]
                # 优先选择 .docx
                if name_without_ext not in name_to_file or ext == ".docx":
                    name_to_file[name_without_ext] = (filename, os.path.join(root, filename), ext)

        # 第二遍：处理去重后的文件列表
        for filename, file_path, ext in name_to_file.values():

                # 提取文本 + 理化特征
                text = self._msds.extract_text(file_path)
                props = self._msds.extract_physical_props(text)
                product_name = props.get("physical_form", "") or props.get("product_name", "")

                # 从文件名提取产品名（去数字前缀）
                name_without_ext = os.path.splitext(filename)[0]
                product_name_cn = re.sub(r"^\d+[-_]*", "", name_without_ext)

                file_format = "pdf" if ext == ".pdf" else ("docx" if ext == ".docx" else "doc")

                # Upsert msds_indexes
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
                    "file_format": file_format,
                    "loaded": 1,
                }

                if existing:
                    for key, val in record_dict.items():
                        setattr(existing, key, val)
                else:
                    db_session.add(MSDSIndex(**record_dict))

                # 写入模块级全局索引缓存
                _INDEX_CACHE[filename] = {
                    "text": text,
                    "props": props,
                    "product_name": product_name or product_name_cn,
                }

                count += 1

        db_session.commit()
        return count

    # ------------------------------------------------------------
    # 2. search_msds — 数据库模糊搜索，三级优先级
    # ------------------------------------------------------------
    def search_msds(self, query: str, db_session=None) -> list[dict]:
        """
        按数据库 filename / product_name_cn 模糊搜索（不依赖文件系统编码），
        三级优先级：文件名匹配 > 品名匹配 > 全文（缓存在 db record 里）。
        """
        if not query:
            return []
        if db_session is None:
            db_session = SessionLocal()

        try:
            q_pattern = f"%{query}%"
            fn_matches = db_session.query(MSDSIndex).filter(
                MSDSIndex.filename.ilike(q_pattern)
            ).all()
            fn_filenames = {r.filename for r in fn_matches}
            pn_matches = db_session.query(MSDSIndex).filter(
                MSDSIndex.product_name_cn.ilike(q_pattern),
                ~MSDSIndex.filename.in_(fn_filenames)  # noqa
            ).all()

            results = []
            for r in fn_matches:
                results.append({"filename": r.filename, "match_type": "filename"})
            for r in pn_matches:
                results.append({"filename": r.filename, "match_type": "product"})
            return results
        finally:
            if db_session is not None:
                db_session.close()

    # ------------------------------------------------------------
    # 3. get_msds_summary — 返回一条 MSDS 摘要
    # ------------------------------------------------------------
    def get_msds_summary(self, file_id: int, db_session) -> Optional[dict]:
        """返回 MSDS 摘要（字段同 MSDSIndex）。"""
        record = db_session.query(MSDSIndex).filter(MSDSIndex.id == file_id).first()
        if not record:
            return None
        return {
            "id": record.id,
            "filename": record.filename,
            "product_name_cn": record.product_name_cn,
            "physical_form": record.physical_form,
            "ion_type": record.ion_type,
            "ph": record.ph,
            "file_format": record.file_format,
            "file_path": record.file_path,
        }

    # ------------------------------------------------------------
    # 4. get_file_path — 返回文件路径供预览
    # ------------------------------------------------------------
    def get_file_path(self, file_id: int, db_session) -> Optional[str]:
        record = db_session.query(MSDSIndex).filter(MSDSIndex.id == file_id).first()
        return record.file_path if record else None

    # ------------------------------------------------------------
    # 5. upload_corrected_msds — 时间戳版本策略
    # ------------------------------------------------------------
    def upload_corrected_msds(
        self,
        file_id: int,
        file_content: bytes,
        original_filename: str,
        user: str = "admin",
        db_session=None,
    ) -> dict:
        """
        永不覆盖原文件。将上传文件以时间戳命名保存到同目录，
        原 MSDSIndex 元数据更新为新文件路径，
        修正历史记录到 MSDSCorrection 表。
        """
        if db_session is None:
            db_session = SessionLocal()

        try:
            record = db_session.query(MSDSIndex).filter(MSDSIndex.id == file_id).first()
            if not record:
                return {"error": "MSDS record not found"}

            # 解析扩展名
            ext = os.path.splitext(original_filename)[1].lower()
            file_format = "pdf" if ext == ".pdf" else "doc"

            # 生成时间戳文件名
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            base = os.path.splitext(original_filename)[0]
            new_filename = f"{base}_{ts}{ext}"

            # 保存到原文件所在目录
            dir_path = os.path.dirname(record.file_path)
            new_path = os.path.join(dir_path, new_filename)

            with open(new_path, "wb") as f:
                f.write(file_content)

            # 从新文件提取文本/属性，更新 MSDSIndex
            text = self._msds.extract_text(new_path)
            props = self._msds.extract_physical_props(text)

            record.file_path = new_path
            record.physical_form = props.get("physical_form") or record.physical_form
            record.ion_type = props.get("ion_type") or record.ion_type
            record.ph = props.get("ph") or record.ph
            record.file_format = file_format
            record.loaded = 1

            # 写修正历史
            correction = MSDSCorrection(
                msds_index_id=file_id,
                file_format=file_format,
                upload_timestamp=datetime.now(),
                product_name=props.get("physical_form") or record.product_name_cn,
                corrected_by=user,
                original_filename=original_filename,
                new_filename=new_filename,
            )
            db_session.add(correction)
            db_session.commit()

            # 更新模块级全局索引缓存
            _INDEX_CACHE[record.filename] = {
                "text": text,
                "props": props,
                "product_name": props.get("physical_form") or record.product_name_cn,
            }

            return {
                "success": True,
                "new_filename": new_filename,
                "file_path": new_path,
                "file_format": file_format,
            }
        finally:
            db_session.close()

    # ------------------------------------------------------------
    # 6. get_directory_tree — 返回目录树结构
    # ------------------------------------------------------------
    def get_directory_tree(self, root_dir: str) -> list[dict]:
        """
        Recursively scan root_dir and return a nested tree structure.
        Each node: { label, key, isLeaf, file_type, file_path, children: [] }
        file_type: 'folder' | 'pdf' | 'doc' | 'docx' | 'xls' | 'xlsx' | 'json' | 'other'
        Only folders with at least one file are included.
        """
        def scan_dir(dir_path: str) -> list[dict]:
            nodes = []
            try:
                for entry in sorted(os.scandir(dir_path), key=lambda e: e.name):
                    if entry.is_dir():
                        children = scan_dir(entry.path)
                        if children:
                            nodes.append({
                                "label": entry.name,
                                "key": entry.path,
                                "isLeaf": False,
                                "file_type": "folder",
                                "file_path": entry.path,
                                "children": children,
                            })
                    elif entry.is_file():
                        ext = os.path.splitext(entry.name)[1].lower()
                        file_type_map = {
                            ".pdf": "pdf",
                            ".doc": "doc",
                            ".docx": "docx",
                            ".xls": "xls",
                            ".xlsx": "xlsx",
                            ".json": "json",
                        }
                        file_type = file_type_map.get(ext, "other")
                        nodes.append({
                            "label": entry.name,
                            "key": entry.path,
                            "isLeaf": True,
                            "file_type": file_type,
                            "file_path": entry.path,
                        })
            except PermissionError:
                logging.warning(f"Permission denied, skipping directory: {dir_path}")
                return []
            return nodes

        return scan_dir(root_dir)