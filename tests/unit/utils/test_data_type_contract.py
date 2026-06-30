# -*- coding: utf-8 -*-
"""
data_type 严格分类契约 v1.0 单测
=================================

覆盖:
- 10 个新枚举值
- 6 张卡片分组
- 旧 → 新值映射
- classify_pkg 各类判定(含 content 字段兜底)
- classify_payloads 批量归类
- group_by_card 6 张卡片分组
- 流程模板常量

运行:
    python -m pytest tests/unit/utils/test_data_type_contract.py -v
"""
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from utils.data_type_contract import (
    NEW_DATA_TYPES,
    CARD_GROUPS,
    LEGACY_TO_NEW,
    PROCESS_FLOW_TEMPLATES,
    classify_pkg,
    classify_payloads,
    group_by_card,
    get_flow_step_names_set,
)


# ────────────────────────────────────────────────────────────
# 固定装置:白名单数据
# ────────────────────────────────────────────────────────────
PROCESS_NAMES_SET = {
    "备料/领料", "原材料准备", "焊接眼镜网", "激光切板",
    "链板冲压孔", "链板冲压成型", "编制左旋", "编制右旋",
    "穿曲轴", "输送带组装穿杆", "安装链条", "安装裙边",
    "整形校直", "焊接输送带", "表面处理", "质量检验", "包装入库",
    "工序测试",
}
FLOW_STEP_NAMES_SET = get_flow_step_names_set()


def _make_pkg(data_type, related_process, content=None, **extra):
    """构造测试用 pkg 字典"""
    p = {"data_type": data_type, "related_process": related_process}
    if content is not None:
        p["content"] = content
    p.update(extra)
    return p


# ────────────────────────────────────────────────────────────
# 1. 契约常量完整性
# ────────────────────────────────────────────────────────────
class TestContractConstants(unittest.TestCase):
    def test_new_data_types_has_11(self):
        """RE-006 新增 approval 后,共 11 个枚举值"""
        self.assertEqual(len(NEW_DATA_TYPES), 11)

    def test_new_data_types_required(self):
        for dt in (
            "process_report", "flow_step", "flow_production",
            "material_request", "material_pickup", "material_buy",
            "quality_task", "equipment_repair", "outsource_task",
            "approval", "config",
        ):
            self.assertIn(dt, NEW_DATA_TYPES, f"缺少新 data_type: {dt}")

    def test_card_groups_has_6_cards(self):
        self.assertEqual(len(CARD_GROUPS), 6)
        for card in (
            "process_tasks", "flow_steps", "material_tasks",
            "quality_tasks", "repair_tasks", "outsource_tasks",
        ):
            self.assertIn(card, CARD_GROUPS, f"缺少卡片: {card}")

    def test_card_groups_disjoint(self):
        """每种 data_type 只能属于一张卡片(严格不混淆)"""
        seen = {}
        for card, dt_set in CARD_GROUPS.items():
            for dt in dt_set:
                if dt in seen:
                    self.fail(f"data_type={dt} 重复出现在 {seen[dt]} 和 {card}")
                seen[dt] = card
        # 业务卡片应覆盖 6 大类业务 data_type(approval / config 不入卡片)
        covered = set()
        for s in CARD_GROUPS.values():
            covered.update(s)
        business_types = NEW_DATA_TYPES - {"config", "approval"}
        self.assertEqual(covered, business_types,
                         "业务卡片应覆盖除 config/approval 外的所有新 data_type")

    def test_legacy_map_contains_known(self):
        for old in ("material", "material_purchase", "purchase", "quality",
                    "quality_inspection", "repair", "outsource", "production", "config"):
            self.assertIn(old, LEGACY_TO_NEW, f"缺少旧值映射: {old}")

    def test_legacy_report_is_dynamic(self):
        """旧的 'report' 必须由 classify_pkg 动态判定,不能静态映射"""
        self.assertEqual(LEGACY_TO_NEW["report"], "__dynamic__")

    def test_process_flow_templates_has_4(self):
        self.assertEqual(len(PROCESS_FLOW_TEMPLATES), 4)
        for tpl in ("material_purchase", "production_6step",
                    "production_7step", "production_8step"):
            self.assertIn(tpl, PROCESS_FLOW_TEMPLATES)


# ────────────────────────────────────────────────────────────
# 2. classify_pkg 单条判定
# ────────────────────────────────────────────────────────────
class TestClassifyPkg(unittest.TestCase):
    def test_new_value_passthrough(self):
        """已是新枚举值,直接返回"""
        self.assertEqual(
            classify_pkg(_make_pkg("process_report", "焊接眼镜网"),
                         PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET),
            "process_report",
        )
        self.assertEqual(
            classify_pkg(_make_pkg("quality_task", "终检"),
                         PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET),
            "quality_task",
        )

    # 旧值静态映射
    def test_legacy_material_pickup(self):
        self.assertEqual(
            classify_pkg(_make_pkg("material", "不锈钢网带"),
                         PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET),
            "material_pickup",
        )

    def test_legacy_material_request(self):
        self.assertEqual(
            classify_pkg(_make_pkg("material_purchase", "不锈钢网带"),
                         PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET),
            "material_request",
        )

    def test_legacy_material_buy(self):
        self.assertEqual(
            classify_pkg(_make_pkg("purchase", "链条"),
                         PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET),
            "material_buy",
        )

    def test_legacy_quality(self):
        for dt in ("quality", "quality_inspection"):
            self.assertEqual(
                classify_pkg(_make_pkg(dt, "终检"),
                             PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET),
                "quality_task",
            )

    def test_legacy_repair(self):
        self.assertEqual(
            classify_pkg(_make_pkg("repair", "激光切板机"),
                         PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET),
            "equipment_repair",
        )

    def test_legacy_outsource(self):
        self.assertEqual(
            classify_pkg(_make_pkg("outsource", "热处理"),
                         PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET),
            "outsource_task",
        )

    def test_legacy_production(self):
        self.assertEqual(
            classify_pkg(_make_pkg("production", "排产发布"),
                         PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET),
            "flow_production",
        )

    def test_legacy_config(self):
        self.assertEqual(
            classify_pkg(_make_pkg("config", "字典缓存"),
                         PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET),
            "config",
        )

    def test_legacy_empty_to_config(self):
        self.assertEqual(
            classify_pkg(_make_pkg("", "未知"),
                         PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET),
            "config",
        )

    def test_legacy_approval_passthrough(self):
        """RE-006 新增:approval 旧值直通"""
        self.assertEqual(
            classify_pkg(_make_pkg("approval", "请假审批"),
                         PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET),
            "approval",
        )

    # 旧值 'report' 动态拆分
    def test_report_with_physical_process(self):
        """report + 物理工序名 → process_report"""
        self.assertEqual(
            classify_pkg(_make_pkg("report", "焊接眼镜网"),
                         PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET),
            "process_report",
        )
        self.assertEqual(
            classify_pkg(_make_pkg("report", "穿曲轴"),
                         PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET),
            "process_report",
        )

    def test_report_with_flow_step(self):
        """report + 流程步骤名 → flow_step"""
        self.assertEqual(
            classify_pkg(_make_pkg("report", "工单发布"),
                         PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET),
            "flow_step",
        )
        self.assertEqual(
            classify_pkg(_make_pkg("report", "排产制定"),
                         PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET),
            "flow_step",
        )
        self.assertEqual(
            classify_pkg(_make_pkg("report", "完工入库"),
                         PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET),
            "flow_step",
        )

    def test_report_with_content_flow_type_production(self):
        """report + content.flow_type='production' → flow_production"""
        self.assertEqual(
            classify_pkg(_make_pkg("report", "排产发布", {"flow_type": "production"}),
                         PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET),
            "flow_production",
        )

    def test_report_with_inspection_prefix(self):
        """report + related_process 以"质检-"开头 → quality_task"""
        self.assertEqual(
            classify_pkg(_make_pkg("report", "质检-终检"),
                         PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET),
            "quality_task",
        )
        self.assertEqual(
            classify_pkg(_make_pkg("report", "质检-首检", {"inspection_type": "首检"}),
                         PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET),
            "quality_task",
        )

    def test_report_with_material_keyword_and_qty(self):
        """report + 物料关键词 + quantity > 0 → material_request"""
        self.assertEqual(
            classify_pkg(_make_pkg("report", "备料-304不锈钢链条", {"quantity": 366}),
                         PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET),
            "material_request",
        )
        self.assertEqual(
            classify_pkg(_make_pkg("report", "304不锈钢穿杆", {"quantity": 150}),
                         PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET),
            "material_request",
        )

    def test_report_with_material_keyword_but_zero_qty(self):
        """物料关键词但 quantity=0 → 走物理工序 / 流程步骤判定"""
        self.assertEqual(
            classify_pkg(_make_pkg("report", "备料-无数量", {"quantity": 0}),
                         PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET),
            "__contract_violation__",  # 不在白名单 → 契约违反
        )

    def test_report_unknown_raises_violation(self):
        """report + 完全陌生 rp → __contract_violation__"""
        self.assertEqual(
            classify_pkg(_make_pkg("report", "完全未知的步骤XYZ"),
                         PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET),
            "__contract_violation__",
        )

    def test_unknown_data_type_raises_violation(self):
        self.assertEqual(
            classify_pkg(_make_pkg("xxx_invalid", "啥都行"),
                         PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET),
            "__contract_violation__",
        )

    def test_invalid_input(self):
        self.assertEqual(
            classify_pkg(None, PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET),
            "__contract_violation__",
        )
        self.assertEqual(
            classify_pkg("not a dict", PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET),
            "__contract_violation__",
        )

    def test_content_string_json(self):
        """content 是 JSON 字符串也能正确解析"""
        content_json = json.dumps({"flow_type": "production"}, ensure_ascii=False)
        self.assertEqual(
            classify_pkg(_make_pkg("report", "排产", content_json),
                         PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET),
            "flow_production",
        )


# ────────────────────────────────────────────────────────────
# 3. classify_payloads 批量归类
# ────────────────────────────────────────────────────────────
class TestClassifyPayloads(unittest.TestCase):
    def setUp(self):
        self.payloads = [
            _make_pkg("process_report", "焊接眼镜网"),
            _make_pkg("report", "穿曲轴"),  # 旧值 → 物理工序
            _make_pkg("report", "工单发布"),  # 旧值 → 流程步骤
            _make_pkg("material_purchase", "不锈钢链条"),
            _make_pkg("material", "不锈钢穿杆"),
            _make_pkg("quality", "终检"),
            _make_pkg("repair", "激光切板机"),
            _make_pkg("outsource", "热处理"),
            _make_pkg("report", "完全未知XYZ"),  # 契约违反
        ]

    def test_group_count_matches(self):
        result = classify_payloads(self.payloads, PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET)
        # process_report: 2 (新值 1 + 旧 report 1)
        self.assertEqual(len(result["process_report"]), 2)
        # flow_step: 1 (旧 report 1)
        self.assertEqual(len(result["flow_step"]), 1)
        # material_request: 1
        self.assertEqual(len(result["material_request"]), 1)
        # material_pickup: 1
        self.assertEqual(len(result["material_pickup"]), 1)
        # quality_task: 1
        self.assertEqual(len(result["quality_task"]), 1)
        # equipment_repair: 1
        self.assertEqual(len(result["equipment_repair"]), 1)
        # outsource_task: 1
        self.assertEqual(len(result["outsource_task"]), 1)
        # 契约违反: 1
        self.assertEqual(len(result["__contract_violation__"]), 1)

    def test_all_payloads_accounted(self):
        """所有 input 必须落到某个分组里"""
        result = classify_payloads(self.payloads, PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET)
        total = sum(len(v) for v in result.values())
        self.assertEqual(total, len(self.payloads))


# ────────────────────────────────────────────────────────────
# 4. group_by_card 6 张卡片分组
# ────────────────────────────────────────────────────────────
class TestGroupByCard(unittest.TestCase):
    """模拟 _core.py list_processes 归类逻辑,验证 6 张卡片准确"""

    def setUp(self):
        self.payloads = [
            # 工序报工
            _make_pkg("process_report", "焊接眼镜网"),
            _make_pkg("report", "穿曲轴"),  # 旧值拆分
            # 流程步骤
            _make_pkg("flow_production", "排产发布"),
            _make_pkg("report", "工单发布"),  # 旧值拆分
            _make_pkg("report", "排产制定"),  # 旧值拆分
            # 物料
            _make_pkg("material_purchase", "不锈钢链条"),
            _make_pkg("material", "不锈钢穿杆"),
            _make_pkg("purchase", "304不锈钢"),
            # 质检
            _make_pkg("quality", "终检"),
            # 维修
            _make_pkg("repair", "激光切板机"),
            # 外协
            _make_pkg("outsource", "热处理"),
        ]

    def test_six_cards_all_present(self):
        result = group_by_card(self.payloads, PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET)
        for card in CARD_GROUPS:
            self.assertIn(card, result)

    def test_process_tasks_count(self):
        result = group_by_card(self.payloads, PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET)
        self.assertEqual(len(result["process_tasks"]), 2)  # 1 新 + 1 旧

    def test_flow_steps_count(self):
        """流程步骤卡片 = flow_step + flow_production"""
        result = group_by_card(self.payloads, PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET)
        # flow_production: 1, flow_step(旧 report): 2
        self.assertEqual(len(result["flow_steps"]), 3)

    def test_material_tasks_count(self):
        """物料卡片 = material_request + material_pickup + material_buy"""
        result = group_by_card(self.payloads, PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET)
        self.assertEqual(len(result["material_tasks"]), 3)

    def test_quality_count(self):
        result = group_by_card(self.payloads, PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET)
        self.assertEqual(len(result["quality_tasks"]), 1)

    def test_repair_count(self):
        result = group_by_card(self.payloads, PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET)
        self.assertEqual(len(result["repair_tasks"]), 1)

    def test_outsource_count(self):
        result = group_by_card(self.payloads, PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET)
        self.assertEqual(len(result["outsource_tasks"]), 1)

    def test_cards_disjoint(self):
        """6 张卡片之间不能有重复元素(严格不混淆)"""
        result = group_by_card(self.payloads, PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET)
        seen_ids = []
        for card, items in result.items():
            for item in items:
                # 用 (data_type, related_process) 作为唯一键
                key = (item.get("data_type"), item.get("related_process"))
                self.assertNotIn(key, seen_ids,
                                 f"元素 {key} 重复出现在多张卡片中,分类不严格!")
                seen_ids.append(key)


# ────────────────────────────────────────────────────────────
# 5. 真实场景回归(从迁移日志摘出的 4 条契约违反 → 修复后)
# ────────────────────────────────────────────────────────────
class TestRealWorldScenarios(unittest.TestCase):
    """P2 数据迁移过程中发现的 4 条契约违反,修复后应正确归类"""

    def test_0828173e_flow_production(self):
        """0828173e: content.flow_type='production' → flow_production"""
        pkg = _make_pkg("report", "排产发布", {"flow_type": "production"})
        self.assertEqual(
            classify_pkg(pkg, PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET),
            "flow_production",
        )

    def test_27b948c6_material_request(self):
        """27B948C6: rp='304不锈钢链条' + quantity=366 → material_request"""
        pkg = _make_pkg("report", "304不锈钢链条", {"quantity": 366})
        self.assertEqual(
            classify_pkg(pkg, PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET),
            "material_request",
        )

    def test_72e29e2f_material_request(self):
        """72E29E2F: rp='304不锈钢穿杆' + quantity=150 → material_request"""
        pkg = _make_pkg("report", "304不锈钢穿杆", {"quantity": 150})
        self.assertEqual(
            classify_pkg(pkg, PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET),
            "material_request",
        )

    def test_82df2f9e_quality_task(self):
        """82DF2F9E: rp='质检-终检' → quality_task"""
        pkg = _make_pkg("report", "质检-终检")
        self.assertEqual(
            classify_pkg(pkg, PROCESS_NAMES_SET, FLOW_STEP_NAMES_SET),
            "quality_task",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
