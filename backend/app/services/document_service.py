# backend/app/services/document_service.py
import openpyxl
import xlrd
from typing import Tuple, Optional
import os, time, base64, uuid
from datetime import datetime
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


def _parse_date(value: str):
    """将多种格式的日期字符串转为 Python datetime，失败时返回原字符串。"""
    if not value:
        return value
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y年%m月%d日"):
        try:
            return datetime.strptime(value[:len("2026-12-31")], fmt)
        except Exception:
            pass
    return value


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

    def fill_booking_template(self, fields: dict, template_key: str = "booking_marked") -> bytes:
        """
        直接操作 xlsx zip 内部 XML，精准替换 {{FIELD_NAME}} 单元格值，
        不经过 openpyxl 加载/保存，完整保留所有 shapes 和格式。
        fields: dict，键为 FIELD_NAME（不带花括号），值为字符串
        template_key: config.py 中的 TEMPLATES 键，默认 "booking_marked"
        """
        import zipfile, re, shutil, os
        from io import BytesIO
        from lxml import etree

        template_path = TEMPLATES.get(template_key, TEMPLATES.get("booking_marked", TEMPLATES.get("booking")))
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
                    elif field_key == "MEASUREMENT" and value:
                        value = f"{value} CBM"
                    # 写回 <v> 元素，并改为内联字符串类型（t="str"）
                    # 原始单元格可能是 t="s"（共享字符串索引），直接改值会导致查表错误
                    v_el = c_el.find(f'{{{NS}}}v')
                    if v_el is None:
                        v_el = etree.SubElement(c_el, f'{{{NS}}}v')
                    v_el.text = str(value)
                    # 改为内联字符串，避免共享字符串表索引错误
                    c_el.set('t', 'str')

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
        生成订舱单：template_type="multi" 使用多产品模板 booking_multi，
        其他情况使用 booking_marked。
        fields: 可选，键为字段名（无花括号），值未提供则返回空白模板。
        """
        if template_type == "multi":
            template_key = "booking_multi"
        else:
            template_key = "booking_marked"

        if fields:
            content_xlsx = self.fill_booking_template(fields, template_key=template_key)
        else:
            # 无参调用也使用 xlsx 已标记模板（空白版本）
            template_path = TEMPLATES.get(template_key, TEMPLATES.get("booking_marked", TEMPLATES.get("booking")))
            with open(template_path, "rb") as f:
                content_xlsx = f.read()

        doc_key = f"booking_{int(time.time())}"
        return content_xlsx, doc_key, base64.b64encode(content_xlsx).decode()

    def generate_loi(self, order_no: str, pi_no: str) -> Tuple[bytes, str, str]:
        """生成 LOI 保函：5 个字段来自运输鉴定报告 + 申报要素"""
        from app.models.transport_report import TransportReport
        from app.services.customs_declaration_service import CustomsDeclarationService

        template_path = TEMPLATES["loi"]
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"LOI template not found: {template_path}")
        db = SessionLocal()
        try:
            records = db.query(OrderPiRecord).filter(OrderPiRecord.order_no == order_no).all()
            if not records:
                raise ValueError(f"Order not found: {order_no}")

            first = records[0]
            product_cn = first.product_cn or ""

            # 从所有产品中找第一个非空 HS Code（LOI 是整单文档）
            hs_code = ""
            for r in records:
                if r.hs_code:
                    hs_code = r.hs_code
                    break

            # 1. 从运输鉴定报告获取前 4 个字段
            transport_fields = {}
            if product_cn:
                # 模糊匹配运输鉴定报告（取最匹配的一条）
                report = db.query(TransportReport).filter(
                    TransportReport.product_name_cn.ilike(f"%{product_cn}%")
                ).first()
                if report:
                    transport_fields = {
                        "report_no": report.report_no or "",
                        "product_name_en": report.product_name_en or "",
                        "sample_desc_cn": report.sample_desc_cn or "",
                        "product_name_cn": report.product_name_cn or product_cn,
                    }

            # 2. 从申报要素获取产品用途
            product_usage = ""
            if hs_code:
                decl_svc = CustomsDeclarationService.get_instance()
                elements = decl_svc.get_elements(hs_code)
                product_usage = elements.get("用途", "")

            # 3. 填充模板
            doc = Document(template_path)
            replacements = {
                "{{product_name_cn}}": transport_fields.get("product_name_cn", product_cn),
                "{{product_name_en}}": transport_fields.get("product_name_en", ""),
                "{{report_no}}": transport_fields.get("report_no", ""),
                "{{sample_desc}}": transport_fields.get("sample_desc_cn", ""),
                "{{product_usage}}": product_usage,
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
        doc_key = f"loi_{first.id}_{int(time.time())}"
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
            # Fix XML-level ordering: if a table immediately precedes a section heading
            # paragraph, swap them so the heading appears before the table in the rendered document.
            content = self._swap_table_heading_order(content)
        finally:
            db.close()
        doc_key = self._sanitize_doc_key(f"msds_{product_name}_{int(time.time())}")
        return content, doc_key, base64.b64encode(content).decode()

    @staticmethod
    def _swap_table_heading_order(content: bytes) -> bytes:
        """
        Fix OOXML body element ordering: if a <w:tbl> immediately precedes a
        <w:p> that starts with a section heading (e.g. "3、" or "13、"),
        swap them so the heading paragraph appears before the table.
        This corrects rendering in editors (OnlyOffice) that follow XML element order.
        """
        import zipfile, re
        from lxml import etree

        NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        # Section heading pattern: paragraph that starts with a non-digit character,
        # contains Chinese text, and ends with "：" (looks like a section label).
        section_heading_pattern = re.compile(r"^[^\d\s][^：]*：")

        try:
            zin = zipfile.ZipFile(BytesIO(content), "r")
            sheet_xml = zin.read("word/document.xml")
            zin.close()
        except Exception:
            return content

        tree = etree.fromstring(sheet_xml)
        body = tree.find(f"{{{NS}}}body")
        if body is None:
            return content

        children = list(body)
        swapped = False

        i = 0
        while i < len(children) - 1:
            curr = children[i]
            nxt = children[i + 1]
            curr_tag = curr.tag.split("}")[1] if "}" in curr.tag else curr.tag
            nxt_tag = nxt.tag.split("}")[1] if "}" in nxt.tag else nxt.tag

            if curr_tag == "tbl" and nxt_tag == "p":
                # Extract text of next paragraph
                texts = [t.text or "" for t in nxt.findall(f".//{{{NS}}}t")]
                para_text = "".join(texts).strip()
                if section_heading_pattern.match(para_text):
                    # Swap: move heading before table
                    body.remove(nxt)
                    body.insert(i, nxt)
                    children = list(body)
                    swapped = True
                    # After swapping, re-evaluate at same position since a new
                    # element is now before the table; skip ahead to avoid infinite loop
                    i += 1
                    continue

            i += 1

        if not swapped:
            return content

        # Repack the docx with the reordered XML
        out = BytesIO()
        with zipfile.ZipFile(BytesIO(content), "r") as zin:
            with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
                for item in zin.namelist():
                    if item == "word/document.xml":
                        zout.writestr(
                            item,
                            etree.tostring(tree, xml_declaration=True, encoding="UTF-8", standalone=True),
                        )
                    else:
                        zout.writestr(item, zin.read(item))
        out.seek(0)
        return out.read()

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

    def generate_customs(
        self,
        order_id: int | None = None,
        ledger_record_id: int | None = None,
        order_no: str | None = None,
    ) -> Tuple[bytes, str, str]:
        """
        生成报关资料工作簿（整本 xlsx，5个 sheet），自动填充模板字段。

        数据来源优先级：
        1. ledger_record_id（台账记录，含三源完整数据）
        2. order_id（回退到 OrderPiRecord 查询）
        3. order_no（直接用于台账查询）

        填充规则（各 Sheet 独立填充同一批产品数据）：
        - 报关单：填写第一产品行（R20），多产品继续填 R38/R41/...；
          汇总数据（件数/毛重/净重）来自 DrumCount/Sum 或首产品
        - 发票/箱单/合同：填写第一产品行（R8/R10/R19），其余行留空
        - 委托书：填写主要货物名称 + HS Code + 总价 + 日期
        """
        import openpyxl
        from app.services.ledger_service import LedgerService
        from app.services.customs_declaration_service import CustomsDeclarationService

        template_path = TEMPLATES["customs"]
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Customs template not found: {template_path}")

        # ── 读取台账数据 ────────────────────────────────────────────────
        if ledger_record_id:
            ledger_svc = LedgerService()
            record = ledger_svc.get_ledger_record(ledger_record_id)
        elif order_no:
            ledger_svc = LedgerService()
            resp = ledger_svc.list_ledger(search=order_no, page_size=1)
            record = resp.records[0] if resp.records else None
        elif order_id:
            db = SessionLocal()
            try:
                rows = db.query(OrderPiRecord).filter_by(id=order_id).all()
                if not rows:
                    record = None
                else:
                    from app.schemas.ledger import LedgerRecordResponse, LedgerItemSchema
                    first = rows[0]
                    record = LedgerRecordResponse(
                        id=first.id,
                        order_no=first.order_no,
                        customer_code=first.customer_code,
                        sales_person=first.sales_person,
                        consignee_name=first.consignee_name,
                        consignee_address=first.consignee_address,
                        destination=first.destination,
                        loading_port=first.loading_port,
                        price_term=first.price_term,
                        payment_terms=first.payment_terms,
                        pi_date=first.pi_date,
                        items=[
                            LedgerItemSchema(
                                internal_code=r.internal_code,
                                product_cn=r.product_cn,
                                spec_kg=r.spec_kg,
                                quantity_kg=r.quantity_kg,
                                unit_price=r.unit_price,
                                total_amount=r.total_amount,
                                hs_code=r.hs_code,
                                customs_name=r.customs_name,
                                customs_ingredients=r.components,
                                gross_weight_kg=r.gross_weight_kg,
                                net_weight_kg=r.net_weight_kg,
                                drum_count=r.drum_count,
                                pallet_count=r.pallet_count,
                            )
                            for r in rows
                        ],
                    )
            finally:
                db.close()
        else:
            record = None

        # ── 加载工作簿 ────────────────────────────────────────────────
        wb = openpyxl.load_workbook(template_path)
        ws_customs = wb["报关单"]
        ws_invoice = wb["发票"]
        ws_packing = wb["箱单"]
        ws_contract = wb["合同"]
        ws_proxy = wb["委托书"]

        decl_svc = CustomsDeclarationService.get_instance()

        # ── 通用辅助函数 ──────────────────────────────────────────────
        def cn_port(dest: str) -> str:
            """将英文港口/国家名翻译为中文海关常用名"""
            mapping = {
                # 国家
                "thailand": "泰国",
                "singapore": "新加坡",
                "shanghai": "上海",
                "guangzhou": "广州",
                "shenzhen": "深圳",
                "hong kong": "香港",
                "hkg": "香港",
                "malaysia": "马来西亚",
                "indonesia": "印度尼西亚",
                "jakarta": "雅加达",
                "indian": "印度",
                "india": "印度",
                "ahmedabad": "艾哈迈达巴德",
                "vietnam": "越南",
                "ho chi minh": "胡志明市",
                "hcmc": "胡志明市",
                "bangladesh": "孟加拉国",
                "philippines": "菲律宾",
                "manila": "马尼拉",
                "korea": "韩国",
                "busan": "釜山",
                "japan": "日本",
                "tokyo": "东京",
                "taiwan": "台湾",
                "taipei": "台北",
                "usa": "美国",
                "united states": "美国",
                "uk": "英国",
                "germany": "德国",
                "france": "法国",
                "netherlands": "荷兰",
                "italy": "意大利",
                "spain": "西班牙",
                "australia": "澳大利亚",
                # 港口
                "lat krabang": "拉格拉邦",
                "laem chabang": "拉格拉邦",
                "bangkok": "曼谷",
                "tangkok": "曼谷",
                "singapore port": "新加坡",
                "port of singapore": "新加坡",
                "shanghai port": "上海",
                "guangzhou port": "广州",
                "yantian": "盐田",
                "shekou": "蛇口",
                "chiwan": "赤湾",
                "ningbo": "宁波",
                "qingdao": "青岛",
                "tianjin": "天津",
                "dalian": "大连",
                "xiamen": "厦门",
            }
            if not dest:
                return ""
            lower = dest.lower().strip()
            # 先精确匹配，再包含匹配
            if lower in mapping:
                return mapping[lower]
            # 包含匹配（取第一个匹配）
            for key, val in mapping.items():
                if key in lower or lower in key:
                    return val
            # 未知原样返回
            return dest

        def fmt_amt(v: float | None) -> str:
            if v is None:
                return ""
            return f"{v:.2f}"

        # ── 无数据：返回未填充模板 ──────────────────────────────────
        if not record:
            buf = BytesIO()
            wb.save(buf)
            content = buf.getvalue()
            doc_key = f"customs_{uuid.uuid4().hex}"
            return content, doc_key, base64.b64encode(content).decode()

        items = record.items or []
        first = items[0] if items else None

        # ── 基本信息 ────────────────────────────────────────────────
        pi_no = record.order_no or ""
        consignee = record.consignee_name or ""
        dest_raw = record.destination or ""
        dest_cn = cn_port(dest_raw)          # 运抵国（中文）
        dest_port = dest_raw                   # 指运港（保留原文本）
        price_term = record.price_term or ""
        payment_terms = record.payment_terms or ""
        pi_date = record.pi_date or ""
        hs_code = first.hs_code if first else ""
        customs_name = first.customs_name if first else ""
        qty_kg = first.quantity_kg if first else None
        unit_price = first.unit_price if first else None
        total_amount = first.total_amount if first else None
        gross_weight = first.gross_weight_kg if first else None
        net_weight = first.net_weight_kg if first else None
        drum_count = first.drum_count if first else 0
        pallet_count = first.pallet_count if first else 0
        order_requirement = ""  # 来自台账或后续扩展

        # 申报要素（从 JSON 知识库查询）
        decl_elements = decl_svc.get_elements(hs_code)
        usage = decl_elements.get("用途", "")
        composition = decl_elements.get("成分", "")
        soluble = decl_elements.get("是否溶于水", "")
        appearance = decl_elements.get("外观", "")
        export_benefit = decl_elements.get("出口享惠情况", "不确定")
        base_source = decl_elements.get("底料来源", "")

        # 构造申报要素格式字符串
        decl_parts = []
        if usage:
            decl_parts.append(f"用途：{usage}")
        if composition:
            decl_parts.append(f"成分：{composition}")
        if soluble:
            decl_parts.append(f"是否溶于水：{soluble}")
        if appearance:
            decl_parts.append(f"外观：{appearance}")
        if export_benefit:
            decl_parts.append(f"出口享惠情况：{export_benefit}")
        if base_source:
            decl_parts.append(f"底料来源：{base_source}")
        decl_str = "|".join(decl_parts)

        # ── 填充 报关单 ──────────────────────────────────────────
        ws = ws_customs
        ws["A4"] = "广东宏昊化工有限公司"  # 境内发货人（固定）
        if price_term:
            ws["V4"] = price_term  # 成交方式
        ws["A6"] = consignee                              # 境外收货人名称
        ws["A8"] = "广东宏昊化工有限公司"                  # 生产销售单位（固定）
        if pi_no:
            ws["A10"] = pi_no                             # 合同协议号
        if dest_cn:
            ws["E10"] = dest_cn                           # 运抵国
            ws["G10"] = dest_cn                           # 运抵国（重复）
        if dest_port:
            ws["K10"] = dest_port                          # 指运港
        # 件数/毛重/净重（来自包装计算）
        if pallet_count:
            ws["E12"] = pallet_count                       # 件数
        if gross_weight:
            ws["F12"] = round(gross_weight, 1)            # 毛重
        if net_weight:
            ws["G12"] = round(net_weight, 1)              # 净重
        if price_term:
            ws["I12"] = price_term                         # 成交方式
        # 备注
        if order_requirement:
            ws["B16"] = order_requirement
        # 产品行（第1行从R20开始）
        if items:
            for idx, item in enumerate(items):
                item_row = 20 + idx * 18  # 间隔18行一个产品槽位（模板结构）
                if item_row > ws.max_row:
                    break
                ws.cell(item_row, 1, idx + 1)  # 项号
                if item.hs_code:
                    ws.cell(item_row, 2, item.hs_code)  # 商品编号
                if item.customs_name:
                    ws.cell(item_row, 4, item.customs_name)  # 商品名称
                qty = item.quantity_kg
                if qty:
                    ws.cell(item_row, 7, qty)   # 数量
                ws.cell(item_row, 8, "千克")      # 单位
                up = item.unit_price
                if up:
                    ws.cell(item_row, 9, up)     # 单价
                ws.cell(item_row, 11, "中国")     # 原产国
                if dest_cn:
                    ws.cell(item_row, 13, dest_cn)  # 最终目的国
                ws.cell(item_row, 16, "肇庆")      # 境内货源地（固定）
                ws.cell(item_row, 19, "照章征税")  # 征免（固定）

                # 申报要素（合并到第2行）
                elem_row = item_row + 1
                elem_parts = []
                if usage:
                    elem_parts.append(f"用途：{usage}")
                if item.customs_ingredients:
                    elem_parts.append(f"成分：{item.customs_ingredients}")
                elif composition:
                    elem_parts.append(f"成分：{composition}")
                if soluble:
                    elem_parts.append(f"是否溶于水：{soluble}")
                if appearance:
                    elem_parts.append(f"外观：{appearance}")
                if export_benefit:
                    elem_parts.append(f"出口享惠情况：{export_benefit}")
                elem_str = "|".join(elem_parts)
                if elem_str:
                    ws.cell(elem_row, 4, elem_str)
                ta = item.total_amount
                if ta:
                    ws.cell(item_row, 9, ta)    # 总价（填单价列，同行）

        # ── 填充 发票 ────────────────────────────────────────────
        ws = ws_invoice
        if pi_no:
            ws["G2"] = f"IN{pi_no}"              # 发票编号
        if consignee:
            ws["C3"] = consignee                 # 买方
        if pi_date:
            ws["G3"] = _parse_date(pi_date)                  # 日期
        if price_term:
            ws["G6"] = price_term                 # 成交方式
        if dest_port:
            ws["H6"] = dest_port                   # 目的港
        if items:
            for idx, item in enumerate(items):
                item_row = 8 + idx
                if item.customs_name:
                    ws.cell(item_row, 3, item.customs_name)  # 货物名称
                qty = item.quantity_kg
                if qty:
                    ws.cell(item_row, 4, qty)
                ws.cell(item_row, 5, "千克")       # 单位
                up = item.unit_price
                if up:
                    ws.cell(item_row, 6, up)       # 单价
                ws.cell(item_row, 7, "人民币")       # 币制
                ta = item.total_amount
                if ta:
                    ws.cell(item_row, 8, ta)        # 金额
            # TOTAL 汇总行
            total_amt = sum((i.total_amount or 0) for i in items)
            if total_amt:
                ws["H24"] = round(total_amt, 2)
                ws["G24"] = "人民币"
            # 重算 G 列总价
            for idx, item in enumerate(items):
                item_row = 8 + idx
                ta = item.total_amount
                if ta:
                    ws.cell(item_row, 8, ta)

        # ── 填充 箱单 ────────────────────────────────────────────
        ws = ws_packing
        if pi_date:
            ws["H3"] = _parse_date(pi_date)
        if pi_no:
            ws["H4"] = f"IN{pi_no}"               # 发票编号
        if consignee:
            ws["B5"] = consignee                   # 客户
        if pi_no:
            ws["H5"] = pi_no                       # 合同号
        if dest_cn:
            ws["E7"] = dest_cn                     # 目的国
        if payment_terms:
            ws["H7"] = payment_terms              # 付款条件
        if items:
            for idx, item in enumerate(items):
                item_row = 10 + idx
                ws.cell(item_row, 1, "N/M")        # 唛头
                if item.customs_name:
                    ws.cell(item_row, 2, item.customs_name)  # 货物名称
                pc = item.pallet_count
                if pc:
                    ws.cell(item_row, 3, pc)        # 件数（托）
                    ws.cell(item_row, 4, "托")       # 单位
                dc = item.drum_count
                if dc:
                    ws.cell(item_row, 5, dc)         # 数量（桶）
                    ws.cell(item_row, 6, "桶")
                gw = item.gross_weight_kg
                if gw:
                    ws.cell(item_row, 7, round(gw, 1))  # 毛重
                nw = item.net_weight_kg
                if nw:
                    ws.cell(item_row, 8, round(nw, 1))  # 净重

        # ── 填充 合同 ────────────────────────────────────────────
        ws = ws_contract
        if pi_no:
            ws["G4"] = pi_no                       # 合同号码
        if pi_date:
            ws["G7"] = _parse_date(pi_date)
        if consignee:
            ws["C8"] = consignee                    # 买方
        if price_term:
            ws["G13"] = price_term                 # 成交方式
        if dest_port:
            ws["H13"] = dest_port                  # 目的港
        if items:
            for idx, item in enumerate(items):
                item_row = 19 + idx
                if item.customs_name:
                    ws.cell(item_row, 2, item.customs_name)  # 货物名称
                qty = item.quantity_kg
                if qty:
                    ws.cell(item_row, 4, qty)
                ws.cell(item_row, 5, "千克")         # 单位
                up = item.unit_price
                if up:
                    ws.cell(item_row, 6, up)        # 单价
                ws.cell(item_row, 7, "人民币")        # 币制
                ta = item.total_amount
                if ta:
                    ws.cell(item_row, 8, ta)        # 金额
            # 总金额
            total_amt = sum((i.total_amount or 0) for i in items)
            if total_amt:
                ws["H31"] = round(total_amt, 2)
                ws["G31"] = "人民币"

        # ── 填充 委托书 ──────────────────────────────────────────
        ws = ws_proxy
        if consignee:
            ws["C21"] = "广东宏昊化工有限公司"      # 委托方
        # 汇总所有产品的货物名称和 HS Code
        all_names = [i.customs_name for i in items if i.customs_name]
        all_hs_codes = [i.hs_code for i in items if i.hs_code]
        name_summary = " / ".join(dict.fromkeys(all_names))  # 去重拼接
        hs_summary = " / ".join(dict.fromkeys(all_hs_codes))
        if name_summary:
            ws["C22"] = name_summary           # 主要货物名称（多产品拼接）
        if hs_summary:
            ws["C23"] = hs_summary            # HS编码（多产品拼接）
        total_amt = sum((i.total_amount or 0) for i in items)
        if total_amt:
            ws["D24"] = round(total_amt, 2)
        if pi_date:
            d = _parse_date(pi_date)
            ws["H23"] = d
            ws["H25"] = d

        # ── 保存 ────────────────────────────────────────────────
        buf = BytesIO()
        wb.save(buf)
        content = buf.getvalue()
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
            # Fix table/heading order in .docx before returning
            if file_path.endswith(".docx"):
                content = self._swap_table_heading_order(content)

        # 构建 doc_key（使用原始文件名，去掉空格括号等）
        import re
        safe_name = re.sub(r"[\(\)\s/\\]+", "_", os.path.splitext(os.path.basename(file_path))[0]).strip("_")
        doc_key = f"msds_{msds_index_record.id}_{safe_name}_{int(time.time())}"
        return content, doc_key, base64.b64encode(content).decode()
