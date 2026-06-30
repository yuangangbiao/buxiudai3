# -*- coding: utf-8 -*-
"""
排产工序测试中心
每步操作都有中文解释，帮助定位工序生成问题
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import get_connection, generate_work_order_no
from models.process_calc_rule import ProcessCalcEngine, ProcessCalcRuleDAO
from config import PROCESSES
from constants import ProcessStatus, OrderStatus, ProductionStatus
import json
import math


def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_step(step_no, title):
    print(f"\n{'─' * 50}")
    print(f"  【步骤{step_no}】{title}")
    print(f"{'─' * 50}")


def print_result(label, value, ok=True):
    symbol = "✅" if ok else "❌"
    print(f"  {symbol} {label}: {value}")


def print_warning(label, value):
    print(f"  ⚠️  {label}: {value}")


def print_info(label, value):
    print(f"  ℹ️  {label}: {value}")


class TestCenter:
    """排产工序测试中心"""

    def __init__(self):
        self.conn = get_connection()
        self.cursor = self.conn.cursor()

    def close(self):
        self.cursor.close()
        self.conn.close()

    def show_orders(self):
        """显示所有订单列表"""
        print_header("订单列表")

        self.cursor.execute("""
            SELECT o.id, o.order_no, o.product_type, o.status, o.quantity,
                   (SELECT COUNT(*) FROM production_orders WHERE order_id=o.id) as wo_count
            FROM orders o
            ORDER BY o.id
        """)
        orders = self.cursor.fetchall()

        print(f"\n  {'ID':<5} {'订单号':<22} {'产品类型':<14} {'状态':<8} {'数量':<8} {'工单':<5}")
        print(f"  {'─'*5} {'─'*22} {'─'*14} {'─'*8} {'─'*8} {'─'*5}")

        for o in orders:
            wo_mark = "有" if o['wo_count'] > 0 else "无"
            print(f"  {o['id']:<5} {o['order_no']:<22} {o['product_type']:<14} {o['status']:<8} {o['quantity']:<8} {wo_mark:<5}")

        print(f"\n  共 {len(orders)} 个订单")
        return orders

    def test_order(self, order_id):
        """对指定订单执行完整排产测试"""
        print_header(f"排产工序完整测试 - 订单ID={order_id}")

        # ========== 步骤1: 查询订单基本信息 ==========
        print_step(1, "查询订单基本信息")
        print_info("说明", "从 orders 表查询订单的产品类型、数量、规格等基础信息")

        self.cursor.execute("""
            SELECT id, order_no, quantity, product_type, mesh_size, customer_name, status
            FROM orders WHERE id=%s
        """, (order_id,))
        order_row = self.cursor.fetchone()

        if not order_row:
            print_result("查询结果", f"订单ID={order_id} 不存在!", ok=False)
            return

        print_result("订单号", order_row['order_no'])
        print_result("产品类型", f"'{order_row['product_type']}'")
        print_result("数量", order_row['quantity'])
        print_result("规格(mesh_size)", order_row['mesh_size'])
        print_result("客户", order_row['customer_name'])
        print_result("当前状态", order_row['status'])

        if not order_row['product_type']:
            print_warning("产品类型为空", "工序匹配将失败！请检查订单数据。")

        # ========== 步骤2: 检查是否已有工单 ==========
        print_step(2, "检查是否已有生产工单")
        print_info("说明", "一个订单只能有一个工单，如果已有则不能重复创建")

        self.cursor.execute("SELECT id, work_order_no, status FROM production_orders WHERE order_id=%s", (order_id,))
        existing = self.cursor.fetchone()

        if existing:
            print_result("已有工单", f"工单ID={existing['id']}, 订单号={existing['work_order_no']}, 状态={existing['status']}")
            print_info("提示", "该订单已有工单，实际排产时会被阻止。测试继续...")
        else:
            print_result("工单状态", "无工单，可以排产")

        # ========== 步骤3: 构建order_data ==========
        print_step(3, "构建 order_data 字典")
        print_info("说明", "将订单信息组装成字典，用于工序匹配和计算。product_type 和 产品类型 两个字段都要设置。")

        order_data = {
            "order_id": order_id,
            "quantity": order_row['quantity'] if order_row['quantity'] else 0,
            "product_type": order_row['product_type'] if order_row['product_type'] else "",
            "产品类型": order_row['product_type'] if order_row['product_type'] else "",
            "specs": str(order_row['mesh_size']) if order_row['mesh_size'] else "",
            "customer": order_row['customer_name'] if order_row['customer_name'] else "",
        }

        print_result("product_type", f"'{order_data['product_type']}'")
        print_result("产品类型", f"'{order_data['产品类型']}'")
        print_result("quantity", order_data['quantity'])
        print_result("specs", f"'{order_data['specs']}'")

        # ========== 步骤4: 获取 extra_params ==========
        print_step(4, "获取订单扩展参数 (extra_params)")
        print_info("说明", "尺寸参数（总长度、网带节距、螺旋直径等）存储在 extra_params JSON字段中，计算公式依赖这些参数")

        self.cursor.execute("SELECT extra_params FROM orders WHERE id=%s", (order_id,))
        extra_row = self.cursor.fetchone()

        extra_params = {}
        if extra_row and extra_row['extra_params']:
            try:
                raw = extra_row['extra_params']
                extra_params = json.loads(raw) if isinstance(raw, str) else raw
                if not isinstance(extra_params, dict):
                    extra_params = {}
                    print_warning("extra_params 不是字典", f"类型: {type(raw)}")
            except Exception as e:
                print_warning("extra_params 解析失败", str(e))
                extra_params = {}
        else:
            print_warning("extra_params 为空", "计算公式可能无法获取参数值，结果将为0")

        if extra_params:
            print_result("参数数量", f"{len(extra_params)} 个")
            for k, v in extra_params.items():
                print_info(f"  {k}", f"'{v}'")
            order_data.update(extra_params)
        else:
            print_warning("无扩展参数", "工序计算公式将无法获取尺寸参数，计划数量可能为0")

        # ========== 步骤5: 获取工序规则 ==========
        print_step(5, "获取工序计算规则")
        print_info("说明", "从 process_calc_rules 表获取所有规则，每条规则包含：工序名、适用产品类型、计算公式")

        rules = ProcessCalcRuleDAO.get_all()
        print_result("规则数量", f"{len(rules)} 条")

        for r in rules:
            enabled = r.get('enabled', True)
            pt_json = r.get('product_types_json', '')
            formula = r.get('planned_qty_formula', '')
            status_mark = "启用" if enabled else "禁用"

            try:
                pt_list = json.loads(pt_json) if isinstance(pt_json, str) else pt_json
                pt_str = ', '.join(pt_list) if isinstance(pt_list, list) else str(pt_json)
            except Exception as e:
                print(f"[test_center] 解析产品类型JSON失败: {e}")
                pt_str = str(pt_json)

            print(f"  {'🟢' if enabled else '🔴'} {r.get('process_name', '?'):<12} | 产品类型: {pt_str}")
            print(f"     公式: {formula if formula else '(无公式,默认1)'}")

        # ========== 步骤6: 逐个工序匹配测试 ==========
        print_step(6, "逐个工序匹配测试")
        print_info("说明", "对每个工序，检查订单的产品类型是否在该工序规则的 product_types_json 中")

        matched = []
        unmatched = []

        for idx, process_name in enumerate(PROCESSES, 1):
            result = ProcessCalcEngine.should_include_process(process_name, order_data, rules)

            if result:
                matched.append((idx, process_name))
                print(f"  ✅ {idx:>2}. {process_name:<12} → 匹配成功（产品类型在规则中）")
            else:
                # 找出原因
                reason = self._get_unmatch_reason(process_name, order_data, rules)
                unmatched.append((idx, process_name))
                print(f"  ❌ {idx:>2}. {process_name:<12} → 不匹配（{reason}）")

        print(f"\n  匹配结果: {len(matched)} 个工序匹配, {len(unmatched)} 个不匹配")

        # ========== 步骤7: 计算每个匹配工序的计划数量 ==========
        print_step(7, "计算每个匹配工序的计划数量")
        print_info("说明", "对匹配的工序，使用规则中的公式和订单参数计算计划数量，结果向上取整")

        for seq, process_name in matched:
            planned_qty = ProcessCalcEngine.calculate_planned_qty_for_process(process_name, rules, order_data)
            formula = self._get_formula(process_name, rules)

            print(f"\n  📊 {process_name}:")
            print(f"     公式: {formula if formula else '(无公式)'}")

            if formula:
                self._explain_calculation(formula, order_data)

            print(f"     计算结果: {planned_qty}")

            if planned_qty == 0:
                print_warning("计划数量为0", "公式中的参数值可能缺失或为0，请检查订单的尺寸参数")

        # ========== 步骤8: 完整生成工序 ==========
        print_step(8, "完整生成工序列表")
        print_info("说明", "调用 ProcessCalcEngine.generate_processes_from_order 生成完整工序列表")

        generated = ProcessCalcEngine.generate_processes_from_order(order_data, list(PROCESSES))

        if generated:
            print_result("生成工序数量", f"{len(generated)} 道")
            print(f"\n  {'序号':<6} {'工序名称':<14} {'计划数量':<10}")
            print(f"  {'─'*6} {'─'*14} {'─'*10}")
            for p in generated:
                qty_mark = " ⚠️为0" if p['planned_qty'] == 0 else ""
                print(f"  {p['process_seq']:<6} {p['process_name']:<14} {p['planned_qty']:<10}{qty_mark}")
        else:
            print_result("生成结果", "0 道工序!", ok=False)
            print_warning("原因", "没有任何工序匹配成功，请检查步骤6的匹配结果")

        # ========== 步骤9: 数据库写入测试 ==========
        print_step(9, "数据库写入测试（仅验证，不实际写入）")
        print_info("说明", "验证 SQL 语句和字段是否正确，不实际执行 INSERT")

        if generated:
            print_result("INSERT process_records", f"将写入 {len(generated)} 条工序记录")
            for p in generated:
                sql = f"INSERT INTO process_records (order_id, production_id, process_name, process_seq, planned_qty, status) VALUES ({order_id}, <prod_id>, '{p['process_name']}', {p['process_seq']}, {p['planned_qty']}, '{ProcessStatus.PENDING.value}')"
                print(f"  📝 {sql}")
        else:
            print_warning("无工序可写入", "请先解决工序匹配问题")

        # ========== 步骤10: 总结 ==========
        print_step(10, "测试总结")

        issues = []

        if not order_row['product_type']:
            issues.append("订单产品类型为空，无法匹配工序规则")

        if not extra_params:
            issues.append("订单缺少尺寸参数(extra_params)，计算公式结果将为0")

        zero_count = sum(1 for p in generated if p['planned_qty'] == 0) if generated else 0
        if zero_count > 0:
            issues.append(f"{zero_count} 道工序计划数量为0，公式参数可能缺失")

        if not generated:
            issues.append("没有生成任何工序！请检查工序规则配置")

        if not rules:
            issues.append("工序规则表为空！请先配置工序计算规则")

        if issues:
            print_warning("发现以下问题", "")
            for i, issue in enumerate(issues, 1):
                print(f"  {i}. ❌ {issue}")
        else:
            print_result("所有检查通过", "工序生成逻辑正常")

        return generated

    def _get_unmatch_reason(self, process_name, order_data, rules):
        """获取工序不匹配的原因"""
        order_product_type = order_data.get("product_type") or order_data.get("产品类型", "")

        for rule in rules:
            if rule.get("process_name") == process_name:
                pt_json = rule.get("product_types_json")
                if not pt_json:
                    return "规则的product_types_json为空"

                try:
                    pt_list = json.loads(pt_json) if isinstance(pt_json, str) else pt_json
                    if not pt_list:
                        return "规则的产品类型列表为空"
                    if order_product_type in pt_list:
                        return "BUG: 应该匹配但未匹配"
                    return f"'{order_product_type}' 不在 {pt_list}"
                except Exception as e:
                    return f"解析异常: {e}"

        return "该工序没有配置规则"

    def _get_formula(self, process_name, rules):
        """获取工序的计算公式"""
        for rule in rules:
            if rule.get("process_name") == process_name:
                return rule.get("planned_qty_formula", "")
        return ""

    def _explain_calculation(self, formula, order_data):
        """解释计算公式的每一步"""
        tokens = self._tokenize_formula(formula)
        for token in tokens:
            if token in ['+', '-', '*', '/', '(', ')']:
                continue
            if token.replace('.', '').replace('-', '').isdigit():
                print(f"     常量: {token}")
            elif token in order_data:
                val = order_data[token]
                print(f"     参数: {token} = {val}")
            else:
                print(f"     ⚠️ 未知参数: {token} (不在订单数据中，将为0)")

    def _tokenize_formula(self, formula):
        """简单分词"""
        import re
        tokens = re.findall(r'[a-zA-Z_\u4e00-\u9fff]+|\d+\.?\d*|[+\-*/()]', formula)
        return tokens

    def test_create_production(self, order_id):
        """实际执行排产并验证结果"""
        print_header(f"实际排产测试 - 订单ID={order_id}")

        # 先检查是否已有工单
        self.cursor.execute("SELECT id FROM production_orders WHERE order_id=%s", (order_id,))
        existing = self.cursor.fetchone()
        if existing:
            print_warning("已有工单", f"工单ID={existing['id']}，跳过创建")
            print_info("提示", "如需重新测试，请先删除该工单")
            return

        try:
            from models.production import ProductionDAO
            print_info("正在创建工单...", "")
            prod_id = ProductionDAO.create(order_id, {"priority": 5})
            print_result("工单创建成功", f"工单ID={prod_id}")

            # 验证工序
            self.cursor.execute("SELECT COUNT(*) as cnt FROM process_records WHERE production_id=%s", (prod_id,))
            cnt = self.cursor.fetchone()['cnt']
            print_result("工序数量", f"{cnt} 道")

            self.cursor.execute("""
                SELECT process_seq, process_name, planned_qty, status
                FROM process_records WHERE production_id=%s ORDER BY process_seq
            """, (prod_id,))
            records = self.cursor.fetchall()

            for r in records:
                qty_mark = " ⚠️为0" if r['planned_qty'] == 0 else ""
                print(f"  {r['process_seq']}. {r['process_name']} = {r['planned_qty']} ({r['status']}){qty_mark}")

        except Exception as e:
            print_result("排产失败", f"{type(e).__name__}: {e}", ok=False)
            import traceback
            traceback.print_exc()

    def test_rules_config(self):
        """检查工序规则配置"""
        print_header("工序规则配置检查")

        rules = ProcessCalcRuleDAO.get_all()
        all_processes = list(PROCESSES)

        print_info("说明", "检查每个工序是否都有对应的规则配置")

        rule_processes = set()
        for r in rules:
            rule_processes.add(r.get('process_name'))

        print(f"\n  系统工序总数: {len(all_processes)}")
        print(f"  规则配置数: {len(rules)}")
        print(f"  有规则的工序: {len(rule_processes)}")

        missing = set(all_processes) - rule_processes
        if missing:
            print_warning("以下工序没有规则配置", "")
            for p in missing:
                print(f"    ❌ {p} - 将永远不会被匹配（should_include_process返回False）")
        else:
            print_result("所有工序都有规则", "✅")

        # 检查规则中的产品类型
        print(f"\n  {'工序名称':<14} {'启用':<5} {'产品类型列表'}")
        print(f"  {'─'*14} {'─'*5} {'─'*40}")

        all_product_types = set()
        for r in rules:
            pt_json = r.get('product_types_json', '')
            try:
                pt_list = json.loads(pt_json) if isinstance(pt_json, str) else pt_json
                if isinstance(pt_list, list):
                    for pt in pt_list:
                        all_product_types.add(pt)
            except Exception as e:
                print(f"[test_center] 收集产品类型JSON失败: {e}")

        print(f"\n  规则中涉及的所有产品类型: {sorted(all_product_types)}")

        # 检查数据库中实际的产品类型
        self.cursor.execute("SELECT DISTINCT product_type FROM orders WHERE product_type IS NOT NULL AND product_type != ''")
        db_types = set(r['product_type'] for r in self.cursor.fetchall())
        print(f"  数据库中实际的产品类型: {sorted(db_types)}")

        unmatched_types = db_types - all_product_types
        if unmatched_types:
            print_warning("以下产品类型在规则中没有配置", "")
            for t in sorted(unmatched_types):
                print(f"    ❌ {t} - 使用此类型的订单将无法匹配任何工序")


def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║          排产工序测试中心 v1.0                          ║")
    print("║          每步操作都有中文解释                           ║")
    print("╚══════════════════════════════════════════════════════════╝")

    tc = TestCenter()

    while True:
        print("\n" + "─" * 50)
        print("  请选择测试项目:")
        print("  1. 显示所有订单列表")
        print("  2. 对指定订单执行完整排产测试（不写入数据库）")
        print("  3. 对指定订单执行实际排产（写入数据库）")
        print("  4. 检查工序规则配置")
        print("  5. 退出")
        print("─" * 50)

        choice = input("  请输入选项 (1-5): ").strip()

        if choice == '1':
            tc.show_orders()

        elif choice == '2':
            order_id = input("  请输入订单ID: ").strip()
            if order_id.isdigit():
                tc.test_order(int(order_id))
            else:
                print("  ❌ 无效的订单ID")

        elif choice == '3':
            order_id = input("  请输入订单ID: ").strip()
            if order_id.isdigit():
                tc.test_create_production(int(order_id))
            else:
                print("  ❌ 无效的订单ID")

        elif choice == '4':
            tc.test_rules_config()

        elif choice == '5':
            print("\n  再见！")
            break
        else:
            print("  ❌ 无效选项")

    tc.close()


if __name__ == "__main__":
    main()