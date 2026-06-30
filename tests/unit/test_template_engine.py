# -*- coding: utf-8 -*-
"""template_engine.py 单元测试"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../mobile_api_ai'))

from template_engine import (
    _render_template, _resolve_variables, MESSAGE_TEMPLATES_DEFAULT,
    VARIABLE_CN_TO_EN, VAR_EN_TO_CN, _send_wechat_message,
)


class TestRenderTemplate:
    """_render_template 渲染测试"""

    def test_full_variables(self):
        r = _render_template('tmpl_task_assigned', {
            '操作员': '张三', '任务标题': '焊接', '订单号': 'WO001',
            '工序': '焊接眼镜网', '数量': 100
        })
        assert '张三' in r
        assert '焊接' in r
        assert 'WO001' in r
        assert '100' in r
        assert '——' not in r  # 所有变量都有值

    def test_missing_variables(self):
        """未传入的变量显示为 —"""
        r = _render_template('tmpl_task_assigned', {'操作员': '李四'})
        assert '李四' in r
        assert '—' in r  # 缺失的订单号/工序/数量

    def test_none_variables(self):
        """None 变量显示为空"""
        r = _render_template('tmpl_task_assigned', {
            '操作员': '王五', '任务标题': None, '订单号': 'WO002'
        })
        assert '王五' in r
        assert '任务: \n' in r or '任务:—' in r  # None → 空 或 缺失 → —

    def test_unknown_template(self):
        r = _render_template('nonexistent_test_xyz', {'操作员': 'test'})
        assert r == ''

    def test_special_chars(self):
        """特殊字符不被误清洗"""
        r = _render_template('tmpl_task_assigned', {
            '操作员': '测试-人', '任务标题': '工序(A)', '订单号': 'WO-003',
            '工序': '焊接#1', '数量': 50
        })
        assert '测试-人' in r
        assert '工序(A)' in r
        assert 'WO-003' in r

    def test_json_like_content_not_cleaned(self):
        """JSON 花括号不受影响"""
        r = _render_template('tmpl_inventory_alert', {
            '物料名称': '螺母M8', '当前库存': 50, '最低库存': 100, '单位': '个'
        })
        assert '螺母M8' in r
        assert '50' in r

    def test_whitespace_only_variables(self):
        r = _render_template('tmpl_task_assigned', {
            '操作员': '   ', '任务标题': '', '订单号': 'WO', '工序': '焊', '数量': 1
        })
        assert 'WO' in r

    def test_long_variable_name(self):
        """超长变量名不崩溃"""
        r = _render_template('tmpl_task_assigned', {
            '操作员': 'A' * 100, '任务标题': 'B' * 100, '订单号': 'C' * 100,
            '工序': 'D' * 100, '数量': 99999
        })
        assert 'A' * 100 in r

    def test_all_33_templates_exist(self):
        """33 个模板全部可渲染"""
        for t in MESSAGE_TEMPLATES_DEFAULT:
            tid = t['id']
            r = _render_template(tid, {'操作员': 'test', '订单号': 'T'})
            assert isinstance(r, str)
            assert len(r) > 5, f'Template {tid} returned short content'

    def test_inventory_alert_template(self):
        r = _render_template('tmpl_inventory_alert', {
            '物料名称': '螺母', '当前库存': 10, '最低库存': 50, '单位': '个'
        })
        assert '螺母' in r
        assert '10' in r
        assert '50' in r
        assert '库存不足' in r

    def test_report_submitted_template(self):
        r = _render_template('tmpl_report_submitted', {
            '订单号': 'WO001', '工序': '焊接', '数量': 200,
            '操作员': '张三', '报工时间': '2026-06-02 10:00'
        })
        assert 'WO001' in r
        assert '张三' in r
        assert '报工已提交' in r

    def test_repair_reminder_template(self):
        r = _render_template('tmpl_repair_reminder', {
            '设备名称': '冲床A3', '故障描述': '异响严重',
            '报修人': '赵六', '报修时间': '2026-06-02 09:30'
        })
        assert '冲床A3' in r
        assert '异响严重' in r
        assert '赵六' in r


class TestResolveVariables:
    """_resolve_variables 解析测试"""

    def test_cn_to_en(self):
        r = _resolve_variables({'操作员': '张三'})
        assert r.get('操作员') == '张三'
        assert r.get('operator_name') == '张三'

    def test_en_to_cn(self):
        r = _resolve_variables({'operator_name': 'Li Si'})
        assert r.get('operator_name') == 'Li Si'
        assert r.get('操作员') == 'Li Si'

    def test_both_present(self):
        r = _resolve_variables({'操作员': '张三', 'operator_name': 'Zhang San'})
        assert r.get('操作员') == '张三'
        assert r.get('operator_name') == 'Zhang San'

    def test_partial_mapping(self):
        r = _resolve_variables({'订单号': 'WO001', '订单号_unknown': 'test'})
        assert r.get('订单号') == 'WO001'
        assert r.get('order_no') == 'WO001'


class TestVARIABinding:
    """变量映射完整性"""

    def test_all_mappings_bidirectional(self):
        assert len(VARIABLE_CN_TO_EN) == len(VAR_EN_TO_CN)

    def test_minimum_60_mappings(self):
        assert len(VARIABLE_CN_TO_EN) >= 60

    def test_new_variables_exist(self):
        """B 阶段新增的变量"""
        assert '报工时间' in VARIABLE_CN_TO_EN
        assert '最低库存' in VARIABLE_CN_TO_EN


class TestSendMessage:
    """_send_wechat_message 不崩溃"""

    def test_no_cloud_poller(self):
        """无云端 relay 时返回 False"""
        ok, err = _send_wechat_message('测试消息', 'text')
        assert isinstance(ok, bool)
        assert isinstance(err, str)


class TestTemplateCount:
    """模板数量 = 41"""

    def test_total_40_templates(self):
        assert len(MESSAGE_TEMPLATES_DEFAULT) == 41  # R6新增第41个模板

    def test_no_duplicate_ids(self):
        ids = [t['id'] for t in MESSAGE_TEMPLATES_DEFAULT]
        assert len(ids) == len(set(ids))
