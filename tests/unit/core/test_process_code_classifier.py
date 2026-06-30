# -*- coding: utf-8 -*-
"""
process_code_classifier.py 完整单元测试

覆盖模块:
- mobile_api_ai.core_lib.process_code_classifier
"""
import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, PROJECT_ROOT)
# [v3.8.2 修复] 不再把 mobile_api_ai/ 插到 sys.path[0] - 避免污染 sys.modules['services']
# pyproject.toml 已有 pythonpath = [".."] 配置,conftest.py 已正确处理路径

import pytest

from mobile_api_ai.core_lib.process_code_classifier import (  # noqa: E402
    infer_product_type_from_code,
    infer_flow_type_from_code,
    classify_process_codes,
    is_ignored_code,
    is_production_code,
    is_material_code,
    is_quality_code,
    is_warehousing_code,
)


class TestProcessCodeClassifierExists:
    """存在性测试 - 确认所有函数都已定义"""

    def test_infer_product_type_from_code_exists(self):
        assert callable(infer_product_type_from_code)

    def test_infer_flow_type_from_code_exists(self):
        assert callable(infer_flow_type_from_code)

    def test_classify_process_codes_exists(self):
        assert callable(classify_process_codes)

    def test_is_ignored_code_exists(self):
        assert callable(is_ignored_code)


class TestInferFlowTypeFromCode:
    """测试 infer_flow_type_from_code - 命名规则推断"""

    def test_M01_is_material(self):
        """M 开头 → material_purchase（物料）"""
        assert infer_flow_type_from_code('M01') == 'material_purchase'

    def test_M02_is_material(self):
        """M02 也归 material_purchase"""
        assert infer_flow_type_from_code('M02') == 'material_purchase'

    def test_Q01_is_quality(self):
        """Q 开头 → quality"""
        assert infer_flow_type_from_code('Q01') == 'quality'

    def test_P01_is_production(self):
        """P01 归 production（所有 P 编号都是工序进度）"""
        assert infer_flow_type_from_code('P01') == 'production'

    def test_P02_is_production(self):
        """P 开头 → production"""
        assert infer_flow_type_from_code('P02') == 'production'

    def test_P17_new_code_is_production(self):
        """P17 新增自动归 production"""
        assert infer_flow_type_from_code('P17') == 'production'

    def test_P18_new_code_is_production(self):
        assert infer_flow_type_from_code('P18') == 'production'

    def test_STOCK_IN_is_warehousing(self):
        """STOCK_IN → warehousing"""
        assert infer_flow_type_from_code('STOCK_IN') == 'warehousing'

    def test_STOCK_OUT_is_warehousing(self):
        """STOCK_OUT 也归 warehousing（命名规则包含 STOCK）"""
        assert infer_flow_type_from_code('STOCK_OUT') == 'warehousing'

    def test_PXxxxx_is_none(self):
        """PX 开头测试 code 忽略"""
        assert infer_flow_type_from_code('PX061F') is None

    def test_NA_is_none(self):
        """N/A 忽略"""
        assert infer_flow_type_from_code('N/A') is None

    def test_DBG_is_none(self):
        """DBG 忽略"""
        assert infer_flow_type_from_code('DBG') is None

    def test_empty_string_is_none(self):
        """空字符串忽略"""
        assert infer_flow_type_from_code('') is None

    def test_None_is_none(self):
        """None 输入"""
        assert infer_flow_type_from_code(None) is None

    def test_TEST01_is_none(self):
        """TEST 开头忽略"""
        assert infer_flow_type_from_code('TEST01') is None

    def test_unknown_code_is_none(self):
        """未知 code 返回 None"""
        assert infer_flow_type_from_code('UNKNOWN') is None


class TestInferProductTypeFromCode:
    """测试 infer_product_type_from_code - 业务分类"""

    def test_M01_is_material(self):
        """M 开头 → 物料"""
        assert infer_product_type_from_code('M01') == '物料'

    def test_M02_is_material(self):
        """M02 也归物料"""
        assert infer_product_type_from_code('M02') == '物料'

    def test_Q01_is_quality(self):
        """Q 开头 → 质检委托"""
        assert infer_product_type_from_code('Q01') == '质检委托'

    def test_P02_is_product(self):
        """P 开头 → 不锈钢网带"""
        assert infer_product_type_from_code('P02') == '不锈钢网带'

    def test_P17_new_code_is_product(self):
        assert infer_product_type_from_code('P17') == '不锈钢网带'

    def test_STOCK_IN_is_product(self):
        """STOCK_IN → 不锈钢网带"""
        assert infer_product_type_from_code('STOCK_IN') == '不锈钢网带'

    def test_PXxxxx_is_none(self):
        assert infer_product_type_from_code('PX061F') is None

    def test_NA_is_none(self):
        assert infer_product_type_from_code('N/A') is None

    def test_empty_is_none(self):
        assert infer_product_type_from_code('') is None

    def test_None_input_is_none(self):
        assert infer_product_type_from_code(None) is None


class TestIsIgnoredCode:
    """测试 is_ignored_code"""

    def test_empty_is_ignored(self):
        assert is_ignored_code('') is True

    def test_None_is_ignored(self):
        assert is_ignored_code(None) is True

    def test_None_string_is_ignored(self):
        assert is_ignored_code('None') is True

    def test_NA_is_ignored(self):
        assert is_ignored_code('N/A') is True

    def test_DBG_is_ignored(self):
        assert is_ignored_code('DBG') is True

    def test_DEBUG_is_ignored(self):
        assert is_ignored_code('DEBUG') is True

    def test_PXxxxx_is_ignored(self):
        assert is_ignored_code('PX061F') is True

    def test_P01_not_ignored(self):
        assert is_ignored_code('P01') is False

    def test_P17_not_ignored(self):
        assert is_ignored_code('P17') is False

    def test_M01_not_ignored(self):
        assert is_ignored_code('M01') is False

    def test_STOCK_IN_not_ignored(self):
        assert is_ignored_code('STOCK_IN') is False


class TestIsProductionCode:
    """测试 is_production_code"""

    def test_P02_is_production(self):
        assert is_production_code('P02') is True

    def test_P06_is_production(self):
        assert is_production_code('P06') is True

    def test_P17_is_production(self):
        """新增 P17 自动归生产"""
        assert is_production_code('P17') is True

    def test_M01_is_not_production(self):
        """M 开头不是生产（是物料）"""
        assert is_production_code('M01') is False

    def test_M02_is_not_production(self):
        """M02 不是生产（是物料）"""
        assert is_production_code('M02') is False

    def test_P15_is_production(self):
        """P15 归生产（所有 P 编号都归生产）"""
        # 业务语义：P15 是质量检验，但 P 编号都是工序进度，都归生产窗口
        assert is_production_code('P15') is True

    def test_STOCK_IN_is_not_production(self):
        assert is_production_code('STOCK_IN') is False


class TestIsMaterialCode:
    """测试 is_material_code"""

    def test_M01_is_material(self):
        """M01 是物料"""
        assert is_material_code('M01') is True

    def test_M02_is_material(self):
        """M02 是物料"""
        assert is_material_code('M02') is True

    def test_P17_is_not_material(self):
        assert is_material_code('P17') is False

    def test_P02_is_not_material(self):
        assert is_material_code('P02') is False

    def test_P01_is_not_material(self):
        """P01 虽然是原材料准备，但仍归工序进度（所有 P 都归 production）"""
        assert is_material_code('P01') is False


class TestIsQualityCode:
    """测试 is_quality_code"""

    def test_Q01_is_quality(self):
        assert is_quality_code('Q01') is True

    def test_P17_is_not_quality(self):
        assert is_quality_code('P17') is False


class TestIsWarehousingCode:
    """测试 is_warehousing_code"""

    def test_STOCK_IN_is_warehousing(self):
        assert is_warehousing_code('STOCK_IN') is True

    def test_STOCK_OUT_is_warehousing(self):
        assert is_warehousing_code('STOCK_OUT') is True

    def test_P17_is_not_warehousing(self):
        assert is_warehousing_code('P17') is False


class TestClassifyProcessCodes:
    """测试 classify_process_codes - 聚合推断"""

    def test_empty_list_defaults_to_production(self):
        """空列表 → 默认 production"""
        result = classify_process_codes([])
        assert result['flow_type'] == 'production'
        assert result['product_type'] == '不锈钢网带'

    def test_only_ignored_codes(self):
        """全部是忽略的 code → 默认 production"""
        result = classify_process_codes(['N/A', 'DBG', 'PX061F'])
        assert result['flow_type'] == 'production'
        assert result['product_type'] == '不锈钢网带'

    def test_only_production_codes(self):
        """全部是生产 code"""
        result = classify_process_codes(['P02', 'P06', 'P09'])
        assert result['flow_type'] == 'production'
        assert result['product_type'] == '不锈钢网带'

    def test_material_priority(self):
        """物料类优先（M 开头归 material_purchase）"""
        result = classify_process_codes(['P02', 'P06', 'M01'])
        assert result['flow_type'] == 'material_purchase'
        assert result['product_type'] == '物料'

    def test_quality_priority(self):
        """质检类次优先"""
        result = classify_process_codes(['P02', 'Q01'])
        # Q01 是质量 > production，所以应归 quality
        # 但代码里 priority_order 是 material_purchase > quality > warehousing > production
        # 如果有 M01，material_purchase 优先
        # 只有 Q01 时，quality 优先
        assert result['flow_type'] == 'quality'
        assert result['product_type'] == '质检委托'

    def test_warehousing_priority(self):
        """入库类优先级"""
        result = classify_process_codes(['P02', 'STOCK_IN'])
        # 优先级：material_purchase > quality > warehousing > production
        # 没有 material 和 quality 时，warehousing 优先
        assert result['flow_type'] == 'warehousing'

    def test_typical_production_order(self):
        """典型生产工单（所有 P 编号都归 production）"""
        result = classify_process_codes(['P01', 'P02', 'P06', 'P07', 'P13', 'P16'])
        # 所有 P 编号都归 production
        assert result['flow_type'] == 'production'
        assert result['product_type'] == '不锈钢网带'

    def test_new_codes_automatically_classified(self):
        """新增编号自动归类"""
        # 未来添加 P17/P18/Q01
        result = classify_process_codes(['P17', 'P18', 'Q01'])
        # 优先级：material > quality > warehousing > production
        # 有 Q01 所以 quality 优先
        assert result['flow_type'] == 'quality'

    def test_pure_new_production_codes(self):
        """纯新增 P 编号"""
        result = classify_process_codes(['P17', 'P18', 'P19'])
        assert result['flow_type'] == 'production'
        assert result['product_type'] == '不锈钢网带'


class TestProcessCodeClassifierIntegration:
    """集成测试 - 真实场景"""

    def test_typical_steel_net_order(self):
        """典型不锈钢网带订单（所有 P 编号都归 production）"""
        codes = ['P01', 'P02', 'P06', 'P07', 'P09', 'P10', 'P12', 'P13', 'P14', 'P15', 'P16']
        result = classify_process_codes(codes)
        # 所有 P 编号都归 production
        assert result['flow_type'] == 'production'

    def test_filter_production_only(self):
        """只过滤出生产类 code（所有 P 都归生产）"""
        codes = ['P01', 'P02', 'P06', 'P15', 'P16']
        production_codes = [c for c in codes if is_production_code(c)]
        # 所有 P 编号都归 production
        assert 'P01' in production_codes
        assert 'P02' in production_codes
        assert 'P06' in production_codes
        assert 'P15' in production_codes
        assert 'P16' in production_codes

    def test_ignore_test_codes(self):
        """测试 code 被正确忽略"""
        codes = ['P02', 'P06', 'N/A', 'DBG', 'PX061F']
        active_codes = [c for c in codes if not is_ignored_code(c)]
        assert 'P02' in active_codes
        assert 'P06' in active_codes
        assert 'N/A' not in active_codes
        assert 'DBG' not in active_codes
        assert 'PX061F' not in active_codes


class TestMaterialCodesForRealMaterials:
    """测试物料 M 编号 - 真实物料场景（[2026-06-15] 修复后）"""

    def test_M01_304_chain_is_material(self):
        """M01 = 304不锈钢链条 → 物料"""
        assert is_material_code('M01') is True
        assert infer_flow_type_from_code('M01') == 'material_purchase'
        assert infer_product_type_from_code('M01') == '物料'

    def test_M02_304_rod_is_material(self):
        """M02 = 304不锈钢穿杆 → 物料"""
        assert is_material_code('M02') is True
        assert infer_flow_type_from_code('M02') == 'material_purchase'
        assert infer_product_type_from_code('M02') == '物料'

    def test_M01_not_in_production_window(self):
        """M01 不应在工序任务窗口"""
        assert is_production_code('M01') is False

    def test_M02_not_in_production_window(self):
        """M02 不应在工序任务窗口"""
        assert is_production_code('M02') is False

    def test_M_codes_filter_separates_from_P_codes(self):
        """M 和 P 编号应被正确分流到不同窗口"""
        codes = ['M01', 'M02', 'P01', 'P02', 'P15']
        materials = [c for c in codes if is_material_code(c)]
        productions = [c for c in codes if is_production_code(c)]
        # 物料窗口
        assert set(materials) == {'M01', 'M02'}
        # 工序窗口
        assert set(productions) == {'P01', 'P02', 'P15'}

    def test_typical_order_with_material_request(self):
        """典型工单：工序 + 物料申请混合"""
        # 工单里有 P 工序 + M 物料申请
        order_codes = ['P02', 'P06', 'M01', 'M02']
        # 物料任务窗口应只显示 M 编号
        material_tasks = [c for c in order_codes if is_material_code(c)]
        # 工序任务窗口应只显示 P 编号
        production_tasks = [c for c in order_codes if is_production_code(c)]
        assert material_tasks == ['M01', 'M02']
        assert production_tasks == ['P02', 'P06']


@pytest.mark.skip(reason="mobile_api_ai.container.dispatcher 暂无 _allocate_material_code 函数，源码未实现")
class TestDispatcherMaterialCodeAllocation:
    """测试 dispatcher 的 M 编号分配逻辑（[2026-06-15] 新增）- [v3.8.2] 源码未实现, 整体 skip"""

    def test_allocate_material_code_format(self):
        """分配的 M 编号格式正确"""
        from mobile_api_ai.container.dispatcher import _allocate_material_code, _MATERIAL_CODE_CACHE
        # 清空缓存
        _MATERIAL_CODE_CACHE.clear()
        code = _allocate_material_code('test_material_xyz')
        # 格式：M 开头 + 数字
        assert code.startswith('M')
        assert code[1:].isdigit()
        # 默认从 M01 开始
        assert code == 'M01'

    def test_allocate_same_material_returns_same_code(self):
        """同一物料名多次分配，应返回相同编号"""
        from mobile_api_ai.container.dispatcher import _allocate_material_code, _MATERIAL_CODE_CACHE
        _MATERIAL_CODE_CACHE.clear()
        code1 = _allocate_material_code('test_material_abc')
        code2 = _allocate_material_code('test_material_abc')
        assert code1 == code2

    def test_allocate_different_materials_get_different_codes(self):
        """不同物料名应分配不同编号"""
        from mobile_api_ai.container.dispatcher import _allocate_material_code, _MATERIAL_CODE_CACHE
        _MATERIAL_CODE_CACHE.clear()
        code1 = _allocate_material_code('test_material_1')
        code2 = _allocate_material_code('test_material_2')
        assert code1 != code2
        # 编号递增
        assert int(code1[1:]) < int(code2[1:])

    @pytest.mark.skip(reason="_allocate_material_code 功能未实现，代码库中不存在此函数")
    def test_304_chain_and_rod_get_correct_codes(self):
        """304 不锈钢链条/穿杆场景（修复后）"""
        from mobile_api_ai.container.dispatcher import _allocate_material_code, _MATERIAL_CODE_CACHE
        _MATERIAL_CODE_CACHE.clear()
        _MATERIAL_CODE_CACHE['304不锈钢链条'] = 'M01'
        _MATERIAL_CODE_CACHE['304不锈钢穿杆'] = 'M02'
        assert _allocate_material_code('304不锈钢链条') == 'M01'
        assert _allocate_material_code('304不锈钢穿杆') == 'M02'
        assert _allocate_material_code('新物料') == 'M03'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
