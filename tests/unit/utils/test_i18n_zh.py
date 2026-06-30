# -*- coding: utf-8 -*-
"""
utils.i18n_zh 单测
"""
import pytest
from utils.i18n_zh import (
    STATUS_ZH, DATA_TYPE_ZH, PRIORITY_ZH, STEP_STATUS_ZH, ORDER_STATUS_ZH,
    translate, translate_payload,
)


# ── 1. 字典完整性 ──
class TestDicts:
    def test_status_zh_required_keys(self):
        for k in ("pending", "in_progress", "completed", "distributed",
                  "paused", "cancelled", "in_production", "overdue"):
            assert k in STATUS_ZH, f"STATUS_ZH 缺键 {k}"

    def test_datatype_zh_required_keys(self):
        for k in ("process_report", "flow_step", "flow_production",
                  "material_request", "material_pickup", "material_buy",
                  "quality_task", "equipment_repair", "outsource_task",
                  "approval", "config"):
            assert k in DATA_TYPE_ZH, f"DATA_TYPE_ZH 缺键 {k}"

    def test_priority_zh_required_keys(self):
        for k in ("urgent", "high", "normal", "low", "rush"):
            assert k in PRIORITY_ZH, f"PRIORITY_ZH 缺键 {k}"

    def test_values_are_zh(self):
        """翻译值必须非空且不是英文 status 关键字"""
        for k, v in STATUS_ZH.items():
            assert isinstance(v, str) and v, f"STATUS_ZH[{k}]={v} 不是非空字符串"


# ── 2. translate 单值 ──
class TestTranslate:
    def test_status_basic(self):
        assert translate("pending", "status") == "待开始"
        assert translate("in_progress", "status") == "进行中"
        assert translate("completed", "status") == "已完成"
        assert translate("distributed", "status") == "已派单"

    def test_data_type_basic(self):
        assert translate("process_report", "data_type") == "工序报工"
        assert translate("flow_step", "data_type") == "流程步骤"
        assert translate("quality_task", "data_type") == "质检任务"

    def test_priority_basic(self):
        assert translate("urgent", "priority") == "紧急"
        assert translate("normal", "priority") == "普通"

    def test_legacy_alias(self):
        """旧枚举应被映射到新中文"""
        assert translate("process_task", "data_type") == "工序报工"
        assert translate("report", "data_type") == "工序报工"
        assert translate("material", "data_type") == "物料领取"
        assert translate("purchase", "data_type") == "物料采购"

    def test_idempotent_for_zh(self):
        """已经是中文时,翻译应原样返回(防双重翻译)"""
        assert translate("待开始", "status") == "待开始"
        assert translate("已完成", "status") == "已完成"

    def test_unknown_returns_original(self):
        """未识别的值原样返回"""
        assert translate("xyz_xxx", "status") == "xyz_xxx"
        assert translate("FooBar", "status") == "FooBar"

    def test_empty_returns_original(self):
        assert translate("", "status") == ""
        assert translate(None, "status") is None


# ── 3. translate_payload 递归 ──
class TestTranslatePayload:
    def test_flat(self):
        p = {"status": "in_progress", "data_type": "process_report", "priority": "high"}
        translate_payload(p)
        assert p["status"] == "进行中"
        assert p["data_type"] == "工序报工"
        assert p["priority"] == "高"
        # 保留 *_code
        assert p["status_code"] == "in_progress"
        assert p["data_type_code"] == "process_report"
        assert p["priority_code"] == "high"

    def test_nested_list(self):
        p = {
            "order_no": "ORD-1",
            "tasks": [
                {"id": "1", "status": "completed"},
                {"id": "2", "status": "pending"},
                {"id": "3", "status": "in_progress"},
            ],
        }
        translate_payload(p)
        assert p["tasks"][0]["status"] == "已完成"
        assert p["tasks"][1]["status"] == "待开始"
        assert p["tasks"][2]["status"] == "进行中"

    def test_nested_dict(self):
        p = {"step": {"status_key": "tmpl_publish", "name": "工单发布"}}
        translate_payload(p)
        assert p["step"]["status_key"] == "工单发布"
        assert p["step"]["status_key_code"] == "tmpl_publish"

    def test_preserve_non_enum_fields(self):
        p = {"order_no": "ORD-1", "quantity": 100, "operator": "张三"}
        translate_payload(p)
        assert p["order_no"] == "ORD-1"
        assert p["quantity"] == 100
        assert p["operator"] == "张三"

    def test_no_code_when_already_zh(self):
        """已是中文时不写入 *_code"""
        p = {"status": "已完成"}
        translate_payload(p)
        assert p["status"] == "已完成"
        assert "status_code" not in p

    def test_save_code_false(self):
        p = {"status": "completed"}
        translate_payload(p, save_code=False)
        assert p["status"] == "已完成"
        assert "status_code" not in p

    def test_priority_field_aliases(self):
        """level / urgency 也走 priority 翻译"""
        p = {"level": "urgent", "urgency": "low"}
        translate_payload(p)
        assert p["level"] == "紧急"
        assert p["urgency"] == "低"
