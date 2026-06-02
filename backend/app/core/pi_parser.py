"""
PI文件解析器 - 从Excel文件中提取PI合同数据

支持两种格式：
1. 表格格式（外贸订单PI合同.xlsx）：标准行列格式，有表头
2. Proforma Invoice 格式（.xls）：自由文本型发票，含产品表格和银行信息
"""

import re
import io
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

    # 使用跨行提取器从行列结构中查找 Label→Value 模式
    pi_no = _extract_field_from_rows(rows, [r"PI\s*No"])
    # customer_code 不从 PI 提取（PI 文件无此字段，客户编号来自订单粘贴数据）
    customer_code = None

    # 提取日期：Date: 2026/3/4（可能是 Excel 序列号 46085 = 2026-03-29）
    pi_date_raw = _extract_field_from_rows(rows, [r"Date\s*:"])
    pi_date = None
    if pi_date_raw:
        try:
            serial = float(pi_date_raw)
            # 如果是 Excel 日期序列号（> 40000），转换为日期格式
            if serial > 40000:
                pi_date = _excel_serial_to_date(serial)
            else:
                pi_date = str(int(serial))
        except (ValueError, TypeError):
            pi_date = pi_date_raw  # fallback to raw string

    # 提取 H.S. Code
    hs_code = _extract_field_from_rows(rows, [r"H\.S\.\s*Code"])

    # 提取 Beneficiary Bank 信息
    beneficiary_bank = _extract_field_from_rows(rows, [r"Beneficiary Bank\s*:"])

    # 提取 Payment Terms
    payment_terms = _extract_field_from_rows(rows, [r"Payment Terms\s*:"])

    # 提取 Destination
    destination = _extract_field_from_rows(rows, [r"Destination\s*:"])

    # 提取收货人信息（Name: 后紧跟公司名）
    consignee_name = _extract_field_from_rows(rows, [r"Name\s*:"])

    # 收货人地址：Address: 或 Add.:
    consignee_address = _extract_field_from_rows(rows, [r"Address\s*:", r"Add\.\s*:"])

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
        destination=destination,
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
    wb = xlrd.open_workbook(file_path, encoding_override="utf-8")
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
    wb = xlrd.open_workbook(file_contents=content, encoding_override="utf-8")
    sheet = wb.sheet_by_index(0)
    rows = []
    for row_idx in range(sheet.nrows):
        row_values = sheet.row_values(row_idx)
        rows.append([str(cell).strip() if cell else "" for cell in row_values])
    wb.release_resources()
    return rows


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
    """直接从内存字节解析PI文件，不写入临时文件"""
    import os
    ext = os.path.splitext(filename)[1].lower() if filename else ""

    if ext == ".xlsx":
        rows = _read_xlsx_bytes(content)
    elif ext == ".xls":
        rows = _read_xls_bytes(content)
    else:
        raise ValueError(f"不支持的文件格式: {ext}，仅支持 .xlsx 和 .xls")

    return _auto_parse_rows(rows)