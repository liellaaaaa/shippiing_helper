# backend/app/services/document_service.py
import openpyxl
import xlrd
from typing import Tuple, Optional
import os, time, base64, uuid
from io import BytesIO
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from app.core.config import TEMPLATES, MSDS_DIR
from app.services.msds_service import MSDSService
from app.database import SessionLocal
from app.models.order import Order, OrderItem
from app.models.order_pi_record import OrderPiRecord
from app.models.pi_contract import PiContract, PiContractItem


import re

# XML 1.0 compatible character set: U+0009, U+000A, U+000D, U+0020–U+10FFFF
_XML_ILLEGALChars = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f\ud800-\udfff￾￿]"
)


def _sanitize_for_xml(text: str) -> str:
    """Remove XML-illegal control characters from text."""
    return _XML_ILLEGALChars.sub("", text)


def convert_doc_to_docx(doc_path: str) -> bytes:
    """
    将 .doc 文件（binary，非 OLE）转换为 .docx 格式。
    使用 antiword 提取纯文本，再按段落写入 python-docx 文档。
    返回 docx 内容的 bytes。
    """
    text = _extract_doc_text(doc_path)
    doc = Document()
    for line in text.split("\n"):
        line = _sanitize_for_xml(line.rstrip())
        if not line:
            doc.add_paragraph("")
        else:
            doc.add_paragraph(line)
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _extract_doc_text(doc_path: str) -> str:
    """
    从 .doc 文件提取纯文本（antiword 优先，chardet 回退）。
    尝试多种编码以确保中文正确提取。
    """
    import subprocess, chardet

    # 优先尝试 antiword（可能返回 utf-8 或 latin-1 编码）
    for encoding in ("utf-8", "latin-1", "cp1252", "gb2312", "gbk"):
        try:
            result = subprocess.run(
                ["antiword", "-f", doc_path] if encoding != "utf-8" else ["antiword", doc_path],
                capture_output=True,
                timeout=30,
            )
            if result.returncode == 0 and result.stdout:
                try:
                    text = result.stdout.decode(encoding, errors="strict")
                except UnicodeDecodeError:
                    text = result.stdout.decode(encoding, errors="replace")
                # 检查是否提取到了有效内容（包含非ASCII字符或足够多的ASCII）
                if text and len(text.strip()) > 10:
                    return text
        except (subprocess.SubprocessError, FileNotFoundError):
            break
        except Exception:
            continue

    # 回退：读取二进制文件，用 chardet 检测编码
    try:
        with open(doc_path, "rb") as f:
            raw = f.read()
        detected = chardet.detect(raw)
        encoding = detected.get("encoding", "latin-1") or "latin-1"
        return raw.decode(encoding, errors="replace")
    except Exception:
        return ""


def convert_xls_to_xlsx(template_path: str) -> bytes:
    """用 xlrd 读取 .xls，用 openpyxl 写出 .xlsx，保持单元格数据不变。"""
    wb_xls = xlrd.open_workbook(template_path)
    ws_xls = wb_xls.sheet_by_index(0)
    wb = openpyxl.Workbook()
    ws = wb.active
    for r in range(ws_xls.nrows):
        for c in range(ws_xls.ncols):
            ws.cell(r + 1, c + 1).value = ws_xls.cell_value(r, c)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def find_marker_cell(ws, marker_text: str) -> Tuple[int, int]:
    """在 worksheet 中搜索 {{MARK_XXX}} 锚点，返回 (row, column)，1-based。"""
    for row in ws.iter_rows():
        for cell in row:
            if cell.value and str(cell.value).strip() == marker_text:
                return cell.row, cell.column
    raise ValueError(f"Marker '{marker_text}' not found in template")


def clear_markers(ws):
    """渲染后清除所有 {{MARK_XXX}} 锚点。"""
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and cell.value.startswith("{{MARK_"):
                cell.value = None


class DocumentService:
    def __init__(self):
        self.msds_service = MSDSService()

    def fill_booking_template(self, fields: dict) -> bytes:
        """
        直接操作 xlsx zip 内部 XML，精准替换 {{FIELD_NAME}} 单元格值，
        不经过 openpyxl 加载/保存，完整保留所有 shapes 和格式。
        fields: dict，键为 FIELD_NAME（不带花括号），值为字符串
        """
        import zipfile, re, shutil, os
        from io import BytesIO
        from lxml import etree

        template_path = TEMPLATES.get("booking_marked", TEMPLATES.get("booking"))
        NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'

        # 1. 先用 openpyxl 只读模式找出 {{FIELD}} 单元格坐标（不保存）
        wb = openpyxl.load_workbook(template_path, data_only=True)
        ws = wb.active
        sheet_name = ws.title
        marker_map = {}  # cell_ref -> field_key
        for row in ws.iter_rows():
            for cell in row:
                if cell.value and isinstance(cell.value, str):
                    m = re.match(r"^\{\{(\w+)\}\}$", str(cell.value).strip())
                    if m:
                        marker_map[cell.coordinate] = m.group(1)
        wb.close()

        # 2. 直接修改 xlsx zip 内的 sheet XML
        tmp_path = template_path + ".tmp"
        shutil.copy(template_path, tmp_path)

        with zipfile.ZipFile(tmp_path, 'r') as zin:
            # 找到工作表文件路径
            wb_xml = etree.fromstring(zin.read('xl/workbook.xml'))
            sheets_el = wb_xml.find(f'{{{NS}}}sheets')
            r_id = None
            for s in sheets_el:
                if s.get('name') == sheet_name:
                    r_id = s.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
                    break

            rels_xml = etree.fromstring(zin.read('xl/_rels/workbook.xml.rels'))
            sheet_file = None
            for rel in rels_xml:
                if rel.get('Id') == r_id:
                    sheet_file = 'xl/' + rel.get('Target')
                    break

            sheet_tree = etree.fromstring(zin.read(sheet_file))

            # 3. 遍历单元格，替换 {{FIELD}} 的值
            for c_el in sheet_tree.iter(f'{{{NS}}}c'):
                r = c_el.get('r')
                if r in marker_map:
                    field_key = marker_map[r]
                    value = fields.get(field_key, "")
                    # 固定单位后缀
                    if field_key == "NO_KIND_PKG" and value:
                        value = f"{value} PALLETS"
                    elif field_key == "GROSS_WEIGHT" and value:
                        value = f"{value} KGS"
                    elif field_key == "MEASUREMENT" and value:
                        value = f"{value} CBM"
                    # 写回 <v> 元素
                    v_el = c_el.find(f'{{{NS}}}v')
                    if v_el is None:
                        v_el = etree.SubElement(c_el, f'{{{NS}}}v')
                    v_el.text = str(value)
                    # 清除 t="str" 等类型标记（改为普通字符串）
                    c_el.attrib.pop('t', None)

            # 4. 重新打包 zip
            out = BytesIO()
            with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zout:
                for item in zin.namelist():
                    if item == sheet_file:
                        zout.writestr(item, etree.tostring(
                            sheet_tree, xml_declaration=True, encoding='UTF-8', standalone=True))
                    else:
                        zout.writestr(item, zin.read(item))

        os.remove(tmp_path)
        out.seek(0)
        return out.read()

    def generate_booking(self, fields: dict | None = None, template_type: str = "xlsx") -> Tuple[bytes, str, str]:
        """
        生成订舱单：始终使用 xlsx 已标记模板。
        fields: 可选，键为字段名（无花括号），值未提供则返回空白模板。
        """
        if fields:
            content_xlsx = self.fill_booking_template(fields)
        else:
            # 无参调用也使用 xlsx 已标记模板（空白版本）
            template_path = TEMPLATES.get("booking_marked", TEMPLATES.get("booking"))
            with open(template_path, "rb") as f:
                content_xlsx = f.read()

        doc_key = f"booking_{int(time.time())}"
        return content_xlsx, doc_key, base64.b64encode(content_xlsx).decode()

    def generate_loi(self, order_no: str, pi_no: str) -> Tuple[bytes, str, str]:
        template_path = TEMPLATES["loi"]
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"LOI template not found: {template_path}")
        db = SessionLocal()
        try:
            # Query OrderPiRecord by order_no (Phase 1 merged data store)
            records = db.query(OrderPiRecord).filter(OrderPiRecord.order_no == order_no).all()
            if not records:
                raise ValueError(f"Order not found: {order_no}")

            pi = db.query(PiContract).filter_by(pi_no=pi_no).first() if pi_no else None

            doc = Document(template_path)

            # 汇总多产品信息
            total_gw = sum(it.gross_weight_kg or 0 for it in records)
            total_vol = sum(it.volume_cbm or 0 for it in records)
            product_names = " / ".join([it.product_cn or "" for it in records if it.product_cn])
            replacements = {
                "{{shipper}}": "HONGHAO CHEMICAL CO., LTD.",
                "{{consignee}}": (pi.consignee_name or "") if pi else "",
                "{{consignee_address}}": (pi.consignee_address or "") if pi else "",
                "{{port_of_discharge}}": (pi.destination or "") if pi else "",
                "{{product_name_cn}}": product_names,
                "{{product_name_en}}": (records[0].product_en or "") if records else "",
                "{{hs_code}}": (records[0].hs_code or "") if records else "",
                "{{gross_weight}}": str(round(total_gw, 1)),
                "{{volume}}": str(round(total_vol, 3)),
                "{{date}}": time.strftime("%Y 年 %m 月 %d 日"),
            }
            for para in doc.paragraphs:
                for key, val in replacements.items():
                    if key in para.text:
                        for run in para.runs:
                            if key in run.text:
                                run.text = run.text.replace(key, val)
            buf = BytesIO()
            doc.save(buf)
            content = buf.getvalue()
        finally:
            db.close()
        first_record = records[0]
        doc_key = f"loi_{first_record.id}_{int(time.time())}"
        return content, doc_key, base64.b64encode(content).decode()

    def generate_msds(self, product_name: str) -> Tuple[bytes, str, str]:
        template_path = TEMPLATES["msds"]
        db = SessionLocal()
        try:
            msds_index = self.msds_service.get_msds_by_product(product_name, db)
            # Find a usable template: prefer standard .docx, then matched .docx, then any .docx in MSDS_DIR
            effective_template: Optional[str] = None
            if template_path.endswith(".docx") and os.path.exists(template_path):
                effective_template = template_path
            elif msds_index:
                matched_path = msds_index.file_path
                if matched_path.endswith(".docx") and os.path.exists(matched_path):
                    effective_template = matched_path
                else:
                    # .doc file is not loadable by python-docx — try to find a .docx fallback in the dir
                    msds_dir = os.path.dirname(matched_path) if os.path.exists(os.path.dirname(matched_path)) else MSDS_DIR
                    for fname in os.listdir(msds_dir):
                        if fname.endswith(".docx"):
                            candidate = os.path.join(msds_dir, fname)
                            if os.path.exists(candidate):
                                effective_template = candidate
                                break
            if not effective_template:
                # Last resort: scan MSDS_DIR for any .docx
                for fname in os.listdir(MSDS_DIR):
                    if fname.endswith(".docx"):
                        candidate = os.path.join(MSDS_DIR, fname)
                        if os.path.exists(candidate):
                            effective_template = candidate
                            break
            if not effective_template:
                # 尝试把 matched .doc 文件转成 .docx（从零构建表格结构）
                if msds_index and msds_index.file_path.endswith(".doc") and os.path.exists(msds_index.file_path):
                    content = self._build_msds_docx_from_doc(msds_index.file_path, product_name)
                    doc_key = f"msds_{product_name}_{int(time.time())}"
                    return content, doc_key, base64.b64encode(content).decode()
                else:
                    # 最后尝试：将 MSDS_DIR 中任意第一个 .doc 转换为 .docx
                    for fname in os.listdir(MSDS_DIR):
                        if fname.endswith(".doc"):
                            candidate = os.path.join(MSDS_DIR, fname)
                            if os.path.exists(candidate):
                                try:
                                    content = self._build_msds_docx_from_doc(candidate, product_name)
                                    doc_key = self._sanitize_doc_key(f"msds_{product_name}_{int(time.time())}")
                                    return content, doc_key, base64.b64encode(content).decode()
                                except Exception:
                                    continue
                    raise FileNotFoundError(f"MSDS template not found for product: {product_name}")

            doc = Document(effective_template)
            tables = doc.tables
            if msds_index and tables:
                text = self.msds_service.extract_text(msds_index.file_path)
                composition = self.msds_service.extract_composition_table(text)
                props = self.msds_service.extract_physical_props(text)
                if len(tables) >= 1:
                    t0 = tables[0]
                    t0.cell(0, 1).text = props.get("physical_form", "")
                    t0.cell(1, 1).text = props.get("ion_type", "")
                    t0.cell(2, 1).text = props.get("ph", "")
                if len(tables) >= 2:
                    comp_table = tables[1]
                    for i, item in enumerate(composition):
                        if i >= len(comp_table.rows):
                            break
                        row = comp_table.rows[i]
                        row.cells[0].text = str(i + 1)
                        row.cells[1].text = item.get("component", "")
                        row.cells[2].text = item.get("cas", "")
                        row.cells[3].text = item.get("percentage", "")
            buf = BytesIO()
            doc.save(buf)
            content = buf.getvalue()
        finally:
            db.close()
        doc_key = self._sanitize_doc_key(f"msds_{product_name}_{int(time.time())}")
        return content, doc_key, base64.b64encode(content).decode()

    @staticmethod
    def _sanitize_doc_key(key: str) -> str:
        """Remove chars that OnlyOffice server-side routing mishandles."""
        import re
        return re.sub(r"[\(\)\s/\\]+", "_", key).strip("_")

    def _build_msds_docx_from_doc(self, doc_path: str, product_name: str) -> bytes:
        """
        将 .doc 文件转换为包含标准 MSDS 表格结构的 .docx。
        从源 .doc 提取文本填充到预设表格中。
        """
        text = self.msds_service.extract_text(doc_path)
        composition = self.msds_service.extract_composition_table(text)
        props = self.msds_service.extract_physical_props(text)

        doc = Document()

        # 标题
        title = doc.add_heading("物质安全数据表 (MSDS)", level=1)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # 产品名
        doc.add_paragraph(f"产品名称：{product_name}").runs[0].bold = True
        doc.add_paragraph("")

        # 表1：理化特性
        doc.add_heading("1. 理化特性", level=2)
        table1 = doc.add_table(rows=4, cols=2)
        table1.style = "Table Grid"
        fields = [
            ("外观与性状", props.get("physical_form", "")),
            ("离子型", props.get("ion_type", "")),
            ("pH值", props.get("ph", "")),
            ("沸点/熔点", ""),
        ]
        for i, (label, value) in enumerate(fields):
            table1.rows[i].cells[0].text = label
            table1.rows[i].cells[1].text = value

        doc.add_paragraph("")

        # 表2：成分组成
        doc.add_heading("2. 成分组成", level=2)
        table2 = doc.add_table(rows=1 + len(composition), cols=3)
        table2.style = "Table Grid"
        # 表头
        hdr = table2.rows[0].cells
        hdr[0].text = "序号"
        hdr[1].text = "组分名称"
        hdr[2].text = "CAS No. / 含量"
        for cell in hdr:
            cell.paragraphs[0].runs[0].bold = True
        # 数据行
        for i, item in enumerate(composition):
            row = table2.rows[i + 1].cells
            row[0].text = str(i + 1)
            row[1].text = item.get("component", "")
            row[2].text = item.get("percentage", "")

        doc.add_paragraph("")

        # 附加信息（来自原文）
        doc.add_heading("3. 其他信息", level=2)
        for line in text.split("\n")[:50]:
            line = line.strip()
            if line and len(line) > 3:
                doc.add_paragraph(line)

        buf = BytesIO()
        doc.save(buf)
        return buf.getvalue()

    def generate_customs(self, order_id: int | None = None) -> Tuple[bytes, str, str]:
        """
        生成报关资料工作簿（整本 xlsx，5个 sheet）。
        第一期仅返回原始模板，不做数据填充（为后续自动填充留扩展口）。
        """
        template_path = TEMPLATES["customs"]
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Customs template not found: {template_path}")

        with open(template_path, "rb") as f:
            content = f.read()

        doc_key = f"customs_{uuid.uuid4().hex}"
        return content, doc_key, base64.b64encode(content).decode()

    def generate_template_instance(self, template_type: str) -> Tuple[bytes, str, str]:
        """加载空白模板（不填充 marker），返回 (content, doc_key, encoded_content)。"""
        type_map = {
            "booking": ("booking", "xlsx"),
            "loi":     ("loi",     "docx"),
            "msds":    ("msds",    "docx"),
        }
        if template_type not in type_map:
            raise ValueError(f"Unknown template type: {template_type}")
        key_prefix, file_ext = type_map[template_type]
        template_path = TEMPLATES[template_type]
        # Find effective template: .docx directly, or .xls for booking
        effective_template: Optional[str] = None
        if os.path.exists(template_path):
            if template_path.endswith(".docx"):
                effective_template = template_path
            elif template_path.endswith(".xls"):
                effective_template = template_path  # .xls will be converted to .xlsx below
        # For MSDS, also scan MSDS_DIR as fallback
        if not effective_template and template_type == "msds":
            for fname in os.listdir(MSDS_DIR):
                candidate = os.path.join(MSDS_DIR, fname)
                if fname.endswith(".docx") and os.path.exists(candidate):
                    effective_template = candidate
                    break
                elif fname.endswith(".doc") and os.path.exists(candidate):
                    try:
                        converted = convert_doc_to_docx(candidate)
                        temp_path = os.path.join(MSDS_DIR, f"_blank_converted_{fname}.docx")
                        with open(temp_path, "wb") as f:
                            f.write(converted)
                        effective_template = temp_path
                        break
                    except Exception:
                        continue
        if not effective_template:
            raise FileNotFoundError(f"Template not found: {template_path}")

        if file_ext == "xlsx":
            # .xls 模板 → .xlsx
            content = convert_xls_to_xlsx(effective_template)
        else:
            doc = Document(effective_template)
            buf = BytesIO()
            doc.save(buf)
            content = buf.getvalue()

        timestamp = int(time.time())
        doc_key = f"{key_prefix}_template_{timestamp}"
        return content, doc_key, base64.b64encode(content).decode()

    def load_msds_file(self, msds_index_record) -> Tuple[bytes, str, str]:
        """
        根据 MSDSIndex 记录加载原始文件，检测文件真实格式后转换。
        msds_index_record: MSDSIndex ORM 对象
        返回 (content_bytes, doc_key, base64_content)
        """
        file_path = msds_index_record.file_path

        # 用魔数检测真实格式，不用扩展名
        with open(file_path, "rb") as f:
            magic = f.read(8)

        # OLE2 Compound Document (.doc/.xls 等旧 Office 格式)
        if magic[:4] == b"\xd0\xcf\x11\xe0":
            content = convert_doc_to_docx(file_path)
        # PDF
        elif magic[:4] == b"%PDF":
            with open(file_path, "rb") as f:
                content = f.read()
        # ZIP-based docx/xlsx (默认)
        else:
            with open(file_path, "rb") as f:
                content = f.read()

        # 构建 doc_key（使用原始文件名，去掉空格括号等）
        import re
        safe_name = re.sub(r"[\(\)\s/\\]+", "_", os.path.splitext(os.path.basename(file_path))[0]).strip("_")
        doc_key = f"msds_{msds_index_record.id}_{safe_name}_{int(time.time())}"
        return content, doc_key, base64.b64encode(content).decode()
