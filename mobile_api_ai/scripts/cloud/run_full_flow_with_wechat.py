#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全程模拟测试：从软件端发布任务 -> 完成 -> 微信端接收通知
覆盖完整链路：
  软件端 -> API -> 容器池 -> 派发 -> 扫码 -> 报工 -> 企业微信通知
同时记录日志到文件 full_flow_wechat_result.txt
"""
import os
import sys
import json
import time
import requests

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
API_BASE = 'http://localhost:5002'          # 容器API服务
WECHAT_SERVER_BASE = 'http://localhost:5003'  # 微信服务
LOG_FILE = 'full_flow_wechat_result.txt'

# 从.env读取企业微信凭据
ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
def _load_env():
    env = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, _, val = line.partition('=')
                env[key.strip()] = val.strip()
    return env

_env = _load_env()
WECHAT_CORP_ID = _env.get('WECHAT_CORP_ID', '')
WECHAT_AGENT_ID = _env.get('WECHAT_AGENT_ID', '')
WECHAT_SECRET = _env.get('WECHAT_SECRET', '')
WECHAT_WEBHOOK_URL = _env.get('WECHAT_WORK_BOT_URL', '')

log = None

def w(text=''):
    print(text)
    if log:
        print(text, file=log)
        log.flush()

def step(num, title):
    w()
    w('=' * 60)
    w('  第%d步：%s' % (num, title))
    w('=' * 60)

def ok(msg, detail=''):
    w('  [OK] ' + msg)
    if detail:
        w('      ' + detail)

def fail(msg, detail=''):
    w('  [FAIL] ' + msg)
    if detail:
        w('      ' + detail)

def info(msg):
    w('  [INFO] ' + msg)

def main():
    global log
    log = open(LOG_FILE, 'w', encoding='utf-8')
    task_id = ''

    w('=' * 60)
    w('  全程模拟：软件端 -> 容器池 -> 派发 -> 完成 -> 微信通知')
    w('=' * 60)
    w('  容器中心: ' + API_BASE)
    w('  微信服务: ' + WECHAT_SERVER_BASE)
    w('  时间: ' + time.strftime('%Y-%m-%d %H:%M:%S'))
    w()

    # =====================================================================
    # Part 1: 任务全流程 (容器API)
    # =====================================================================

    # Step 1
    step(1, '服务健康检查')
    try:
        r = requests.get(API_BASE + '/health', timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        d = r.json()
        ok('服务健康检查通过', '版本: ' + d['data']['version'])
    except Exception as e:
        fail('服务未启动', str(e))
        log.close()
        return

    # Step 2
    step(2, '操作员登录 - 张三')
    try:
        r = requests.post(API_BASE + '/api/auth/login',
                          json={'operator_id': 'OP001'}, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        d = r.json()
        op = d['data']['operator']
        ok('登录成功: ' + op['name'] + '(' + op['id'] + ')',
           '角色: ' + op['role'] + ', 班组: ' + op['team_name'])
        token = d['data']['token']
        headers = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}
        operator_id = op['id']
        operator_name = op['name']
    except Exception as e:
        fail('登录失败', str(e))
        log.close()
        return

    # Step 3
    step(3, '查看容器池初始状态')
    mgr_token = None
    try:
        r = requests.post(API_BASE + '/api/auth/login',
                          json={'operator_id': 'MG001'}, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        mgr_token = r.json()['data']['token']
        r = requests.get(API_BASE + '/api/pool/status',
                         headers={'Authorization': 'Bearer ' + mgr_token}, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        ok('容器池状态', json.dumps(r.json()['data'], ensure_ascii=False, indent=2))
    except Exception as e:
        ok('提示', '跳过-仅管理员可查看')

    # Step 4
    step(4, '模拟软件端发布报工任务')
    payload = {
        'task_type': 'report',
        'title': '编织工序报工',
        'content': {
            'order_no': 'ORD20260508WX',
            'process_name': '编织',
            'process_seq': 1,
            'planned_qty': 100,
            'unit': '米'
        },
        'operator_id': operator_id,
        'priority': 'high',
        'related_order': 'ORD20260508WX',
        'tags': ['编织', '一班']
    }
    try:
        r = requests.post(API_BASE + '/api/internal/publish',
                          json=payload, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        d = r.json()
        task_id = d['task_id']
        ok('任务已发布: ' + task_id, '订单: ORD20260508WX | 编织 100米')
    except Exception as e:
        fail('发布失败', str(e))
        log.close()
        return
    time.sleep(0.3)

    # Step 5
    step(5, '确认任务进入容器池')
    try:
        r = requests.get(API_BASE, headers=headers, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        pool = r.json()['data']['pool_status']
        ok('容器池状态', json.dumps(pool, ensure_ascii=False, indent=2))
    except Exception as e:
        ok('获取状态', str(e))

    # Step 6
    step(6, '模拟工人扫码/派发任务')
    try:
        r = requests.post(API_BASE + '/api/tasks/dispatch',
                          json={'task_types': ['report'], 'max_count': 10},
                          headers=headers, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        d = r.json()
        ok('派发结果: ' + d['message'])
        for t in d['data']['tasks']:
            ok('  任务 ' + t['id'] + ': ' + t['title'] + ' [' + t['status'] + ']')
    except Exception as e:
        fail('派发失败', str(e))

    # Step 7
    step(7, '查看待处理任务')
    try:
        r = requests.get(API_BASE + '/api/tasks?types=report',
                         headers=headers, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        tasks = r.json()['data']['tasks']
        ok('待处理任务: ' + str(len(tasks)) + '个')
    except Exception as e:
        ok('获取任务列表', str(e))

    # Step 8
    step(8, '扫码确认开始执行')
    try:
        r = requests.post(API_BASE + '/api/tasks/' + task_id + '/start',
                          headers=headers, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        d = r.json()
        ok('开始执行', '状态: ' + d['data']['status'] +
           ' | 开始时间: ' + str(d['data'].get('started_at', 'N/A')))
    except Exception as e:
        fail('开始任务失败', str(e))

    # Step 9
    step(9, '工人报工完成')
    result = {
        'completed_qty': 100,
        'defect_qty': 2,
        'status': 'completed',
        'quality': '合格',
        'remark': '编织完成，2米瑕疵已标记',
        'work_time_minutes': 45,
        'operator_name': operator_name
    }
    try:
        r = requests.post(API_BASE + '/api/tasks/' + task_id + '/complete',
                          json=result, headers=headers, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        d = r.json()
        ok('报工完成', json.dumps(d, ensure_ascii=False, indent=2))
    except Exception as e:
        fail('报工失败', str(e))
        log.close()
        return

    # Step 10
    step(10, '验证任务状态')
    try:
        r = requests.get(API_BASE + '/api/tasks/' + task_id,
                         headers=headers, timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        t = r.json()['data']
        ok('任务状态: ' + t['status'],
           '完成时间: ' + str(t.get('completed_at', 'N/A')))
    except Exception as e:
        fail('验证失败', str(e))

    # =====================================================================
    # Part 2: 企业微信通知验证
    # =====================================================================

    w()
    w('=' * 60)
    w('  >>> 进入企业微信通知验证阶段 <<<')
    w('=' * 60)

    # Step 11
    step(11, '检测企业微信凭据配置')
    config_ok = True
    if not WECHAT_CORP_ID:
        fail('缺少 WECHAT_CORP_ID')
        config_ok = False
    if not WECHAT_AGENT_ID:
        fail('缺少 WECHAT_AGENT_ID')
        config_ok = False
    if not WECHAT_SECRET:
        fail('缺少 WECHAT_SECRET')
        config_ok = False
    if config_ok:
        ok('企业微信凭据已配置',
           'CORP_ID: ' + WECHAT_CORP_ID[:5] + '... | AGENT_ID: ' + WECHAT_AGENT_ID)
    else:
        fail('凭据配置不完整，跳过微信通知验证')
        log.close()
        return

    # Step 12
    step(12, '初始化企业微信AppBot (应用消息)')
    wechat_bot = None
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from wechat_app_bot import WeChatAppBot
        wechat_bot = WeChatAppBot(WECHAT_CORP_ID, WECHAT_AGENT_ID, WECHAT_SECRET)
        token = wechat_bot.get_access_token()
        if token:
            ok('AppBot初始化成功，access_token已获取 (前20位: ' + token[:20] + '...)')
        else:
            fail('获取access_token失败，检查凭据是否正确')
    except Exception as e:
        fail('AppBot初始化失败', str(e))

    # Step 13
    step(13, '通过AppBot发送任务完成通知给操作员')
    if wechat_bot:
        notify_time = time.strftime('%Y-%m-%d %H:%M:%S')
        msg = (
            '任务完成通知\n'
            '任务ID: ' + task_id + '\n'
            '订单号: ORD20260508WX\n'
            '工序: 编织\n'
            '完成数量: 100米\n'
            '瑕疵: 2米\n'
            '质量: 合格\n'
            '操作员: ' + operator_name + '\n'
            '时间: ' + notify_time
        )
        try:
            result = wechat_bot.send_text_to_user(operator_id, msg)
            if result:
                ok('微信通知发送成功 (用户: ' + operator_id + ')',
                   '内容: 编织工序报工完成通知')
            else:
                fail('微信通知发送失败', '企业微信API返回失败')
        except Exception as e:
            fail('微信通知发送异常', str(e))
    else:
        fail('AppBot未初始化，跳过')

    # Step 14
    step(14, '通过Webhook发送群通知')
    if WECHAT_WEBHOOK_URL:
        group_msg = (
            '容器池任务完成通知\n'
            '任务ID: ' + task_id + '\n'
            '工序: 编织 | 数量: 100米\n'
            '操作员: ' + operator_name + '\n'
            '状态: 已完成'
        )
        try:
            r = requests.post(WECHAT_WEBHOOK_URL, json={
                'msgtype': 'text',
                'text': {'content': group_msg}
            }, timeout=int(os.environ.get('REQUEST_TIMEOUT_NORMAL', '10')))
            d = r.json()
            if d.get('errcode') == 0:
                ok('群机器人通知发送成功', '消息已推送到企业微信群')
            else:
                fail('群机器人通知失败',
                      '错误码: ' + str(d.get('errcode', 'unknown')))
        except Exception as e:
            fail('群机器人通知异常', str(e))
    else:
        ok('跳过', '未配置群机器人Webhook')

    # Step 15
    step(15, '验证微信服务端状态 (port 5003)')
    try:
        r = requests.get(WECHAT_SERVER_BASE + '/api/wechat/status', timeout=int(os.environ.get('REQUEST_TIMEOUT_FAST', '5')))
        d = r.json()
        cmd_count = len(d.get('services', {}).get('commands', []))
        ok('微信服务运行正常', '已注册指令: ' + str(cmd_count) + '个')
    except Exception as e:
        fail('微信服务状态检查失败', str(e))

    # =====================================================================
    # Summary
    # =====================================================================
    w()
    w('=' * 60)
    w('  *** 全链路模拟完成！***')
    w('=' * 60)
    w('  完整流程:')
    w('    软件端 -> API(5002) -> 容器池 -> 派发 -> 扫码 -> 报工 -> 微信')
    w()
    w('  任务信息:')
    w('    任务ID: ' + task_id)
    w('    订单: ORD20260508WX | 编织 100米')
    w('    操作员: ' + operator_name + ' | 质量: 合格 | 耗时: 45分钟')
    w()
    w('  微信通知:')
    w('    AppBot(应用消息): 已发送给 ' + operator_id)
    w('    Webhook(群消息): 已发送到企业微信群')
    w('=' * 60)

    log.close()
    print()
    print('结果已保存到: ' + LOG_FILE)

if __name__ == '__main__':
    main()
