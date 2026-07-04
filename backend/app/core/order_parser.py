"""Order paste parser - parses tab/newline delimited order data into ParsedOrderSchema."""

from app.schemas.order import ParsedOrderSchema, OrderItemSchema, SkippedRowSchema


# Column name aliases mapping internal field names to possible column header names
COLUMN_MAPPING: dict[str, list[str]] = {
    "order_no": ["订单号", "Order No", "PO", "PO Number", "PI No", "HT"],
    "order_date_placed": ["下单日期", "Order Date"],
    "customer_code": ["客户编号", "客户编码", "Customer Code", "Client Code"],
    "internal_code": ["内部编号", "Internal Code", "Product Code", "SKU"],
    "product_cn": ["产品中文名", "Product Name (CN)", "Description"],
    "spec_kg": ["规格kg", "Spec", "Specification"],
    "quantity_kg": ["订单量kg", "Quantity", "QTY (kg)", "Order Qty"],
    "unit_price": ["单价/kg", "Unit Price", "Price per kg"],
    "total_amount": ["总金额", "Total Amount", "Amount"],
    "salesperson": ["业务员", "Salesperson", "Sales Rep"],
    "merchandiser": ["跟单员", "Merchandiser", "Merch"],
    "customs_name": ["报关名称", "Customs Name"],
    "hs_code": ["H.S.Code", "HS Code", "H.S.", "海关编码"],
    "order_requirement": ["订单要求", "Order Requirement", "要求"],
    "order_date": ["交货日期", "Delivery Date", "交期", "下单日期", "Order Date"],
    "production_deadline": ["生产交期", "Production Deadline"],
    "shipment_method": ["出货方式", "Shipment Method", "出运方式"],
    "shipment_channel": ["出货渠道", "Shipment Channel"],
    "customer_name": ["客户名称", "Customer Name"],
    "is_ordered": ["是否下单", "Is Ordered"],
    "shipment_title": ["出货抬头", "Shipment Title"],
    "document_type": ["单据类型", "Document Type"],
    "product_color": ["产品颜色", "Color"],
    "notes": ["备注", "Notes"],
}


def normalize_column_name(col_name: str) -> str | None:
    """Strip spaces and match against aliases. Return field name or None."""
    stripped = col_name.strip()
    if not stripped:
        return None
    for field_name, aliases in COLUMN_MAPPING.items():
        if stripped in aliases:
            return field_name
    return None


# Standard Excel column order (23 fields) — used as positional fallback when no header
STANDARD_COLUMN_ORDER: list[str | None] = [
    'salesperson',           # 0  业务员
    'order_no',             # 1  订单号/PI号
    'shipment_title',       # 2  出货抬头
    'document_type',        # 3  单据类型
    'order_date_placed',   # 4  下单日期
    'merchandiser',         # 5  跟单员
    'customer_code',        # 6  客户编号
    'product_cn',           # 7  产品中文名
    'customs_name',         # 8  报关名称
    'internal_code',        # 9  内部编号
    'spec_kg',             # 10 规格kg
    'quantity_kg',         # 11 订单量kg
    'price_adjusted',       # 12 是否调价
    'has_sample',           # 13 有无样品
    'order_requirement',    # 14 订单要求
    'order_date',           # 15 交货日期
    None,                  # 16 审核（不解析）
    None,                  # 17 销售区域（不解析）
    None,                  # 18 订单号（重复列）
    None,                  # 19 出货抬头（重复列）
    None,                  # 20 单据类型（重复列）
    None,                  # 21 跟单员（重复列）
    None,                  # 22 下单日期（重复列）
]


def detect_delimiter(raw_text: str) -> str:
    """检测分隔符：优先 Tab，其次连续空格（8空格），最后换行。"""
    if "\t" in raw_text:
        return "\t"
    # 企业微信在线表格复制可能产生连续空格（通常8个）
    import re
    if re.search(r"  {4,}", raw_text):
        return "SPACE"
    return "\n"


# 空格分隔符的拆分函数
def split_by_spaces(line: str) -> list[str]:
    """按连续4+空格拆分一行（兼容企业微信粘贴格式）"""
    import re
    return [p.strip() for p in re.split(r"  {4,}", line)]


def split_lines(text: str) -> list[str]:
    """Split by newline to get rows, filter empty lines, strip each part."""
    lines = text.split("\n")
    return [line.strip() for line in lines if line.strip()]


def merge_quoted_lines(lines: list[str]) -> list[str]:
    """
    合并被 Excel 引号包围或无引号的单元格换行打断的行。

    问题：Excel 单元格含换行时，复制粘贴会把一行拆成多行。

    逻辑：
    1. 引号模式：若上一行"订单要求"列以 " 开头但未以 " 结尾 → 后续行并入
    2. 列数模式：若上一行有 >=10 列（完整数据行），当前行只有 1 列（无分隔符） → 并入上一行的订单要求
    """
    if not lines:
        return lines

    # 检测分隔符类型
    import re
    has_tab = any("\t" in line for line in lines[:5])
    use_space = not has_tab and any(re.search(r"  {4,}", line) for line in lines[:5])

    def split_cols(line: str) -> list[str]:
        if use_space:
            return split_by_spaces(line)
        return line.split("\t")

    def join_cols(parts: list[str]) -> str:
        if use_space:
            return "        ".join(parts)  # 8空格
        return "\t".join(parts)

    result: list[str] = []
    in_open_quote = False
    REQ_COL = 14
    FULL_ROW_MIN_COLS = 10

    i = 0
    while i < len(lines):
        line = lines[i]
        line_cols = split_cols(line)

        if result and in_open_quote:
            # 引号模式：合并续行
            if len(line_cols) == 1 and not line.endswith('"'):
                prev_parts = split_cols(result[-1])
                if len(prev_parts) > REQ_COL:
                    prev_parts[REQ_COL] = prev_parts[REQ_COL] + "\n" + line.strip()
                else:
                    prev_parts[-1] = prev_parts[-1] + "\n" + line.strip()
                result[-1] = join_cols(prev_parts)
                i += 1
                continue
            elif line.endswith('"') and not line.startswith('"'):
                prev_parts = split_cols(result[-1])
                if len(prev_parts) > REQ_COL:
                    prev_parts[REQ_COL] = prev_parts[REQ_COL] + "\n" + line.strip()
                else:
                    prev_parts[-1] = prev_parts[-1] + "\n" + line.strip()
                result[-1] = join_cols(prev_parts)
                in_open_quote = False
                i += 1
                continue
            elif len(line_cols) > 1 and line_cols[0].endswith('"') and not line_cols[0].startswith('"'):
                prev_parts = split_cols(result[-1])
                if len(prev_parts) > REQ_COL:
                    prev_parts[REQ_COL] = prev_parts[REQ_COL] + "\n" + line_cols[0]
                else:
                    prev_parts[-1] = prev_parts[-1] + "\n" + line_cols[0]
                result[-1] = join_cols(prev_parts)
                rest = join_cols(line_cols[1:])
                if rest.strip():
                    result.append(rest)
                in_open_quote = False
                i += 1
                continue

        # 列数模式：上一行是完整数据行，当前行只有 1 列（无分隔符） → 续行
        if result:
            prev_parts = split_cols(result[-1])
            if len(line_cols) == 1 and len(prev_parts) >= FULL_ROW_MIN_COLS:
                continuation = line.strip()
                if continuation:
                    if len(prev_parts) > REQ_COL:
                        prev_parts[REQ_COL] = prev_parts[REQ_COL] + "\n" + continuation
                    else:
                        prev_parts[-1] = prev_parts[-1] + "\n" + continuation
                    result[-1] = join_cols(prev_parts)
                    i += 1
                    continue

        # 引号模式检查：若上一行的订单要求列以 " 开头但未以 " 结尾
        if result:
            prev_parts = split_cols(result[-1])
            req_field = prev_parts[REQ_COL] if len(prev_parts) > REQ_COL else prev_parts[-1]
            if req_field.startswith('"') and not req_field.endswith('"'):
                in_open_quote = True
                # 当前行也要并入（不 append）
                if len(prev_parts) > REQ_COL:
                    prev_parts[REQ_COL] = prev_parts[REQ_COL] + "\n" + line.strip()
                else:
                    prev_parts[-1] = prev_parts[-1] + "\n" + line.strip()
                result[-1] = join_cols(prev_parts)
                i += 1
                continue

        result.append(line)
        i += 1

    return result


def parse_header(header_line: str, delimiter: str) -> dict[int, str]:
    """Parse first row as header, return {col_index: field_name} dict."""
    parts = [p.strip() for p in header_line.split(delimiter)]
    col_map: dict[int, str] = {}
    for i, part in enumerate(parts):
        field_name = normalize_column_name(part)
        if field_name is not None:
            col_map[i] = field_name
    return col_map


def build_positional_map(col_count: int) -> dict[int, str]:
    """Build column map from standard Excel column order (positional fallback)."""
    col_map: dict[int, str] = {}
    for i, field_name in enumerate(STANDARD_COLUMN_ORDER):
        if field_name is not None and i < col_count:
            col_map[i] = field_name
    return col_map


def parse_row(parts: list[str], col_map: dict[int, str]) -> dict[str, str | float | None]:
    """Map row parts to field names using col_map."""
    row_data: dict[str, str | float | None] = {}
    for col_idx, field_name in col_map.items():
        if col_idx < len(parts):
            value = parts[col_idx].strip()
            if field_name in ("spec_kg", "quantity_kg", "unit_price", "total_amount"):
                parsed = _parse_float(value)
                row_data[field_name] = parsed
            else:
                row_data[field_name] = value if value else None
        else:
            row_data[field_name] = None
    return row_data


def _parse_float(value: str) -> float | None:
    """Safe float parsing, return None on failure."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def parse_pasted_data(
    raw_text: str,
) -> tuple[list[ParsedOrderSchema], list[SkippedRowSchema], str | None]:
    """
    Parse pasted order data.

    Returns:
        tuple of (list of ParsedOrderSchema, list of SkippedRowSchema, warning string or None)
    """
    if not raw_text.strip():
        return [], [], None

    # 先修复引号打断的行，再检测分隔符
    lines = split_lines(raw_text)
    lines = merge_quoted_lines(lines)

    if not lines:
        return [], [], None

    delimiter = detect_delimiter(lines[0])

    # 统一拆分函数：Tab 用 split("\t")，空格用 split_by_spaces
    def split_line(line: str) -> list[str]:
        if delimiter == "SPACE":
            return split_by_spaces(line)
        return line.split(delimiter)

    # Parse header — fall back to positional mapping if header yields < 2 mapped fields
    col_map = parse_header(lines[0], delimiter)
    has_header = len(col_map) >= 2
    if not has_header:
        col_count = len(split_line(lines[0]))
        # Short format (8 cols): order_no | customer_code | internal_code | product | spec_kg | qty_kg | unit_price | total_amount
        # Long format (>=10 cols): full 23-column standard, first row is data
        if col_count == 8:
            # Map to short format directly: order_no=0, customer_code=1, internal_code=2, ...
            SHORT_FORMAT = ["order_no", "customer_code", "internal_code", "product_cn", "spec_kg", "quantity_kg", "unit_price", "total_amount"]
            col_map = {i: v for i, v in enumerate(SHORT_FORMAT)}
            has_header = False   # 8-col short format has no header row — first line is data
        else:
            # For long rows: treat first line as data row
            col_map = build_positional_map(col_count)

    # Parse data rows — skip header row if present
    raw_items: list[dict] = []
    skipped_rows: list[SkippedRowSchema] = []
    data_start = 1 if has_header else 0

    for i, line in enumerate(lines[data_start:], start=data_start + 2):
        parts = [p.strip() for p in split_line(line)]
        row_data = parse_row(parts, col_map)

        order_no = row_data.get("order_no")
        internal_code = row_data.get("internal_code")

        if not order_no or not internal_code:
            skipped_rows.append(
                SkippedRowSchema(
                    line_index=i,
                    reason="order_no or internal_code is empty",
                    raw_data=parts,
                )
            )
        else:
            raw_items.append(row_data)

    # Batch dedup: key = (order_no, internal_code), later overwrites earlier
    deduped: dict[tuple[str, str], dict] = {}
    duplicate_keys: set[tuple[str, str]] = set()
    warnings: list[str] = []
    for item in raw_items:
        key = (str(item["order_no"]), str(item["internal_code"]))
        if key in deduped:
            duplicate_keys.add(key)
        deduped[key] = item

    if duplicate_keys:
        warnings.append(f"Batch dedup: {len(duplicate_keys)} duplicate(s) overwritten")

    # Aggregate by order_no
    orders_by_no: dict[str, ParsedOrderSchema] = {}

    for item in deduped.values():
        order_no = str(item["order_no"])

        if order_no not in orders_by_no:
            orders_by_no[order_no] = ParsedOrderSchema(
                order_no=order_no,
                customer_code=item.get("customer_code"),
                salesperson=item.get("salesperson"),
                items=[],
            )

        # Build OrderItemSchema from item data
        order_item = OrderItemSchema(
            internal_code=str(item["internal_code"]),
            product_cn=item.get("product_cn"),
            spec_kg=item.get("spec_kg") if isinstance(item.get("spec_kg"), float) else None,
            quantity_kg=item.get("quantity_kg") if isinstance(item.get("quantity_kg"), float) else None,
            unit_price=item.get("unit_price") if isinstance(item.get("unit_price"), float) else None,
            total_amount=item.get("total_amount") if isinstance(item.get("total_amount"), float) else None,
            customs_name=item.get("customs_name"),
            hs_code=item.get("hs_code"),
            order_requirement=item.get("order_requirement"),
            order_date=item.get("order_date"),
            order_date_placed=item.get("order_date_placed"),
            production_deadline=item.get("production_deadline"),
            shipment_method=item.get("shipment_method"),
            shipment_channel=item.get("shipment_channel"),
            salesperson=item.get("salesperson"),
            merchandiser=item.get("merchandiser"),
            price_adjusted=item.get("price_adjusted"),
            has_sample=item.get("has_sample"),
            order_confirmed=item.get("order_confirmed"),
            spec_abnormal=item.get("spec_abnormal"),
            shipment_title=item.get("shipment_title"),
            document_type=item.get("document_type"),
        )
        orders_by_no[order_no].items.append(order_item)

    # Check for header conflicts within each order
    for order_no, order in orders_by_no.items():
        first_customer = order.items[0].product_cn  # using product_cn as placeholder for customer
        first_salesperson = None
        for item in order.items:
            # Check if any item has different customer code or salesperson info
            pass  # Already handled via item-level fields
        # header_conflict_warning logic would check across items, not needed here

    # Inject customs name matching logic before returning
    from app.services.customs_name_service import CustomsNameService
    from app.core.config import CUSTOMS_CODES_JSON

    customs_svc = CustomsNameService.get_instance(CUSTOMS_CODES_JSON)

    for order in orders_by_no.values():
        for item in order.items:
            json_data = customs_svc.lookup(item.internal_code)
            if json_data is None:
                item.customs_match_status = "not_found"
                continue

            # Collect conflict types
            conflict_types = []
            if item.customs_name and item.customs_name != json_data.get("customs_name"):
                conflict_types.append("customs_name")
            if item.hs_code and item.hs_code != json_data.get("product_code"):
                conflict_types.append("hs_code")

            if conflict_types:
                item.customs_match_status = "conflict"
                if "customs_name" in conflict_types:
                    item.conflict_customs_name = json_data.get("customs_name")
                if "hs_code" in conflict_types:
                    item.conflict_hs_code = json_data.get("product_code")
                # Fill other fields even in conflict
                item.customs_ingredients = json_data.get("components")
                item.product_code = json_data.get("product_code")
                item.product_appearance = json_data.get("product_appearance")
            elif not item.customs_name:
                # Empty - auto-fill
                item.customs_name = json_data.get("customs_name")
                item.customs_ingredients = json_data.get("components")
                item.product_code = json_data.get("product_code")
                item.product_appearance = json_data.get("product_appearance")
                item.hs_code = item.hs_code or json_data.get("product_code")
                item.customs_match_status = "filled"
            else:
                # Perfect match
                item.customs_match_status = "matched"
                item.hs_code = item.hs_code or json_data.get("product_code")
                item.customs_ingredients = json_data.get("components")
                item.product_code = json_data.get("product_code")
                item.product_appearance = json_data.get("product_appearance")

    return list(orders_by_no.values()), skipped_rows, warnings[0] if warnings else None


# ── PI合同表解析（17列，企业微信在线表格格式）───────────────────────────────────
# 实测样本列位置（17列，0-indexed）：
#  Col  0: 客户编码 (WA231)
#  Col  1: PI号 (HT260630SZ)
#  Col  2: 业务员 (邓素珍)
#  Col  3: 出货抬头 (宏昊)
#  Col  4: 运输方式 (海运)
#  Col  5: 数量 (2500)
#  Col  6: 单价 (1.73)
#  Col  7: 金额 (4325)
#  Col  8: 内部编码 (B-40EA)
#  Col  9: 产品颜色 (棕黑色粘稠液体)
#  Col 10: 海关编码/HS Code (3402900000)
#  Col 11: 报关品名 (固色剂)
#  Col 12: 报关成分 (双酚S：80-09-1；52%...)
#  Col 13: 日期 (2026年6月30日)
#  Col 14: 付款方式 (LC0)
#  Col 15: 订单确认时间 (2026-07-02 21:52)
#  Col 16: 是否下单 (是/否)

PI_CONTRACT_COL_ORDER: list[str | None] = [
    "customer_code",          # 0 客户编码
    "pi_no",                  # 1 PI号
    "salesperson",             # 2 业务员
    "shipment_title",          # 3 出货抬头（实测有数据，设计文档标为空）
    "shipment_method",          # 4 运输方式（实测有数据，设计文档标为空）
    "quantity_kg",            # 5 数量
    "unit_price",             # 6 单价
    "total_amount",           # 7 金额
    "internal_code",          # 8 内部编码
    "product_color",          # 9 产品颜色
    "hs_code",                # 10 海关编码
    "customs_name",           # 11 报关品名
    "customs_ingredients",    # 12 报关成分
    "pi_date",                # 13 日期
    "payment_terms",          # 14 付款方式（实测有数据LC0）
    "order_confirm_datetime", # 15 订单确认时间（2026-07-02 21:52）
    "is_ordered",             # 16 是否下单
]


def parse_pi_contract_table(
    raw_text: str,
) -> tuple[list[ParsedOrderSchema], list[SkippedRowSchema], str | None]:
    """
    解析 PI 合同表粘贴数据（企业微信在线表格格式，17列）。

    与 parse_pasted_data 共用分隔符检测、引号修复逻辑，
    仅列映射和字段聚合规则不同。
    """
    if not raw_text.strip():
        return [], [], None

    lines = split_lines(raw_text)
    lines = merge_quoted_lines(lines)
    if not lines:
        return [], [], None

    delimiter = detect_delimiter(lines[0])

    def split_line(line: str) -> list[str]:
        if delimiter == "SPACE":
            return split_by_spaces(line)
        return line.split(delimiter)

    # 尝试按 header 解析（需要 ≥2 个可识别列名）
    col_map = parse_header(lines[0], delimiter)
    has_header = len(col_map) >= 2

    # 如果没有可用 header，用位置映射
    if not has_header:
        col_count = len(split_line(lines[0]))
        col_map = _build_pi_contract_positional_map(col_count)

    data_start = 1 if has_header else 0
    raw_items: list[dict] = []
    skipped_rows: list[SkippedRowSchema] = []

    for i, line in enumerate(lines[data_start:], start=data_start + 2):
        parts = [p.strip() for p in split_line(line)]
        row_data = _parse_pi_contract_row(parts, col_map)

        pi_no = row_data.get("pi_no")
        internal_code = row_data.get("internal_code")

        if not pi_no or not internal_code:
            skipped_rows.append(
                SkippedRowSchema(
                    line_index=i,
                    reason="pi_no or internal_code is empty",
                    raw_data=parts,
                )
            )
        else:
            raw_items.append(row_data)

    # 批次内去重
    deduped: dict[tuple[str, str], dict] = {}
    duplicate_keys: set[tuple[str, str]] = set()
    warnings: list[str] = []
    for item in raw_items:
        key = (str(item["pi_no"]), str(item["internal_code"]))
        if key in deduped:
            duplicate_keys.add(key)
        deduped[key] = item
    if duplicate_keys:
        warnings.append(f"批次去重：{len(duplicate_keys)} 个重复项被覆盖")

    # 按 pi_no 聚合
    orders_by_no: dict[str, ParsedOrderSchema] = {}

    for item in deduped.values():
        pi_no = str(item["pi_no"])
        if pi_no not in orders_by_no:
            orders_by_no[pi_no] = ParsedOrderSchema(
                order_no=pi_no,
                customer_code=item.get("customer_code"),
                salesperson=item.get("salesperson"),
                items=[],
            )

        order_item = OrderItemSchema(
            internal_code=str(item["internal_code"]),
            product_cn=None,  # 销售订单表提供
            spec_kg=None,
            quantity_kg=item.get("quantity_kg"),
            unit_price=item.get("unit_price"),   # PI合同表 Col 6 有单价
            total_amount=item.get("total_amount"),
            customs_name=item.get("customs_name"),
            hs_code=item.get("hs_code"),
            customs_ingredients=item.get("customs_ingredients"),
            product_appearance=item.get("product_color"),  # Col 9
            shipment_method=item.get("shipment_method"),    # Col 4 运输方式
        )
        orders_by_no[pi_no].items.append(order_item)

    return list(orders_by_no.values()), skipped_rows, warnings[0] if warnings else None


def _build_pi_contract_positional_map(col_count: int) -> dict[int, str]:
    """Build column map from PI contract table positional order."""
    col_map: dict[int, str] = {}
    for i, field_name in enumerate(PI_CONTRACT_COL_ORDER):
        if field_name is not None and i < col_count:
            col_map[i] = field_name
    return col_map


def _parse_pi_contract_row(
    parts: list[str], col_map: dict[int, str]
) -> dict[str, str | float | None]:
    """Parse a single PI contract table row."""
    row_data: dict[str, str | float | None] = {}
    for col_idx, field_name in col_map.items():
        if col_idx < len(parts):
            value = parts[col_idx].strip()
            if field_name in ("quantity_kg", "total_amount", "unit_price"):
                row_data[field_name] = _parse_float(value)
            else:
                row_data[field_name] = value if value else None
        else:
            row_data[field_name] = None
    return row_data