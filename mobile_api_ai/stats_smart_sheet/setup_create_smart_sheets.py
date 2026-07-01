# -*- coding: utf-8 -*-
"""
智能表格 API 创建脚本
自动化创建 9 张智能表格（需企业微信 CorpID + Secret）

用法：
1. 在企业微信管理后台创建自建应用，获取 AgentId + Secret
2. 配置 .env 中的 WECHAT_CORP_ID / WECHAT_APP_SECRET / WECHAT_APP_AGENT_ID
3. 运行: python setup_create_smart_sheets.py --dry-run  (先预览)
   运行: python setup_create_smart_sheets.py           (实际创建)

注意：智能表格 API 需要企业微信「办公版」或「专业版」，
且应用需要有「智能表格」权限。
"""
import os
import sys
import json
import argparse
import requests
from dotenv import load_dotenv

load_dotenv('.env', override=True)


def get_access_token(corp_id: str, secret: str) -> str:
    """获取应用 AccessToken"""
    url = 'https://qyapi.weixin.qq.com/cgi-bin/gettoken'
    resp = requests.get(url, params={'corpid': corp_id, 'corpsecret': secret}, timeout=10)
    result = resp.json()
    if result.get('errcode') != 0:
        raise RuntimeError(f"获取 access_token 失败: {result}")
    return result['access_token']


def create_smartsheet(token: str, name: str, field_schemas: list) -> dict:
    """创建智能表格（doc）"""
    url = 'https://qyapi.weixin.qq.com/cgi-bin/wedoc/smartsheet/create'
    payload = {
        'title': name,
        'fields': [{'field_name': f['name'], 'field_type': f.get('type', 1)}
                   for f in field_schemas],
    }
    resp = requests.post(url, params={'access_token': token}, json=payload, timeout=30)
    return resp.json()


# 9 张表的字段定义（企业微信智能表格字段类型: 1=文本 2=数字 3=日期 4=时间 5=单选 6=多选 9=百分比）
FIELD_DEFINITIONS = [
    # 1. 生产日报
    ('production_daily_report', '工单-生产日报', [
        {'name': '记录ID', 'type': 1},
        {'name': '日期', 'type': 3},
        {'name': '班组', 'type': 5},
        {'name': '产线', 'type': 1},
        {'name': '计划数', 'type': 2},
        {'name': '完成数', 'type': 2},
        {'name': '差异率', 'type': 9},
        {'name': '合格率', 'type': 9},
        {'name': '操作员', 'type': 1},
        {'name': '备注', 'type': 1},
        {'name': '写入时间', 'type': 1},
    ]),
    # 2. 生产月报
    ('production_monthly_report', '工单-生产月报', [
        {'name': '记录ID', 'type': 1},
        {'name': '月份', 'type': 1},
        {'name': '产线', 'type': 1},
        {'name': '计划数', 'type': 2},
        {'name': '完成数', 'type': 2},
        {'name': '产能利用率', 'type': 9},
        {'name': '达成率', 'type': 9},
        {'name': '订单数', 'type': 2},
        {'name': '停机时长(h)', 'type': 2},
        {'name': '备注', 'type': 1},
        {'name': '写入时间', 'type': 1},
    ]),
    # 3. 车间产能分析
    ('workshop_capacity', '工单-车间产能分析', [
        {'name': '记录ID', 'type': 1},
        {'name': '车间', 'type': 1},
        {'name': '设备', 'type': 1},
        {'name': '日期', 'type': 3},
        {'name': '工时(h)', 'type': 2},
        {'name': '有效工时(h)', 'type': 2},
        {'name': '停机时长(h)', 'type': 2},
        {'name': 'OEE', 'type': 9},
        {'name': '性能率', 'type': 9},
        {'name': '合格率', 'type': 9},
        {'name': '写入时间', 'type': 1},
    ]),
    # 4. 工单进度跟踪
    ('workorder_progress', '工单-工单进度跟踪', [
        {'name': '工单号', 'type': 1},
        {'name': '客户', 'type': 1},
        {'name': '产品', 'type': 1},
        {'name': '计划开始', 'type': 3},
        {'name': '计划完工', 'type': 3},
        {'name': '实际开始', 'type': 3},
        {'name': '实际完工', 'type': 3},
        {'name': '当前工序', 'type': 1},
        {'name': '完成工序', 'type': 2},
        {'name': '总工序', 'type': 2},
        {'name': '进度条', 'type': 9},
        {'name': '状态', 'type': 5},
        {'name': '写入时间', 'type': 1},
    ]),
    # 5. 工序报工汇总
    ('substep_report', '工单-工序报工汇总', [
        {'name': '记录ID', 'type': 1},
        {'name': '工单号', 'type': 1},
        {'name': '工序', 'type': 1},
        {'name': '操作人', 'type': 1},
        {'name': '批次号', 'type': 1},
        {'name': '报工数', 'type': 2},
        {'name': '合格数', 'type': 2},
        {'name': '合格率', 'type': 9},
        {'name': '报工时间', 'type': 1},
        {'name': '备注', 'type': 1},
        {'name': '写入时间', 'type': 1},
    ]),
    # 6. 库存周报
    ('inventory_weekly_report', '库存-库存周报', [
        {'name': '记录ID', 'type': 1},
        {'name': '周次', 'type': 1},
        {'name': '周起始日期', 'type': 3},
        {'name': '周结束日期', 'type': 3},
        {'name': '仓库', 'type': 1},
        {'name': '入库数', 'type': 2},
        {'name': '出库数', 'type': 2},
        {'name': '库存余额', 'type': 2},
        {'name': '库存金额', 'type': 2},
        {'name': '异动笔数', 'type': 2},
        {'name': '写入时间', 'type': 1},
    ]),
    # 7. 物料收发存汇总
    ('inventory_monthly_summary', '库存-物料收发存汇总', [
        {'name': '记录ID', 'type': 1},
        {'name': '月份', 'type': 1},
        {'name': '物料编码', 'type': 1},
        {'name': '物料名称', 'type': 1},
        {'name': '期初数量', 'type': 2},
        {'name': '入库数量', 'type': 2},
        {'name': '出库数量', 'type': 2},
        {'name': '期末数量', 'type': 2},
        {'name': '单价', 'type': 2},
        {'name': '期末金额', 'type': 2},
        {'name': '写入时间', 'type': 1},
    ]),
    # 8. 库存预警
    ('inventory_alert', '库存-库存预警', [
        {'name': '物料编码', 'type': 1},
        {'name': '物料名称', 'type': 1},
        {'name': '仓库', 'type': 1},
        {'name': '当前库存', 'type': 2},
        {'name': '安全库存', 'type': 2},
        {'name': '预警状态', 'type': 5},
        {'name': '建议补货量', 'type': 2},
        {'name': '最近入库时间', 'type': 3},
        {'name': '写入时间', 'type': 1},
    ]),
    # 9. 呆滞料分析
    ('inventory_slow_moving', '库存-呆滞料分析', [
        {'name': '物料编码', 'type': 1},
        {'name': '物料名称', 'type': 1},
        {'name': '仓库', 'type': 1},
        {'name': '当前库存', 'type': 2},
        {'name': '最后异动日期', 'type': 3},
        {'name': '库龄(天)', 'type': 2},
        {'name': '单价', 'type': 2},
        {'name': '库存金额', 'type': 2},
        {'name': '状态', 'type': 5},
        {'name': '写入时间', 'type': 1},
    ]),
]


def main():
    parser = argparse.ArgumentParser(description='创建 9 张智能表格')
    parser.add_argument('--dry-run', action='store_true', help='仅预览，不实际创建')
    parser.add_argument('--corp-id', default=os.getenv('WECHAT_CORP_ID', ''),
                        help='企业 ID')
    parser.add_argument('--app-secret', default=os.getenv('WECHAT_APP_SECRET', ''),
                        help='应用 Secret')
    args = parser.parse_args()

    if not args.corp_id or not args.app_secret:
        print("❌ 请设置 WECHAT_CORP_ID 和 WECHAT_APP_SECRET 环境变量")
        print("   或使用 --corp-id 和 --app-secret 参数")
        sys.exit(1)

    print("=" * 60)
    print("智能表格批量创建脚本")
    print("=" * 60)
    print(f"CorpID: {args.corp_id}")
    print(f"模式: {'DRY-RUN（仅预览）' if args.dry_run else '实际创建'}")
    print()

    if args.dry_run:
        print("📋 预览将创建的 9 张表格：")
        for key, name, fields in FIELD_DEFINITIONS:
            print(f"\n  📊 {name} ({key})")
            for f in fields:
                print(f"     - {f['name']} [type={f['type']}]")
        return

    print("🔑 获取 access_token...")
    try:
        token = get_access_token(args.corp_id, args.app_secret)
        print(f"  ✅ token 获取成功")
    except Exception as e:
        print(f"  ❌ {e}")
        sys.exit(1)

    results = {}
    for key, name, fields in FIELD_DEFINITIONS:
        print(f"\n📋 创建: {name}...", end=' ', flush=True)
        try:
            result = create_smartsheet(token, name, fields)
            if result.get('errcode') == 0:
                docid = result.get('smartsheet', {}).get('docid', '')
                print(f"✅ docid={docid}")
                results[key] = {'docid': docid, 'sheet_id': docid}
            else:
                print(f"❌ errcode={result.get('errcode')} errmsg={result.get('errmsg')}")
                results[key] = {'error': result.get('errmsg')}
        except Exception as e:
            print(f"❌ {e}")
            results[key] = {'error': str(e)}

    # 输出结果
    print("\n" + "=" * 60)
    print("创建结果汇总：")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print("=" * 60)
    print("💡 后续步骤：")
    print("   1. 将上述 docid 填入 TABLE_INDEX.json")
    print("   2. 将 TABLE_INDEX.json 放到 stats_smart_sheet/ 目录")
    print("   3. 配置 WECHAT_SMARTSHEET_KEY 环境变量")


if __name__ == '__main__':
    main()
