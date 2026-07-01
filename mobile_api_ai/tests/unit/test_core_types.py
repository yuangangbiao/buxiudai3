# -*- coding: utf-8 -*-
"""dispatch_center/_core_types.py 单元测试"""
import pytest


class TestStatusKeyMapping:
    def test_status_keys_present(self):
        from dispatch_center._core_types import STATUS_KEY_TO_MYSQL
        assert 'published' in STATUS_KEY_TO_MYSQL
        assert 'completed' in STATUS_KEY_TO_MYSQL
        assert STATUS_KEY_TO_MYSQL['published'] == '已发布'

    def test_all_statuses_have_mapping(self):
        from dispatch_center._core_types import STATUS_KEY_TO_MYSQL
        required = ['published', 'scheduled', 'confirmed', 'in_production',
                     'reported', 'qc_passed', 'completed']
        for key in required:
            assert key in STATUS_KEY_TO_MYSQL


class TestDispatchRules:
    def test_rules_structure(self):
        from dispatch_center._core_types import DISPATCH_RULES_DEFAULT
        assert 'auto_dispatch_timeout' in DISPATCH_RULES_DEFAULT
        assert DISPATCH_RULES_DEFAULT['auto_dispatch_timeout']['type'] == 'number'
        assert DISPATCH_RULES_DEFAULT['enable_auto_dispatch']['type'] == 'boolean'

    def test_rule_values_sane(self):
        from dispatch_center._core_types import DISPATCH_RULES_DEFAULT
        timeout = DISPATCH_RULES_DEFAULT['auto_dispatch_timeout']['value']
        assert 1 <= timeout <= 120


class TestFlowTemplates:
    def test_production_template(self):
        from dispatch_center._core_types import PROCESS_FLOW_TEMPLATES
        prod = PROCESS_FLOW_TEMPLATES['production']
        assert prod['name'] == '生产流程'
        assert len(prod['steps']) == 7
        assert prod['steps'][0]['name'] == '工单发布'

    def test_material_template(self):
        from dispatch_center._core_types import PROCESS_FLOW_TEMPLATES
        mat = PROCESS_FLOW_TEMPLATES['material_purchase']
        assert mat['name'] == '物料流程'
        assert len(mat['steps']) == 6

    def test_quality_template(self):
        from dispatch_center._core_types import PROCESS_FLOW_TEMPLATES
        qc = PROCESS_FLOW_TEMPLATES['quality']
        assert qc['name'] == '质检流程'

    def test_repair_template(self):
        from dispatch_center._core_types import PROCESS_FLOW_TEMPLATES
        rep = PROCESS_FLOW_TEMPLATES['repair']
        assert rep['name'] == '维修流程'

    def test_outsource_template(self):
        from dispatch_center._core_types import PROCESS_FLOW_TEMPLATES
        out = PROCESS_FLOW_TEMPLATES['outsource']
        assert out['name'] == '外协流程'


class TestConfirmation:
    def test_confirmation_steps(self):
        from dispatch_center._core_types import CONFIRMATION_REQUIRED_STEPS
        assert 'scheduled' in CONFIRMATION_REQUIRED_STEPS
        assert 'completed' in CONFIRMATION_REQUIRED_STEPS

    def test_confirmation_keywords(self):
        from dispatch_center._core_types import CONFIRMATION_REPLY_KEYWORDS
        assert '确认' in CONFIRMATION_REPLY_KEYWORDS
        assert 'ok' in CONFIRMATION_REPLY_KEYWORDS


class TestProductNames:
    def test_product_types(self):
        from dispatch_center._core_types import PRODUCT_TYPE_NAMES
        assert PRODUCT_TYPE_NAMES[11] == '人字形网带'
        assert 23 in PRODUCT_TYPE_NAMES
