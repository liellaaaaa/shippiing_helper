# backend/app/services/document_service.py
import openpyxl
from typing import Tuple
import os, time, base64
from io import BytesIO
from docx import Document
from app.core.config import TEMPLATES, DOCS_DIR
from app.services.msds_service import MSDSService
from app.database import SessionLocal
from app.models.order_pi_record import OrderPiRecord
from app.models.pi_contract import PiContract


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

    def generate_booking(self, order_id: int) -> tuple[bytes, str, str]:
        template_path = TEMPLATES["booking"]
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Booking template not found: {template_path}")
        wb = openpyxl.load_workbook(template_path)
        ws = wb.active
        db = SessionLocal()
        try:
            record = db.query(OrderPiRecord).filter(OrderPiRecord.id == order_id).first()
            pi = None
            if record and record.pi_no:
                pi = db.query(PiContract).filter(PiContract.pi_no == record.pi_no).first()
            shipper_row, shipper_col = find_marker_cell(ws, "{{MARK_SHIPPER}}")
            port_row, port_col = find_marker_cell(ws, "{{MARK_PORT}}")
            goods_row, goods_col = find_marker_cell(ws, "{{MARK_GOODS_TABLE}}")
            ws.cell(shipper_row, shipper_col + 1).value = "HONGHAO CHEMICAL CO., LTD."
            ws.cell(shipper_row, shipper_col + 2).value = "广东省清远市清新区太和镇百合花园综合楼"
            ws.cell(shipper_row, shipper_col + 3).value = "TEL: 0763-6866888"
            if pi:
                ws.cell(shipper_row + 1, shipper_col + 1).value = pi.consignee_name or ""
                ws.cell(shipper_row + 1, shipper_col + 2).value = pi.consignee_address or ""
                ws.cell(port_row, port_col + 1).value = pi.destination or ""
            if record:
                items = [(record.product_cn or "", record.product_en or "",
                          record.hs_code or "", record.gross_weight_kg or 0, record.volume_cbm or 0)]
            else:
                items = []
            for i, (cn, en, hs, gw, vol) in enumerate(items):
                r = goods_row + i
                ws.cell(r, goods_col).value = cn
                ws.cell(r, goods_col + 1).value = en
                ws.cell(r, goods_col + 2).value = hs
                ws.cell(r, goods_col + 3).value = gw
                ws.cell(r, goods_col + 4).value = vol
            clear_markers(ws)
            buf = BytesIO()
            wb.save(buf)
            content = buf.getvalue()
        finally:
            db.close()
        doc_key = f"booking_{order_id}_{int(time.time())}"
        doc_path = os.path.join(DOCS_DIR, doc_key + ".xlsx")
        os.makedirs(DOCS_DIR, exist_ok=True)
        with open(doc_path, "wb") as f:
            f.write(content)
        return content, doc_key, base64.b64encode(content).decode()

    def generate_loi(self, order_id: int, pi_no: str) -> tuple[bytes, str, str]:
        template_path = TEMPLATES["loi"]
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"LOI template not found: {template_path}")
        db = SessionLocal()
        try:
            record = db.query(OrderPiRecord).filter(OrderPiRecord.id == order_id).first()
            pi = db.query(PiContract).filter(PiContract.pi_no == pi_no).first() if pi_no else None
            doc = Document(template_path)
            replacements = {
                "{{shipper}}": "HONGHAO CHEMICAL CO., LTD.",
                "{{consignee}}": pi.consignee_name if pi else "",
                "{{consignee_address}}": pi.consignee_address if pi else "",
                "{{port_of_discharge}}": pi.destination if pi else "",
                "{{product_name_cn}}": record.product_cn if record else "",
                "{{product_name_en}}": record.product_en if record else "",
                "{{hs_code}}": record.hs_code if record else "",
                "{{gross_weight}}": str(record.gross_weight_kg) if record and record.gross_weight_kg else "",
                "{{volume}}": str(record.volume_cbm) if record and record.volume_cbm else "",
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
        doc_key = f"loi_{order_id}_{int(time.time())}"
        doc_path = os.path.join(DOCS_DIR, doc_key + ".docx")
        with open(doc_path, "wb") as f:
            f.write(content)
        return content, doc_key, base64.b64encode(content).decode()

    def generate_msds(self, product_name: str) -> tuple[bytes, str, str]:
        template_path = TEMPLATES["msds"]
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"MSDS template not found: {template_path}")
        db = SessionLocal()
        try:
            msds_index = self.msds_service.get_msds_by_product(product_name, db)
            doc = Document(template_path)
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
        doc_key = f"msds_{product_name}_{int(time.time())}"
        doc_path = os.path.join(DOCS_DIR, doc_key + ".docx")
        with open(doc_path, "wb") as f:
            f.write(content)
        return content, doc_key, base64.b64encode(content).decode()