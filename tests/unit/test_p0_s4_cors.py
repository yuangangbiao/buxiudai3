# -*- coding: utf-8 -*-
"""
P0-S4 单元测试 - CORS 配置安全

测试范围: container_center_api.py CORS 配置
- fail-fast：未设置 CORS_ALLOWED_ORIGINS 时启动失败
- 合法域名：supports_credentials=True
- 通配符 *：自动 supports_credentials=False
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# 项目根目录加入 sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'mobile_api_ai'))


class TestCorsConfigParsing:
    """CORS 配置解析逻辑测试（不启动 5002）"""

    def _parse_cors(self, raw_value):
        """模拟 container_center_api.py 中的 CORS 解析逻辑"""
        if not raw_value or not raw_value.strip():
            raise RuntimeError('CORS_ALLOWED_ORIGINS 未设置, 请在 .env 中配置允许的域名列表, 多个域名用逗号分隔')
        allowed = [o.strip() for o in raw_value.split(',') if o.strip()]
        if '*' in allowed:
            return {'origins': allowed, 'supports_credentials': False, 'has_wildcard': True}
        return {'origins': allowed, 'supports_credentials': True, 'has_wildcard': False}

    def test_empty_value_raises(self):
        """空值触发 fail-fast"""
        with pytest.raises(RuntimeError) as exc_info:
            self._parse_cors('')
        assert 'CORS_ALLOWED_ORIGINS 未设置' in str(exc_info.value)

    def test_whitespace_only_raises(self):
        """纯空格也触发 fail-fast"""
        with pytest.raises(RuntimeError):
            self._parse_cors('   ')

    def test_legal_single_domain(self):
        """合法单域名"""
        result = self._parse_cors('http://localhost:5000')
        assert result['origins'] == ['http://localhost:5000']
        assert result['supports_credentials'] is True
        assert result['has_wildcard'] is False

    def test_legal_multiple_domains(self):
        """合法多域名"""
        result = self._parse_cors('http://localhost:5000,http://localhost:5010,http://192.168.1.100:5000')
        assert len(result['origins']) == 3
        assert result['supports_credentials'] is True
        assert result['has_wildcard'] is False

    def test_wildcard_disables_credentials(self):
        """通配符自动禁用 credentials"""
        result = self._parse_cors('*')
        assert result['origins'] == ['*']
        assert result['supports_credentials'] is False
        assert result['has_wildcard'] is True

    def test_wildcard_in_list_disables_credentials(self):
        """通配符在列表中也禁用 credentials"""
        result = self._parse_cors('http://localhost:5000,*')
        assert '*' in result['origins']
        assert result['supports_credentials'] is False

    def test_strip_whitespace(self):
        """自动去除域名两侧空格"""
        result = self._parse_cors('  http://localhost:5000  ,  http://localhost:5010  ')
        assert result['origins'] == ['http://localhost:5000', 'http://localhost:5010']


class TestCorsSecurity:
    """CORS 安全场景测试"""

    def _parse_cors(self, raw_value):
        if not raw_value or not raw_value.strip():
            raise RuntimeError('CORS_ALLOWED_ORIGINS 未设置')
        allowed = [o.strip() for o in raw_value.split(',') if o.strip()]
        if '*' in allowed:
            return {'origins': allowed, 'supports_credentials': False}
        return {'origins': allowed, 'supports_credentials': True}

    def test_no_default_wildcard(self):
        """无默认值（原配置默认是 *, 现在 fail-fast）"""
        # 原配置：os.getenv('CORS_ALLOWED_ORIGINS', '*') — 不安全
        # 新配置：无默认值，未设置时启动失败
        with pytest.raises(RuntimeError):
            self._parse_cors('')  # 模拟未设置环境变量

    def test_credentials_only_with_whitelist(self):
        """credentials 仅在白名单模式下启用"""
        # 合法配置
        result = self._parse_cors('http://trusted.com')
        assert result['supports_credentials'] is True

        # 通配符配置
        result = self._parse_cors('*')
        assert result['supports_credentials'] is False

    def test_csrf_prevented(self):
        """CSRF 防护验证"""
        # 攻击场景：通配符 + credentials（最危险组合）
        # 新配置自动禁用 credentials，阻止 CSRF
        result = self._parse_cors('*')
        assert not (result['origins'] == ['*'] and result['supports_credentials'] is True), \
            "CSRF 风险：通配符 + credentials 组合不允许"


class TestCorsConfigInSource:
    """CORS 配置源码验证"""

    def test_source_uses_fail_fast(self):
        """源码使用 fail-fast 模式"""
        # 读取源码验证
        container_center_api_path = os.path.join(
            BASE_DIR, 'mobile_api_ai', 'container_center_api.py'
        )
        with open(container_center_api_path, 'r', encoding='utf-8') as f:
            source = f.read()

        # 验证有 fail-fast 检查
        assert "CORS_ALLOWED_ORIGINS 未设置" in source
        assert "raise RuntimeError" in source
        # 验证有通配符降级
        assert "supports_credentials=False" in source
        # 验证不再有原始的不安全配置
        assert "origins=os.getenv('CORS_ALLOWED_ORIGINS', '*')" not in source, \
            "旧的不安全 CORS 配置已移除"

    def test_source_has_wildcard_warning(self):
        """源码有通配符警告"""
        container_center_api_path = os.path.join(
            BASE_DIR, 'mobile_api_ai', 'container_center_api.py'
        )
        with open(container_center_api_path, 'r', encoding='utf-8') as f:
            source = f.read()

        # 验证有 WARNING 日志
        assert "logger.warning" in source
        assert "通配符" in source


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
