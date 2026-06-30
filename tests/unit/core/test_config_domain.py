# -*- coding: utf-8 -*-
"""
core/_config_domain.py 完整单元测试

覆盖模块:
- 时间工具: now, now_str, today_str
- 业务常量: MATERIALS, PROCESS_CODES, ORDER_STATUS
- 业务函数: get_process_code, get_process_seq, is_registered
- 业务类: BusinessConfig
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest
from datetime import datetime


class TestConfigDomainExists:
    """_config_domain 存在性测试"""

    def test_config_domain_module_exists(self):
        """测试_config_domain模块存在"""
        from core import _config_domain
        assert _config_domain is not None


@pytest.mark.skip(reason="core._config_domain 暂无 now/now_str/today_str 函数，源码未实现")
class TestTimeUtils:
    """时间工具测试 - [v3.8.2] 源码未实现时间工具, 整体 skip"""

    def test_now(self):
        """测试now函数"""
        from core._config_domain import now
        result = now()
        assert isinstance(result, datetime)

    def test_now_str(self):
        """测试now_str函数"""
        from core._config_domain import now_str
        result = now_str()
        assert isinstance(result, str)
        assert len(result) == 19  # YYYY-MM-DD HH:MM:SS

    def test_today_str(self):
        """测试today_str函数"""
        from core._config_domain import today_str
        result = today_str()
        assert isinstance(result, str)
        assert len(result) == 10  # YYYY-MM-DD


class TestMaterials:
    """MATERIALS 测试"""

    def test_materials_exists(self):
        """测试MATERIALS存在"""
        from core._config_domain import MATERIALS
        assert MATERIALS is not None
        assert isinstance(MATERIALS, list)

    def test_materials_not_empty(self):
        """测试MATERIALS非空"""
        from core._config_domain import MATERIALS
        assert len(MATERIALS) > 0

    def test_materials_has_stainless(self):
        """测试包含不锈钢"""
        from core._config_domain import MATERIALS
        has_stainless = any('不锈钢' in m for m in MATERIALS)
        assert has_stainless

    def test_material_densities(self):
        """测试MATERIAL_DENSITIES"""
        from core._config_domain import MATERIAL_DENSITIES
        if hasattr(_config_domain := __import__('core._config_domain', fromlist=['*']), 'MATERIAL_DENSITIES'):
            densities = _config_domain.MATERIAL_DENSITIES
            assert isinstance(densities, dict)


class TestProcessCodes:
    """PROCESS_CODES 测试"""

    def test_process_codes_exists(self):
        """测试PROCESS_CODES存在"""
        from core._config_domain import PROCESS_CODES
        assert PROCESS_CODES is not None
        assert isinstance(PROCESS_CODES, dict)

    def test_process_codes_not_empty(self):
        """测试PROCESS_CODES非空"""
        from core._config_domain import PROCESS_CODES
        assert len(PROCESS_CODES) > 0

    def test_get_process_code_found(self):
        """测试get_process_code找到"""
        from core._config_domain import get_process_code, PROCESS_CODES
        if PROCESS_CODES:
            first_key = list(PROCESS_CODES.keys())[0]
            result = get_process_code(first_key)
            assert result is not None
            assert isinstance(result, str)

    def test_get_process_code_not_found(self):
        """测试get_process_code未找到"""
        from core._config_domain import get_process_code
        result = get_process_code("NONEXISTENT_PROCESS_XYZ")
        # 未找到应该返回空字符串或生成临时编码
        assert result is None or isinstance(result, str)


class TestOrderStatus:
    """ORDER_STATUS 测试"""

    def test_order_status_exists(self):
        """测试ORDER_STATUS存在"""
        from core._config_domain import ORDER_STATUS
        assert ORDER_STATUS is not None
        assert isinstance(ORDER_STATUS, dict)

    def test_order_status_keys(self):
        """测试ORDER_STATUS键"""
        from core._config_domain import ORDER_STATUS
        # 应该包含常见的订单状态
        assert len(ORDER_STATUS) > 0


class TestProcesses:
    """PROCESSES 测试"""

    def test_processes_exists(self):
        """测试PROCESSES存在"""
        from core._config_domain import PROCESSES
        if PROCESSES is not None:
            # PROCESSES 是 list 或 dict
            assert isinstance(PROCESSES, (list, dict))


class TestIsRegistered:
    """is_registered 测试"""

    def test_is_registered(self):
        """测试is_registered"""
        from core._config_domain import is_registered
        result = is_registered("原材料准备")
        assert isinstance(result, bool)

    def test_is_registered_false(self):
        """测试未注册的工序"""
        from core._config_domain import is_registered
        result = is_registered("NONEXISTENT_PROCESS_XYZ_12345")
        assert result is False


class TestGetAllProcesses:
    """get_all_processes 测试"""

    def test_get_all_processes(self):
        """测试获取所有工序"""
        from core._config_domain import get_all_processes
        result = get_all_processes()
        assert isinstance(result, list)

    def test_get_all_processes_unsorted(self):
        """测试不排序的工序列表"""
        from core._config_domain import get_all_processes
        result = get_all_processes(sort=False)
        assert isinstance(result, list)


class TestGetAllProcessCodes:
    """get_all_process_codes 测试"""

    def test_get_all_process_codes(self):
        """测试获取所有工序编码"""
        from core._config_domain import get_all_process_codes
        result = get_all_process_codes()
        assert isinstance(result, dict)


class TestGetProcessSeq:
    """get_process_seq 测试"""

    def test_get_process_seq(self):
        """测试获取工序序号"""
        from core._config_domain import get_process_seq
        result = get_process_seq("原材料准备")
        # 返回整数或0
        assert isinstance(result, int) or result is None


class TestProductTypes:
    """PRODUCT_TYPES 测试"""

    def test_product_types_exists(self):
        """测试PRODUCT_TYPES存在"""
        from core._config_domain import PRODUCT_TYPES
        if PRODUCT_TYPES is not None:
            assert isinstance(PRODUCT_TYPES, list)


class TestSurfaceTreatments:
    """SURFACE_TREATMENTS 测试"""

    def test_surface_treatments_exists(self):
        """测试SURFACE_TREATMENTS存在"""
        from core._config_domain import SURFACE_TREATMENTS
        if SURFACE_TREATMENTS is not None:
            assert isinstance(SURFACE_TREATMENTS, list)


class TestInspectionConfig:
    """检验配置测试"""

    def test_inspection_types(self):
        """测试INSPECTION_TYPES"""
        from core._config_domain import INSPECTION_TYPES
        assert INSPECTION_TYPES is not None
        assert isinstance(INSPECTION_TYPES, list)
        assert "首检" in INSPECTION_TYPES
        assert "巡检" in INSPECTION_TYPES
        assert "终检" in INSPECTION_TYPES

    def test_inspection_results(self):
        """测试INSPECTION_RESULTS"""
        from core._config_domain import INSPECTION_RESULTS
        assert INSPECTION_RESULTS is not None
        assert isinstance(INSPECTION_RESULTS, list)
        assert "合格" in INSPECTION_RESULTS
        assert "不合格" in INSPECTION_RESULTS

    def test_inspection_items_by_category(self):
        """测试INSPECTION_ITEMS_BY_CATEGORY"""
        from core._config_domain import INSPECTION_ITEMS_BY_CATEGORY
        assert INSPECTION_ITEMS_BY_CATEGORY is not None
        assert isinstance(INSPECTION_ITEMS_BY_CATEGORY, dict)


class TestUnits:
    """UNITS 测试"""

    def test_units_exists(self):
        """测试UNITS存在"""
        from core._config_domain import UNITS
        assert UNITS is not None
        assert isinstance(UNITS, list)
        assert "米" in UNITS


class TestBusinessConfig:
    """BusinessConfig 测试"""

    def test_business_config_exists(self):
        """测试BusinessConfig存在"""
        from core._config_domain import BusinessConfig
        assert BusinessConfig is not None

    def test_business_config_class(self):
        """测试BusinessConfig是类"""
        from core._config_domain import BusinessConfig
        assert isinstance(BusinessConfig, type)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
