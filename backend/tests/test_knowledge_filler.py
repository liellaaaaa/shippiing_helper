import pytest
from unittest.mock import patch, MagicMock
from app.core.knowledge_filler import auto_fill_knowledge
from app.schemas.order import OrderItemSchema


class TestAutoFillKnowledge:
    """知识库匹配测试"""

    def test_fill_from_internal_code(self):
        """internal_code 精确命中时直接填充"""
        mock_knowledge = MagicMock()
        mock_knowledge.hs_code = "3910000000"
        mock_knowledge.customs_name = "有机硅柔软剂"

        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_knowledge

        with patch("app.core.knowledge_filler.SessionLocal") as mock_db:
            mock_db.return_value.query.return_value = mock_query
            mock_db.return_value.close = MagicMock()

            item = OrderItemSchema(internal_code="SILI-001", product_cn="有机硅柔软剂")
            auto_fill_knowledge(item, None)

            assert item.hs_code == "3910000000"
            assert item.customs_name == "有机硅柔软剂"

    def test_hs_code_length_warning(self):
        """H.S.Code 不足10位时应有警告"""
        item = OrderItemSchema(internal_code="SILI-001", hs_code="3910")
        auto_fill_knowledge(item, None)
        assert item.hs_code_warning is not None
        assert "位数不足" in item.hs_code_warning

    def test_customs_name_auto_generate(self):
        """知识库无匹配时自动生成报关品名"""
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None

        with patch("app.core.knowledge_filler.SessionLocal") as mock_db:
            mock_db.return_value.query.return_value = mock_query
            mock_db.return_value.close = MagicMock()

            item = OrderItemSchema(internal_code="NEW-CODE", product_cn="改性硅油", spec_kg=25)
            auto_fill_knowledge(item, None)

            assert "改性硅油" in item.customs_name
            assert item.warning is not None
            assert "自动生成" in item.warning

    def test_hs_code_from_pi_data_takes_priority(self):
        """PI 数据中的 H.S.Code 优先级最高"""
        item = OrderItemSchema(internal_code="SILI-001")
        pi_data = {"hs_code": "3910000000", "customs_name": "PI报关名"}
        auto_fill_knowledge(item, pi_data)
        assert item.hs_code == "3910000000"