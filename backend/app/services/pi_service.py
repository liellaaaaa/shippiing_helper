"""
PI Service - placeholder for BB-4 implementation.
This module will be fully implemented in BB-4.
"""
from typing import Optional


class PiService:
    """PI合同服务（暂存根）"""

    def __init__(self, db=None):
        self.db = db

    def save_contract(self, request):
        """保存PI合同（BB-4实现）"""
        raise NotImplementedError("PiService.save_contract 等待 BB-4 实现")

    def query_contracts(self, pi_no=None, customer_code=None, internal_code=None):
        """查询PI合同（BB-4实现）"""
        raise NotImplementedError("PiService.query_contracts 等待 BB-4 实现")