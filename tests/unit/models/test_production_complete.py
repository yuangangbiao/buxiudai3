# -*- coding: utf-8 -*-
"""
models/production.py 基础单元测试

覆盖模块:
- ProductionDAO
"""
import os
import sys
import pytest
from unittest.mock import Mock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestProductionDAOExists:
    """ProductionDAO 存在性测试"""

    def test_production_dao_class_exists(self):
        """测试ProductionDAO类存在"""
        from models.production import ProductionDAO
        assert ProductionDAO is not None

    def test_production_dao_has_create_method(self):
        """测试create方法存在"""
        from models.production import ProductionDAO
        assert hasattr(ProductionDAO, 'create')
        assert callable(ProductionDAO.create)


class TestProductionStatusConstants:
    """ProductionStatus 状态常量测试"""

    def test_production_status_pending_exists(self):
        """测试待排产状态存在"""
        from constants import ProductionStatus
        assert hasattr(ProductionStatus, 'PENDING')

    def test_production_status_in_progress_exists(self):
        """测试生产中状态存在"""
        from constants import ProductionStatus
        assert hasattr(ProductionStatus, 'IN_PROGRESS')

    def test_production_status_completed_exists(self):
        """测试已完成状态存在"""
        from constants import ProductionStatus
        assert hasattr(ProductionStatus, 'COMPLETED')


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
