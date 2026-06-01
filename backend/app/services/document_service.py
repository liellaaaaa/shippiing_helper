# backend/app/services/document_service.py
import openpyxl
from typing import Tuple


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