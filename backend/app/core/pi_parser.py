"""
PI文件解析器 - 从Excel文件中提取PI合同数据

支持两种格式：
1. 表格格式（外贸订单PI合同.xlsx）：标准行列格式，有表头
2. Proforma Invoice 格式（.xls）：自由文本型发票，含产品表格和银行信息
"""

import re
import io
import os
import pymupdf
import pytesseract
from PIL import Image
from openpyxl import load_workbook
import xlrd
from typing import Optional

from app.schemas.pi_contract import (
    PiContractUploadResponse,
    PiContractItemRow,
    ConfidenceInfo,
)


# 标准字段映射：字段名 -> 可能的中英文表头别名
COLUMN_MAPPING: dict[str, list[str]] = {
    "customer_code": ["客户编码", "客户编号", "客户代码", "Customer Code", "customer"],
    "pi_no": ["PI号", "PI NO.", "Proforma Invoice No.", "PI号码", "PI_NO", "Proforma Invoice Number", "发票号"],
    "sales_person": ["业务员", "Salesperson", "销售员"],
    "pi_date": ["日期", "Date", "PI Date", "开票日期"],
    "order_id": ["销售订单号", "Sales Order No.", "SO No.", "订单号"],
    "internal_code": ["内部编码", "Item Code", "SKU", "产品代码", "编码"],
    "quantity": ["数量", "QTY", "Quantity", "订单数量"],
    "unit_price": ["单价", "Unit Price", "Price", "单价(USD)"],
    "total_amount": ["金额", "Amount", "Total", "总额"],
    "product_color": ["产品颜色", "Color", "颜色"],
    "hs_code": ["海关编码", "H.S. Code", "HS Code", "编码"],
    "customs_name": ["报关品名", "Customs Name", "品名"],
    "customs_composition": ["报关成分", "Ingredients", "成分"],
    "order_customs_name": ["填写订单报关品名", "Order Customs Name"],
    "is_ordered": ["是否下单", "Is Ordered", "已下单"],
    "notes": ["备注", "Notes", "Remark", "备注信息"],
}


def _normalize_column_name(col_name: str) -> str | None:
    """
    将列名标准化为目标字段名

    - 去除空格
    - 匹配 COLUMN_MAPPING 中的别名
    - 返回字段名或 None（无法识别）
    """
    col_name = col_name.strip()
    for field_name, aliases in COLUMN_MAPPING.items():
        if col_name in aliases:
            return field_name
    return None


def _parse_float(value: str) -> float | None:
    """
    安全地解析浮点数

    - 空字符串返回 None
    - 解析失败返回 None
    """
    if not value or not value.strip():
        return None
    try:
        return float(value.strip())
    except (ValueError, TypeError):
        return None


def _build_header_map(header_row: list[str]) -> dict[int, str]:
    """
    构建列索引到目标字段名的映射

    根据表头行，返回 {列索引: 字段名} 的字典
    """
    col_map: dict[int, str] = {}
    for idx, col_name in enumerate(header_row):
        field_name = _normalize_column_name(col_name)
        if field_name:
            col_map[idx] = field_name
    return col_map


def parse_pi_file(rows: list[list[str]]) -> PiContractUploadResponse:
    """
    解析表格格式PI文件数据（标准行列格式）

    参数:
        rows: Excel行列表，第一行是表头

    返回:
        PiContractUploadResponse

    异常:
        ValueError: 表头为空或缺少关键字段（pi_no, customer_code）
    """
    if not rows or len(rows) < 1:
        raise ValueError("文件为空或无有效数据")

    header_row = rows[0]
    if not header_row or all(not c.strip() for c in header_row):
        raise ValueError("表头行无效")

    col_map = _build_header_map(header_row)

    # 关键字段检查：pi_no 和 customer_code
    if "pi_no" not in col_map.values() or "customer_code" not in col_map.values():
        raise ValueError("缺少关键字段：pi_no 或 customer_code")

    data_rows = rows[1:]

    # 构建反向映射：字段名 -> 列索引
    field_to_col: dict[str, int] = {}
    for col_idx, field_name in col_map.items():
        field_to_col[field_name] = col_idx

    # 公共字段（取第一行的值）
    pi_no = None
    customer_code = None
    sales_person = None
    pi_date = None
    is_ordered = "0"

    if data_rows:
        first_row = data_rows[0]
        for field_name, col_idx in field_to_col.items():
            if col_idx < len(first_row):
                val = first_row[col_idx].strip() if first_row[col_idx] else None
                if field_name == "pi_no":
                    pi_no = val
                elif field_name == "customer_code":
                    customer_code = val
                elif field_name == "sales_person":
                    sales_person = val
                elif field_name == "pi_date":
                    pi_date = val
                elif field_name == "is_ordered":
                    is_ordered = val if val else "0"

    # 解析明细行
    items: list[PiContractItemRow] = []
    row_errors: list[str] = []
    failed_rows = 0

    for row_idx, row in enumerate(data_rows):
        item_row_errors: list[str] = []
        missing_fields: list[str] = []

        internal_code = None
        quantity = None
        unit_price = None
        total_amount = None
        product_color = None
        hs_code = None
        customs_name = None
        customs_composition = None
        order_customs_name = None
        notes = None

        for field_name, col_idx in field_to_col.items():
            if col_idx < len(row):
                raw_val = row[col_idx]
                if field_name in ("quantity", "unit_price", "total_amount"):
                    parsed = _parse_float(raw_val)
                    if raw_val and raw_val.strip() and parsed is None:
                        item_row_errors.append(f"{field_name}解析失败: {raw_val}")
                    if field_name == "quantity":
                        quantity = parsed
                    elif field_name == "unit_price":
                        unit_price = parsed
                    elif field_name == "total_amount":
                        total_amount = parsed
                else:
                    val = raw_val.strip() if raw_val else None
                    if field_name == "internal_code":
                        internal_code = val
                        if not val:
                            missing_fields.append("internal_code")
                    elif field_name == "product_color":
                        product_color = val
                    elif field_name == "hs_code":
                        hs_code = val
                    elif field_name == "customs_name":
                        customs_name = val
                    elif field_name == "customs_composition":
                        customs_composition = val
                    elif field_name == "order_customs_name":
                        order_customs_name = val
                    elif field_name == "notes":
                        notes = val

        row_status = "success"
        row_error_msg = None
        if item_row_errors or missing_fields:
            row_status = "error"
            failed_rows += 1
            error_parts = item_row_errors.copy()
            if missing_fields:
                error_parts.append(f"缺少字段: {', '.join(missing_fields)}")
            row_error_msg = "; ".join(error_parts)
            row_errors.append(row_error_msg)

        items.append(PiContractItemRow(
            row_index=row_idx + 1,
            status=row_status,
            error_msg=row_error_msg,
            internal_code=internal_code,
            quantity=quantity,
            unit_price=unit_price,
            total_amount=total_amount,
            product_color=product_color,
            hs_code=hs_code,
            customs_name=customs_name,
            customs_composition=customs_composition,
            order_customs_name=order_customs_name,
            notes=notes,
        ))

    recognized = len(col_map)
    total_cols = len(header_row)
    confidence = ConfidenceInfo(
        recognized=recognized,
        total=total_cols,
        percentage=f"{recognized / total_cols * 100:.0f}%" if total_cols > 0 else "0%",
        failed_rows=failed_rows,
    )

    if not pi_no:
        raise ValueError("无法从数据中提取 PI号")

    return PiContractUploadResponse(
        pi_no=pi_no or "",
        customer_code=customer_code,
        sales_person=sales_person,
        pi_date=pi_date,
        is_ordered=is_ordered or "0",
        items=items,
        confidence=confidence,
    )


def _extract_field(text: str, pattern: str) -> str | None:
    """
    从文本中提取指定模式后的值。
    支持两种方式：
    1. Label: Value 在同一行
    2. Label: 在一行，Value 在下一行同一列（常见于 .xls 跨行列）
    """
    match = re.search(rf'(?i){pattern}\s*[:：]\s*(.+)', text)
    if match:
        val = match.group(1).strip()
        if val:
            return val
    return None


def _extract_field_from_rows(rows: list[list[str]], patterns: list[str]) -> str | None:
    """
    从行列结构中直接查找 Label→Value 模式（跨行、同一列）。

    适用场景：.xls 文件中 "PI No.:" 在某单元格，下一行的同列单元格是值。
    """
    for row_idx, row in enumerate(rows):
        for col_idx, cell in enumerate(row):
            cell_str = str(cell).strip()
            for pattern in patterns:
                if re.search(rf'(?i){pattern}', cell_str):
                    # 优先返回当前格 after-colon 的值（不为空才用）
                    current_val = cell_str.split(":")[-1].strip()
                    if current_val:
                        return current_val
                    # 当前格 after-colon 为空，检查下一行同列
                    if row_idx + 1 < len(rows):
                        next_row = rows[row_idx + 1]
                        if col_idx < len(next_row):
                            next_val = str(next_row[col_idx]).strip()
                            # 过滤掉纯字段名行（如 "Payment Terms:"）
                            if next_val and not re.match(r'^[A-Za-z\s]+:\s*$', next_val):
                                return next_val
    return None


def _clean_number(value: str) -> float | None:
    """清洗并解析数值字段，移除 ¥ , 等符号"""
    if not value:
        return None
    value = value.replace("¥", "").replace(",", "").replace(" ", "").strip()
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _excel_serial_to_date(serial: float) -> str | None:
    """将 Excel 日期序列号转换为 YYYY-MM-DD 格式"""
    try:
        from datetime import datetime, timedelta
        # Excel 日期从 1900-01-01 开始（序列号 1）
        # 考虑 Excel 的 1900 年闰年 bug
        base = datetime(1899, 12, 30)
        return (base + timedelta(days=int(serial))).strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def parse_proforma_invoice(rows: list[list[str]]) -> PiContractUploadResponse:
    """
    解析 Proforma Invoice 格式文档（非表格型发票）。

    文档结构：
    - 公司名称 + 地址（头部）
    - Consignee 信息（客户名称、地址）
    - Date / PI No.
    - 产品明细表格（品名、数量、单价、金额）
    - 汇总信息（H.S.Code, Payment Terms, Bank 等）

    适用文件：Proforma Invoice HT260304E01 - Honghao Ella.xls
    """
    # 合并所有行为纯文本，便于正则匹配
    full_text = "\n".join(" | ".join(str(c).strip() for c in row) for row in rows)

    # ── 1. 找到 Consignee 区域起始行 ──────────────────────────────
    consignee_start = -1
    for ri, row in enumerate(rows):
        for cell in row:
            if re.search(r"Consignee\s*:", str(cell), re.IGNORECASE):
                consignee_start = ri
                break
        if consignee_start >= 0:
            break

    # ── 2. 从 Consignee 区域提取 Name 和 Address ──────────────────
    consignee_name = None
    consignee_address = None
    if consignee_start >= 0:
        name_row = -1
        for ri in range(consignee_start, min(consignee_start + 5, len(rows))):
            row = rows[ri]
            for cell in row:
                cell_str = str(cell).strip()
                m = re.match(r"(?i)Name\s*:\s*(.+)", cell_str)
                if m:
                    consignee_name = m.group(1).strip()
                    name_row = ri
                    break
        # 地址在 Name 行的下一行第 0 列
        if consignee_name and name_row >= 0 and name_row + 1 < len(rows):
            next_row = rows[name_row + 1]
            if next_row:
                addr = str(next_row[0]).strip()
                # 过滤掉日期序列号、标签行等
                if addr and not re.match(r"^\d{4,6}\.\d+$", addr) and not re.match(r"(?i)^(Name|Consignee|Date|PI\s*No|The\s+undersigned)", addr):
                    consignee_address = addr

    # ── 3. 提取 PI No ──────────────────────────────────────────────
    pi_no = _extract_field_from_rows(rows, [r"PI\s*No"])
    customer_code = None

    # ── 4. 提取日期 ──────────────────────────────────────────────
    pi_date_raw = _extract_field_from_rows(rows, [r"Date\s*:"])
    pi_date = None
    if pi_date_raw:
        try:
            serial = float(pi_date_raw)
            if serial > 40000:
                pi_date = _excel_serial_to_date(serial)
            else:
                pi_date = str(int(serial))
        except (ValueError, TypeError):
            pi_date = pi_date_raw

    # ── 5. 从表格表头提取价格条款（如 "CIF Jakarta(USD/Kg)"） ────
    price_term = None
    for row in rows:
        for cell in row:
            cell_str = str(cell).strip()
            m = re.search(r"\b(CIF|FOB|CFR|C\s*&\s*F|EXW|FCA|CPT|CIP|DAP|DPU)\b", cell_str, re.IGNORECASE)
            if m:
                price_term = m.group(1).upper()
                if price_term == "C&F":
                    price_term = "C&F"
                break
        if price_term:
            break

    # ── 6. 从 Payment terms and conditions 区域提取字段 ──────────
    payment_terms = None
    destination = None
    hs_code = None
    beneficiary_bank = None
    in_payment_section = False
    for ri, row in enumerate(rows):
        for cell in row:
            cell_str = str(cell).strip()
            if re.search(r"Payment\s+terms\s+and\s+conditions", cell_str, re.IGNORECASE):
                in_payment_section = True
            if in_payment_section:
                # Payment Terms: 100% T/T before shipment
                m = re.search(r"Payment\s+Terms?\s*:\s*(.+)", cell_str, re.IGNORECASE)
                if m:
                    payment_terms = m.group(1).strip()
                # Destination: Jakarta, Indonesia
                m = re.search(r"Destination\s*:\s*(.+)", cell_str, re.IGNORECASE)
                if m:
                    destination = m.group(1).strip()
                # H.S. Code: 3402.90.99
                m = re.search(r"H\.S\.\s*Code\s*:\s*(.+)", cell_str, re.IGNORECASE)
                if m:
                    hs_code = m.group(1).strip()
                # Beneficiary Bank: ...
                m = re.search(r"Beneficiary\s+Bank\s*:\s*(.+)", cell_str, re.IGNORECASE)
                if m:
                    beneficiary_bank = m.group(1).strip()

    # ── 7. 其他字段 ──────────────────────────────────────────────
    consignee_tel = None  # PI 合同中一般不包含收货人电话
    loading_port = _extract_field_from_rows(rows, [r"Port\s+of\s+loading\s*:", r"Loading\s+Port\s*:"])
    invoice_to = _extract_field_from_rows(rows, [r"INVOICE\s+TO\s*[:.]?\s*NAME\s*:", r"INVOICE\s+TO\s*:"])

    # 提取 Total Amount
    total_amount_str = _extract_field_from_rows(rows, [r"Total Amount\s*:"])
    total_amount = _clean_number(total_amount_str) if total_amount_str else None

    # 提取产品明细
    items: list[PiContractItemRow] = []
    table_started = False
    item_index = 0

    for row in rows:
        row_text = " | ".join(str(c).strip() for c in row)

        # 检测表格开始
        if "DESCRIPTION OF GOODS" in row_text or "QUANTITY" in row_text.upper():
            table_started = True
            continue
        if not table_started:
            continue

        # 检测到 REMARKS 或非产品行则停止
        if "REMARKS" in row_text or row_text.strip() == "":
            break

        # 解析产品行
        non_empty = [str(c).strip() for c in row if str(c).strip()]
        if len(non_empty) < 3:
            continue

        description = row[0].strip() if row[0] else ""
        if not description or "TOTAL" in description:
            continue

        quantity = None
        unit_price = None
        amount = None

        for cell in row:
            val = str(cell).strip()
            if not val or val in ("", " "):
                continue
            if _clean_number(val) is not None:
                if quantity is None:
                    quantity = _clean_number(val)
                elif unit_price is None:
                    unit_price = _clean_number(val)
                elif amount is None:
                    amount = _clean_number(val)

        item_index += 1
        notes_parts = []
        if payment_terms:
            notes_parts.append(f"付款条款: {payment_terms}")
        if beneficiary_bank:
            notes_parts.append(f"受益银行: {beneficiary_bank}")
        if destination:
            notes_parts.append(f"目的地: {destination}")

        items.append(PiContractItemRow(
            row_index=item_index,
            status="success",
            error_msg=None,
            internal_code=None,
            quantity=quantity,
            unit_price=unit_price,
            total_amount=amount,
            product_color=None,
            hs_code=hs_code,
            customs_name=description,
            customs_composition=None,
            order_customs_name=None,
            notes="; ".join(notes_parts) if notes_parts else None,
        ))

    if not pi_no:
        raise ValueError("无法识别 PI 编号，请确认文件格式")

    fields_recognized = sum(1 for v in [pi_no, customer_code, hs_code, pi_date, consignee_name, destination] if v)
    total_fields = 6
    confidence = ConfidenceInfo(
        recognized=fields_recognized,
        total=total_fields,
        percentage=f"{fields_recognized / total_fields * 100:.0f}%",
        failed_rows=0,
    )

    return PiContractUploadResponse(
        pi_no=pi_no or "",
        customer_code=customer_code,
        sales_person=None,
        pi_date=pi_date,
        is_ordered="0",
        consignee_name=consignee_name,
        consignee_address=consignee_address,
        consignee_tel=consignee_tel,
        destination=destination,
        loading_port=loading_port,
        price_term=price_term,
        payment_terms=payment_terms,
        invoice_to=invoice_to,
        items=items,
        confidence=confidence,
    )


def _read_xlsx_rows(file_path: str) -> list[list[str]]:
    wb = load_workbook(file_path, read_only=False, data_only=True)
    ws = wb.active
    rows: list[list[str]] = []
    for row in ws.iter_rows(values_only=True):
        rows.append([str(cell).strip() if cell is not None else "" for cell in row])
    wb.close()
    return rows


def _read_xls_rows(file_path: str) -> list[list[str]]:
    wb = xlrd.open_workbook(file_path, encoding_override="gbk")
    sheet = wb.sheet_by_index(0)
    rows = []
    for row_idx in range(sheet.nrows):
        row_values = sheet.row_values(row_idx)
        rows.append([str(cell).strip() if cell else "" for cell in row_values])
    wb.release_resources()
    return rows


def _read_xlsx_bytes(content: bytes) -> list[list[str]]:
    wb = load_workbook(io.BytesIO(content), read_only=False, data_only=True)
    ws = wb.active
    rows: list[list[str]] = []
    for row in ws.iter_rows(values_only=True):
        rows.append([str(cell).strip() if cell is not None else "" for cell in row])
    wb.close()
    return rows


def _read_xls_bytes(content: bytes) -> list[list[str]]:
    wb = xlrd.open_workbook(file_contents=content, encoding_override="gbk")
    sheet = wb.sheet_by_index(0)
    rows = []
    for row_idx in range(sheet.nrows):
        row_values = sheet.row_values(row_idx)
        rows.append([str(cell).strip() if cell else "" for cell in row_values])
    wb.release_resources()
    return rows


def _extract_text_from_pdf_bytes(content: bytes) -> str:
    """通过 OCR 从 PDF 内容提取纯文本（图片型扫描 PDF）"""
    pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_CMD", "/usr/bin/tesseract")
    doc = pymupdf.open(stream=content, filetype="pdf")
    texts = []
    for page in doc:
        mat = pymupdf.Matrix(3, 3)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_bytes))
        text = pytesseract.image_to_string(img, lang="chi_sim+eng", config="--psm 6")
        texts.append(text)
    doc.close()
    return "\n".join(texts)


def _parse_rows_from_text(text: str) -> list[list[str]]:
    """将纯文本转换为行列表（用于 Proforma Invoice 解析）"""
    lines = text.split("\n")
    rows = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        parts = re.split(r"\s{2,}", stripped)
        if parts and parts[0]:
            rows.append([p.strip() for p in parts])
    return rows


def parse_proforma_invoice_from_text(text: str, filename: str = "") -> PiContractUploadResponse:
    """从 OCR 文本直接解析 Proforma Invoice（用于 PDF）"""

    def scan(label_pat):
        """先找标签同行值，若值看起来像另一标签或为空则检查下一行"""
        idx = re.search(label_pat, text, re.IGNORECASE)
        if not idx:
            return None
        start = idx.end()
        after = text[start:]
        # 取本行剩余内容
        same = after.split(chr(10))[0].strip()
        # 如果同行值是另一个标签（纯大写+标点）或为空，尝试下一行
        if not same or re.match(r"^[A-Z]{2,}[:：;]?\s*$", same):
            rest = after.split(chr(10), 2)
            if len(rest) >= 2 and rest[1].strip():
                return rest[1].strip()
            return None
        return same

    def scan_next_line(label_pat):
        """标签在第N行，值在第N+1行"""
        idx = re.search(label_pat, text, re.IGNORECASE)
        if not idx:
            return None
        start = idx.end()
        after = text[start:]
        lines = after.split(chr(10), 2)
        return lines[1].strip() if len(lines) >= 2 and lines[1].strip() else None

    def scan_value(label_pat, value_pat):
        """找标签后, 在后续文本中搜索匹配 value_pat 的值（如日期、价格条款关键字）"""
        idx = re.search(label_pat, text, re.IGNORECASE)
        if not idx:
            return None
        # 在标签后 200 字符内找 value_pat
        window = text[idx.end(): idx.end() + 200]
        m = re.search(value_pat, window)
        return m.group(0).strip() if m else None

    # 1) PI/Order No — 多种 OCR 变形
    pi_no = (
        scan(r"ORDER\s+NO\s*[:;.]?") or
        scan(r"PI\s+NO\s*[:;.]?") or
        scan(r"PI\s+NUMBER\s*[:;.]?") or
        scan(r"ORDER\s+NUMBER\s*[:;.]?") or
        scan_next_line(r"ORDER\s+NO\s*[:;.]?") or
        scan_next_line(r"PI\s+NO\s*[:;.]?") or
        scan_next_line(r"'\s*PI\s+NO\s*;?") or
        # 最后一搏：扫描文本中第一个 HT 格式的订单号（支持8位或10位日期）
    (m.group(0) if (m := re.search(r"HT\d{8,10}[A-Z0-9]*", text)) else None)
    )
    # PDF文件从文件名提取PI号作为最终兜底
    if not pi_no and filename:
        fn_pi = re.search(r"HT\d{8,10}[A-Z0-9]*", os.path.basename(filename))
        pi_no = fn_pi.group(0) if fn_pi else None
    if pi_no and len(pi_no) >= 8:
        pass
    else:
        pi_no = None

    # 2) consignee NAME
    consignee_name = scan(r"NAME\s*:")
    if not consignee_name:
        # 尝试 NAME: 在行首
        m = re.search(r"(?mi)^NAME\s*:\s*(.+)$", text, re.MULTILINE)
        consignee_name = m.group(1).strip() if m else None

    # 3) consignee ADD — 剥离尾部可能拼接的日期（2列布局OCR会拼接右列）
    consignee_address = scan(r"ADD\s*:") or scan(r"ADDRESS\s*:")
    if consignee_address:
        consignee_address = re.sub(r"\s+\d{4}[-/.]\d{1,2}[-/.]\d{1,2}\s*$", "", consignee_address).strip()

    # 3b) consignee TEL
    consignee_tel = scan(r"TEL\s*:") or scan(r"Tel\s*:") or scan(r"Telephone\s*:")

    # 4) destination
    destination = scan(r"[0-9]\.\s*DEST\s*:") or scan(r"DEST\s*INAT\s*ION\s*:")

    # 5) date
    pi_date = scan_value(r"DATE\s*[:;]?", r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}") or scan(r"DATE\s*:")

    # 6) Port of loading (装货地)
    loading_port = scan(r"Port\s+of\s+loading\s*:") or scan(r"Loading\s+Port\s*:")

    # 7) Price Term (价格条款) — 兼容 "Price Term: CIF" 标签 与 表格表头 "CIF ISTANBUL" 独立行
    price_term = scan(r"Price\s+Term\s*:")
    if not price_term:
        # 兜底: 找表头的 CIF/FOB/C&F/CFR 关键字
        m = re.search(r"\b(CIF|FOB|CFR|C\s*&\s*F|EXW|FCA|CPT|CIP|DAP|DPU)\b", text)
        price_term = m.group(0) if m else None

    # 8) Invoice To (发票抬头)
    invoice_to = scan(r"INVOICE\s+TO\s*[:.]?\s*NAME\s*:") or scan(r"INVOICE\s+TO\s*:")

    # 产品明细行解析（支持品名单行+数字下一行的OCR分拆格式）
    items = []
    lines = text.split(chr(10))
    started = False
    idx2 = 0
    pending_desc = None  # 跨行：上一行品名，下一行数字
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if "DESCRIPTION" in s.upper() or "QUANTITY" in s.upper():
            started = True
            continue
        if not started:
            continue
        if s.startswith("1.") and "Packing" in s or s.startswith("TOTAL") or "Payment" in s:
            break

        # 尝试匹配「品名+数量+金额」单行（标准格式）
        m = re.match(r"(.+?)\s+([\d,]+\.?\d*)\s+\|?\s*([\d,]+\.?\d*)\s+\|?\s*US?\\\$?\s+([\d,]+\.?\d*)", s)
        if m:
            desc, qty_raw, price_raw, amount_raw = m.groups()
        else:
            # 尝试「两个数字」（数量+金额），结合 pending_desc 使用
            num_m = re.match(r"^([\d,]+\.?\d*)\s+([\d,]+\.?\d*)$", s)
            if num_m and pending_desc:
                qty_raw, amount_raw = num_m.groups()
                price_raw = None
                desc = pending_desc
            else:
                # 可能是品名行（无数字或文字为主），暂存为 pending_desc
                if not re.match(r"^[\d,. ]+$", s):
                    pending_desc = s
                continue

        try:
            qty_val = float(qty_raw.replace(",", "")) if qty_raw else None
            price_val = float(price_raw.replace(",", "")) if price_raw else None
            amount_val = float(amount_raw.replace(",", "")) if amount_raw else None
        except ValueError:
            qty_val = price_val = amount_val = None
        idx2 += 1
        notes = []
        if destination:
            notes.append(f"目的地: {destination}")
        items.append(PiContractItemRow(
            row_index=idx2,
            status="success",
            error_msg=None,
            internal_code=None,
            quantity=qty_val,
            unit_price=price_val,
            total_amount=amount_val,
            product_color=None,
            hs_code=None,
            customs_name=desc.strip() if desc else s,
            customs_composition=None,
            order_customs_name=None,
            notes="; ".join(notes) if notes else None,
        ))
        pending_desc = None  # 使用后清除

    if not pi_no:
        raise ValueError("无法识别 PI 编号，请确认文件格式")

    recognized = sum(1 for v in [pi_no] if v)
    confidence = ConfidenceInfo(
        recognized=recognized,
        total=1,
        percentage="100%" if recognized else "0%",
        failed_rows=0,
    )

    return PiContractUploadResponse(
        pi_no=pi_no or "",
        customer_code=None,
        sales_person=None,
        pi_date=pi_date,
        is_ordered="0",
        consignee_name=consignee_name,
        consignee_address=consignee_address,
        consignee_tel=consignee_tel,
        destination=destination,
        loading_port=loading_port,
        price_term=price_term,
        invoice_to=invoice_to,
        items=items,
        confidence=confidence,
    )

def _auto_parse_rows(rows: list[list[str]]) -> PiContractUploadResponse:
    """
    自动识别格式并解析：先尝试表格解析，失败则尝试 Proforma Invoice 格式。
    """
    try:
        return parse_pi_file(rows)
    except ValueError as e:
        if "缺少关键字段" in str(e) or "表头行无效" in str(e) or "无法从数据中提取 PI号" in str(e):
            return parse_proforma_invoice(rows)
        raise


def parse_file_path(file_path: str) -> PiContractUploadResponse:
    """解析PI文件路径，支持 .xlsx 和 .xls 格式"""
    import os
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".xlsx":
        rows = _read_xlsx_rows(file_path)
    elif ext == ".xls":
        rows = _read_xls_rows(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {ext}，仅支持 .xlsx 和 .xls")

    return _auto_parse_rows(rows)


def parse_pi_bytes(content: bytes, filename: str) -> PiContractUploadResponse:
    """直接从内存字节解析PI文件，支持 .xlsx / .xls / .pdf"""
    ext = os.path.splitext(filename)[1].lower() if filename else ""

    if ext == ".xlsx":
        rows = _read_xlsx_bytes(content)
        return _auto_parse_rows(rows)
    elif ext == ".xls":
        rows = _read_xls_bytes(content)
        return _auto_parse_rows(rows)
    elif ext == ".pdf":
        text = _extract_text_from_pdf_bytes(content)
        return parse_proforma_invoice_from_text(text, filename)
    else:
        raise ValueError(f"不支持的文件格式: {ext}，仅支持 .xlsx、.xls 和 .pdf")