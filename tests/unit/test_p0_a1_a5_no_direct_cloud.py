# -*- coding: utf-8 -*-
"""
P0-A1 + P0-A5 单元测试 - 云端直连群组

测试范围:
- P0-A1: 5003 内部 _CloudPoller 调本地 5003 endpoint（不再直连 124.223.57.82:5006）
- P0-A5: cloud_poller.py 顶部 CLOUD_HOST 默认值改为本地
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# 项目根目录加入 sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'mobile_api_ai'))


class TestStandaloneDispatchServerCloudPoller:
    """P0-A1: 5003 _CloudPoller 不再直连云端 5006"""

    def _has_active_cloud_url(self, source):
        """检查是否有 http://124.223.57.82 直连 URL（排除注释和 docstring）"""
        import re
        pattern = re.compile(r'https?://124\.223\.57\.82', re.IGNORECASE)
        in_docstring = False
        for line in source.split('\n'):
            stripped = line.strip()
            # 跟踪 docstring
            if '"""' in line:
                in_docstring = not in_docstring if line.count('"""') == 1 else False
                if line.count('"""') == 2:
                    in_docstring = False
                continue
            if in_docstring:
                continue
            # 跳过注释
            if stripped.startswith('#'):
                continue
            # 检查实际代码
            if pattern.search(line):
                return True
        return False

    def test_cors_relay_url_default_is_local(self):
        """CLOUD_RELAY_URL 默认值是本地 5003"""
        # 读取源码验证
        standalone_dispatch_server_path = os.path.join(
            BASE_DIR, 'mobile_api_ai', 'standalone_dispatch_server.py'
        )
        with open(standalone_dispatch_server_path, 'r', encoding='utf-8') as f:
            source = f.read()

        # 验证默认 URL 是 localhost:5003
        assert "CLOUD_RELAY_URL = os.getenv('CLOUD_RELAY_URL', 'http://localhost:5003')" in source, \
            "CLOUD_RELAY_URL 默认值应为 http://localhost:5003"
        # 验证不再有 http://124.223.57.82 URL（注释中的不计入）
        assert not self._has_active_cloud_url(source), \
            "standalone_dispatch_server.py 仍含 http://124.223.57.82 直连 URL"

    def test_cloud_poller_class_poll_url_format(self):
        """_CloudPoller.run() 调用 /api/queue/poll"""
        standalone_dispatch_server_path = os.path.join(
            BASE_DIR, 'mobile_api_ai', 'standalone_dispatch_server.py'
        )
        with open(standalone_dispatch_server_path, 'r', encoding='utf-8') as f:
            source = f.read()

        # 验证轮询 URL 格式
        assert "f'{CLOUD_RELAY_URL}/api/queue/poll'" in source, \
            "_CloudPoller 应调用 /api/queue/poll"


class TestCloudPollerDefaultHost:
    """P0-A5: cloud_poller.py CLOUD_HOST 默认值"""

    def _has_active_cloud_url(self, source):
        """检查是否有 http://124.223.57.82 直连 URL（排除注释和 docstring）"""
        import re
        pattern = re.compile(r'https?://124\.223\.57\.82', re.IGNORECASE)
        in_docstring = False
        for line in source.split('\n'):
            stripped = line.strip()
            # 跟踪 docstring
            if '"""' in line:
                in_docstring = not in_docstring if line.count('"""') == 1 else False
                if line.count('"""') == 2:
                    in_docstring = False
                continue
            if in_docstring:
                continue
            # 跳过注释
            if stripped.startswith('#'):
                continue
            # 检查实际代码
            if pattern.search(line):
                return True
        return False

    def test_default_host_is_local(self):
        """CLOUD_HOST 默认值是 localhost:5003"""
        cloud_poller_path = os.path.join(
            BASE_DIR, 'mobile_api_ai', 'cloud_poller.py'
        )
        with open(cloud_poller_path, 'r', encoding='utf-8') as f:
            source = f.read()

        # 验证默认值是 http://localhost:5003
        assert "_DEFAULT_CLOUD_HOST = 'http://localhost:5003'" in source
        # 验证不在 URL 中硬编码 124.223.57.82（WARNING 日志中的字符串不算）
        assert not self._has_active_cloud_url(source), "cloud_poller.py 仍含 http://124.223.57.82 直连 URL"
        # 验证有 WARNING 日志
        assert "logger.warning" in source
        assert 'R-002' in source or '云端 124.223' in source

    def test_cloud_host_default_is_local_in_source(self):
        """cloud_poller.py 源码：_DEFAULT_CLOUD_HOST 默认值是 localhost:5003"""
        cloud_poller_path = os.path.join(
            BASE_DIR, 'mobile_api_ai', 'cloud_poller.py'
        )
        with open(cloud_poller_path, 'r', encoding='utf-8') as f:
            source = f.read()

        # 验证默认值是 http://localhost:5003
        assert "_DEFAULT_CLOUD_HOST = 'http://localhost:5003'" in source
        # 验证不在 URL 中出现 124.223.57.82
        assert not self._has_active_cloud_url(source)
        # 验证有 WARNING 日志提示
        assert "logger.warning" in source
        assert 'R-002' in source or '云端 124.223' in source

    def test_cloud_host_explicit_cloud_warns_in_source(self):
        """源码逻辑：显式设置 WECHAT_CLOUD_HOST=124.223.57.82 会触发 WARNING"""
        cloud_poller_path = os.path.join(
            BASE_DIR, 'mobile_api_ai', 'cloud_poller.py'
        )
        with open(cloud_poller_path, 'r', encoding='utf-8') as f:
            source = f.read()

        # 验证有判断逻辑
        assert "if _RAW_CLOUD_HOST and '124.223.57.82' in _RAW_CLOUD_HOST" in source
        assert "logger.warning('[P0-A5]" in source


class TestNoDirectCloudConnection:
    """测试全代码无 124.223.57.82 直连 URL"""

    def _has_active_cloud_url(self, source):
        """检查是否有 http://124.223.57.82 直连 URL（排除注释和 docstring）"""
        import re
        pattern = re.compile(r'https?://124\.223\.57\.82', re.IGNORECASE)
        in_docstring = False
        for line in source.split('\n'):
            stripped = line.strip()
            # 跟踪 docstring
            if '"""' in line:
                if line.count('"""') == 1:
                    in_docstring = not in_docstring
                else:
                    in_docstring = False
                continue
            if in_docstring:
                continue
            # 跳过注释
            if stripped.startswith('#'):
                continue
            # 检查实际代码
            if pattern.search(line):
                return True
        return False

    def test_no_direct_cloud_url_in_dispatch_server(self):
        """standalone_dispatch_server.py 无 http://124.223.57.82 URL"""
        path = os.path.join(BASE_DIR, 'mobile_api_ai', 'standalone_dispatch_server.py')
        with open(path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert not self._has_active_cloud_url(source), \
            "standalone_dispatch_server.py 仍含 http://124.223.57.82 直连 URL"

    def test_no_direct_cloud_url_in_cloud_poller(self):
        """cloud_poller.py 无 http://124.223.57.82 URL"""
        path = os.path.join(BASE_DIR, 'mobile_api_ai', 'cloud_poller.py')
        with open(path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert not self._has_active_cloud_url(source), \
            "cloud_poller.py 仍含 http://124.223.57.82 直连 URL"

    def test_no_direct_cloud_url_in_core_config(self):
        """core/_config_infra.py 无 http://124.223.57.82 URL"""
        path = os.path.join(BASE_DIR, 'core', '_config_infra.py')
        if not os.path.exists(path):
            pytest.skip("core/_config_infra.py 不存在")
        with open(path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert not self._has_active_cloud_url(source), \
            "core/_config_infra.py 仍含 http://124.223.57.82 直连 URL"


class TestArchitectureDocUpdate:
    """P0-A7: 架构文档修正"""

    def test_doc_has_v367_p0_a1_fix(self):
        """文档有 v3.6.7 P0-A1 修复记录"""
        doc_path = os.path.join(
            BASE_DIR, 'mobile_api_ai', 'docs', 'ARCHITECTURE_v3.6.md'
        )
        with open(doc_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert 'v3.6.7 P0-A1 修复（已完成）' in source
        assert 'v3.6.7 P0-A5 修复（已完成）' in source


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
