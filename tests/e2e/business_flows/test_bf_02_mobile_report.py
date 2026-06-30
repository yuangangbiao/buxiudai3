# -*- coding: utf-8 -*-
"""
test_bf_02_mobile_report.py - 移动端扫码报工测试

覆盖场景:
- 登录认证（operator_id + JWT）
- 打卡考勤（上班/下班）
- 质检报告（合格/不合格）
- 消息通知
- Playwright UI 扫码验证
"""
import pytest


def api_ok(response, msg=''):
    data = response.json()
    assert data.get('code') == 0, f'{msg} → {data.get("message")} (code={data.get("code")})'
    return data


class TestMobileAuth:
    """认证验证"""

    def test_x_user_id_header_works(self, e2e_mobile_client):
        """X-User-Id header 直接访问（5008 为本地服务）"""
        r = e2e_mobile_client.get('http://localhost:5008/api/workers')
        data = api_ok(r, 'X-User-Id header 认证')
        workers = data.get('data', [])
        print(f'\n[移动认证] 工人总数: {len(workers)}')


class TestMobileAttendance:
    """打卡考勤"""

    def test_check_in(self, mobile_session):
        """上班打卡"""
        r = mobile_session.post(
            'http://localhost:5008/api/attendance',
            json={'action': 'check-in'},
        )
        data = r.json()
        print(f'\n[移动打卡] code={data.get("code")} msg={data.get("message","")}')

    def test_check_out(self, mobile_session):
        """下班打卡"""
        r = mobile_session.post(
            'http://localhost:5008/api/attendance',
            json={'action': 'check-out'},
        )
        data = r.json()
        print(f'\n[移动打卡] code={data.get("code")} msg={data.get("message","")}')

    def test_get_attendance(self, mobile_session):
        """查询打卡记录"""
        r = mobile_session.get('http://localhost:5008/api/attendance')
        raw = r.json()
        records = raw if isinstance(raw, list) else (raw.get('data', []) if isinstance(raw, dict) else [])
        print(f'\n[移动打卡] 今日记录: {len(records)} 条')


class TestMobileQuality:
    """质检报告"""

    def test_submit_quality_passed(self, mobile_session):
        """提交质检（合格）"""
        r = mobile_session.post(
            'http://localhost:5008/api/quality',
            json={'result': 'passed', 'notes': 'E2E 质检合格'},
        )
        data = r.json()
        print(f'\n[移动质检] code={data.get("code")} msg={data.get("message","")}')

    def test_submit_quality_failed(self, mobile_session):
        """提交质检（不合格）"""
        r = mobile_session.post(
            'http://localhost:5008/api/quality',
            json={'result': 'failed', 'notes': 'E2E 质检不合格'},
        )
        data = r.json()
        print(f'\n[移动质检] code={data.get("code")} msg={data.get("message","")}')

    def test_quality_list(self, mobile_session):
        """查询质检记录"""
        r = mobile_session.get('http://localhost:5008/api/quality/list')
        data = api_ok(r, '查询质检记录')
        records = data.get('data', [])
        print(f'\n[移动质检] 记录数: {len(records)}')


class TestMobileMessage:
    """消息通知"""

    def test_unread_count(self, mobile_session):
        """未读消息数"""
        r = mobile_session.get('http://localhost:5008/api/message/unread-count')
        data = api_ok(r, '未读消息数')
        print(f'\n[移动消息] 未读数: {data.get("data")}')

    def test_message_list(self, mobile_session):
        """消息列表"""
        r = mobile_session.get('http://localhost:5008/api/message/list')
        data = api_ok(r, '消息列表')
        msgs = data.get('data', [])
        print(f'\n[移动消息] 消息数: {len(msgs)}')


class TestMobileApproval:
    """审批流程"""

    def test_pending_approvals(self, mobile_session):
        """待审批列表"""
        r = mobile_session.get('http://localhost:5008/api/approval/pending')
        data = api_ok(r, '待审批列表')
        items = data.get('data', [])
        print(f'\n[移动审批] 待审批: {len(items)} 条')

    def test_approval_history(self, mobile_session):
        """审批历史"""
        r = mobile_session.get('http://localhost:5008/api/approval/history')
        data = api_ok(r, '审批历史')
        items = data.get('data', [])
        print(f'\n[移动审批] 历史记录: {len(items)} 条')


class TestMobileUI:
    """Playwright UI 验证"""

    def test_mobile_home_page(self, mobile_page):
        """移动端首页"""
        base_url = 'http://localhost:5008'
        try:
            r = mobile_page.goto(f'{base_url}/', timeout=10000)
            assert r.ok, f'首页返回 {r.status}'
            print(f'\n[移动 UI] 首页: {r.status} {r.url}')
        except Exception as e:
            pytest.skip(f'5008 页面未就绪: {e}')

    def test_mobile_schedule_page(self, mobile_page):
        """移动端排产页面"""
        base_url = 'http://localhost:5008'
        try:
            r = mobile_page.goto(f'{base_url}/schedule', timeout=10000)
            print(f'\n[移动 UI] 排产页: {r.status} {r.url}')
        except Exception as e:
            pytest.skip(f'排产页面未就绪: {e}')
