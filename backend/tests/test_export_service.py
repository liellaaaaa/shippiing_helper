import pytest
from app.services.export_service import ExportService


def test_generate_excel_bytes():
    """测试 Excel 文件流生成"""
    service = ExportService()

    data = [
        {
            "order_no": "HT260529E01",
            "customer_code": "TOA-DOVECHEM",
            "salesperson": "张三",
            "internal_code": "SILI-001",
            "product_cn": "有机硅柔软剂",
            "order_quantity": 2400.0,
            "pi_quantity": 2400.0,
            "association_status": "full",
            "diff_status": "一致",
        }
    ]

    result = service.generate_excel_bytes(data)
    assert result is not None
    assert len(result) > 0
    # 验证是有效的 xlsx 文件（以 PK 开头，即 ZIP 文件）
    assert result[:2] == b'PK'


def test_generate_filename():
    """测试文件名生成"""
    service = ExportService()
    filename = service.generate_filename()
    assert filename.startswith("数据看板_")
    assert filename.endswith(".xlsx")