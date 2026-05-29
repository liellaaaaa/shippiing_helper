"""
PI文件解析器 - 从Excel文件中提取PI合同数据

支持 .xlsx (openpyxl) 和 .xls (xlrd) 格式
"""

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
    "customer_code": ["客户编码", "客户编号"],
    "pi_no": ["PI号", "PI NO.", "Proforma Invoice No."],
    "sales_person": ["业务员", "Salesperson"],
    "pi_date": ["日期", "Date", "PI Date"],
    "order_id": ["销售订单号", "Sales Order No.", "SO No."],
    "internal_code": ["内部编码", "Item Code", "SKU", "产品代码"],
    "quantity": ["数量", "QTY", "Quantity"],
    "unit_price": ["单价", "Unit Price", "Price"],
    "total_amount": ["金额", "Amount", "Total"],
    "product_color": ["产品颜色", "Color"],
    "hs_code": ["海关编码", "H.S. Code", "HS Code"],
    "customs_name": ["报关品名", "Customs Name"],
    "customs_composition": ["报关成分", "Ingredients"],
    "order_customs_name": ["填写订单报关品名", "Order Customs Name"],
    "is_ordered": ["是否下单", "Is Ordered"],
    "notes": ["文本", "Notes", "Remark"],
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
    解析PI文件数据（内存中的行列表）

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

    # 提取表头级别的公共字段
    def get_header_value(field_name: str) -> Optional[str]:
        for idx, col_idx in enumerate(header_row):
            if _normalize_column_name(col_idx) == field_name:
                if idx + 1 < len(rows[1]) if len(rows) > 1 else False:
                    return rows[1][idx]
        return None

    # 从第一行数据提取公共信息
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

        # 提取各字段值
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
                    # 数值字段
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
                    # 字符串字段
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

        # 判断行状态
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

    # 计算置信度
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


def parse_file_path(file_path: str) -> PiContractUploadResponse:
    """
    解析PI文件路径，支持 .xlsx 和 .xls 格式

    参数:
        file_path: 文件绝对路径

    返回:
        PiContractUploadResponse
    """
    import os

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".xlsx":
        wb = load_workbook(file_path, read_only=True, data_only=True)
        ws = wb.active
        rows: list[list[str]] = []
        for row in ws.iter_rows(values_only=True):
            rows.append([str(cell).strip() if cell is not None else "" for cell in row])
        wb.close()
    elif ext == ".xls":
        wb = xlrd.open_workbook(file_path, encoding_override="utf-8")
        sheet = wb.sheet_by_index(0)
        rows = []
        for row_idx in range(sheet.nrows):
            row_values = sheet.row_values(row_idx)
            rows.append([str(cell).strip() if cell else "" for cell in row_values])
        wb.release_resources()
    else:
        raise ValueError(f"不支持的文件格式: {ext}，仅支持 .xlsx 和 .xls")

    return parse_pi_file(rows)