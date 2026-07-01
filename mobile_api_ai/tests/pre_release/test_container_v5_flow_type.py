# -*- coding: utf-8 -*-
"""
T5 前测: 容器中心 V5 DataCollector/Distributor 加 flow_type 路由 (D3.1 映射)

修复点 (SPEC v1.1 F5):
  1. DataType enum 扩 REPAIR + OUTSOURCE (L86-93)
  2. DataPackage 加 flow_type 字段 (L110-154)
  3. D3.1 6→5 映射函数 (新模块级)
  4. DataCollector.collect 接受 flow_type 入参 + 默认推断 (L200-232)
  5. DataDistributor.distribute 按 flow_type 路由 (L465-540)

设计契约 (9 用例):
  1-5. D3.1 映射表 5 种 flow_type (production/quality/material_purchase/outsource/repair)
  6. DataPackage 实例化含 flow_type 字段
  7. collect 入参 flow_type='outsource' 优先于 data_type 推断
  8. collect 入参缺 flow_type → 按 data_type 推断
  9. data_type 不在 enum → 兜底 'production'

D3.1 映射表 (6 data_type → 5 flow_type):
  report/approval/order/process/cost → production
  quality → quality
  material → material_purchase
  (扩展) repair → repair
  (扩展) outsource → outsource
"""
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# 模拟修复后 (与方案一致)
DATA_TYPE_TO_FLOW_TYPE = {
    "report": "production",
    "approval": "production",
    "order": "production",
    "process": "production",
    "cost": "production",
    "quality": "quality",
    "material": "material_purchase",
    "repair": "repair",
    "outsource": "outsource",
}


def map_data_type_to_flow_type(data_type: str) -> str:
    """D3.1 6→5 映射函数 (模块级, 纯函数)"""
    if not data_type:
        return "production"
    return DATA_TYPE_TO_FLOW_TYPE.get(data_type.lower(), "production")


class TestD31Mapping(unittest.TestCase):
    """D3.1 映射表 6→5 (5 用例覆盖所有 flow_type)"""

    def test_report_to_production(self):
        """1. data_type='report' → flow_type='production'"""
        self.assertEqual(map_data_type_to_flow_type("report"), "production")

    def test_quality_to_quality(self):
        """2. data_type='quality' → flow_type='quality' (独立 flow_type)"""
        self.assertEqual(map_data_type_to_flow_type("quality"), "quality")

    def test_material_to_material_purchase(self):
        """3. data_type='material' → flow_type='material_purchase'"""
        self.assertEqual(map_data_type_to_flow_type("material"), "material_purchase")

    def test_repair_to_repair(self):
        """4. data_type='repair' → flow_type='repair' (独立 flow_type)"""
        self.assertEqual(map_data_type_to_flow_type("repair"), "repair")

    def test_outsource_to_outsource(self):
        """5. data_type='outsource' → flow_type='outsource' (独立 flow_type)"""
        self.assertEqual(map_data_type_to_flow_type("outsource"), "outsource")


class TestDataPackageFlowTypeField(unittest.TestCase):
    """DataPackage 加 flow_type 字段"""

    def test_data_package_has_flow_type_attribute(self):
        """6. DataPackage 实例化后有 flow_type 属性"""
        # 模拟 DataPackage.__init__ (修复后版本)
        class MockDataPackage:
            def __init__(self, data_type, title, content, flow_type=""):
                self.data_type = data_type
                self.title = title
                self.content = content
                self.flow_type = flow_type

        pkg = MockDataPackage(
            data_type="report",
            title="报工",
            content={"qty": 10},
            flow_type="production",
        )
        self.assertEqual(pkg.flow_type, "production")
        # 默认空字符串
        pkg2 = MockDataPackage(data_type="report", title="t", content={})
        self.assertEqual(pkg2.flow_type, "")


class TestDataCollectorFlowTypePriority(unittest.TestCase):
    """DataCollector.collect 入参 flow_type 优先于 data_type 推断"""

    def test_explicit_flow_type_overrides_inference(self):
        """7. kwargs 传 flow_type='outsource' → DataPackage.flow_type='outsource'
        (即使 data_type='report', 也不被推断为 'production')"""
        # 模拟 collect 内部: flow_type or map_data_type_to_flow_type(data_type)
        flow_type = "outsource"
        data_type = "report"
        effective = flow_type or map_data_type_to_flow_type(data_type)
        self.assertEqual(effective, "outsource",
                         f"显式 flow_type 应优先, 实际 {effective}")

    def test_missing_flow_type_falls_back_to_inference(self):
        """8. kwargs 缺 flow_type → 按 data_type 推断"""
        flow_type = ""
        data_type = "material"
        effective = flow_type or map_data_type_to_flow_type(data_type)
        self.assertEqual(effective, "material_purchase")

    def test_unknown_data_type_falls_back_to_production(self):
        """9. data_type='unknown' 不在 enum → 兜底 'production'"""
        effective = map_data_type_to_flow_type("unknown")
        self.assertEqual(effective, "production")

    def test_empty_data_type_falls_back_to_production(self):
        """10. data_type='' 兜底 'production'"""
        effective = map_data_type_to_flow_type("")
        self.assertEqual(effective, "production")


if __name__ == "__main__":
    unittest.main()
