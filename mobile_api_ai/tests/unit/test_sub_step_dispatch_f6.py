# -*- coding: utf-8 -*-
"""F6 阶段边界测试 (T1/T2/T3/T4/T5 验证):
- 场景1: app.py 入口（手机报工 + 扫码报工）已改走 save_process_sub_step, 不再有裸 SQL
- 场景2: _config_infra.py 已彻底删除 container_storage key
- 场景5: sync_bridge / sub_step_handler 的事件流 INSERT 保留但带 v4.0 标注
"""
import os
import re

# 项目根目录 (本文件位于 mobile_api_ai/tests/unit/)
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
APP_PY = os.path.join(ROOT, 'mobile_api_ai', 'app.py')
SYNC_BRIDGE_PY = os.path.join(ROOT, 'mobile_api_ai', 'sync_bridge.py')
SUB_STEP_HANDLER_PY = os.path.join(ROOT, 'mobile_api_ai', 'sync', 'handlers', 'sub_step_handler.py')
CONFIG_INFRA_PY = os.path.join(ROOT, 'core', '_config_infra.py')
STORAGE_LAYER_PY = os.path.join(ROOT, 'mobile_api_ai', 'storage_layer.py')


def _read(p):
    with open(p, 'r', encoding='utf-8') as f:
        return f.read()


def _extract_route_body(src: str, func_sig: str) -> str:
    """提取 Flask 路由函数体: 从 func_sig 起到下一个 @app.route 或文件结尾."""
    idx = src.find(func_sig)
    if idx < 0:
        return ''
    # 找下一个 @app.route
    tail = src[idx + len(func_sig):]
    nxt = tail.find('\n    @app.route')
    if nxt < 0:
        return tail
    return tail[:nxt]


class TestF6RouteIngress:
    """场景 1: app.py 入口路由 (T1+T2) 必须复用 save_process_sub_step."""

    def test_process_sub_step_route_uses_save_method(self):
        """route /api/process_sub_step 必须调用 save_process_sub_step."""
        src = _read(APP_PY)
        # 1. 路由函数体内出现 save_process_sub_step 调用
        assert 'save_process_sub_step' in src, 'app.py 完全未引用 save_process_sub_step'

    def test_process_sub_step_route_no_bare_insert(self):
        """route /api/process_sub_step 路由块内不应有裸 INSERT INTO process_sub_steps."""
        src = _read(APP_PY)
        # 定位到 process_sub_step 函数体 (Flask 风格: def xxx():)
        body = _extract_route_body(src, "def process_sub_step():")
        assert body, '未找到 process_sub_step 函数体'
        assert 'INSERT INTO process_sub_steps' not in body, \
            'process_sub_step 路由块内仍存在裸 INSERT, 应改走 save_process_sub_step'

    def test_scanner_report_route_no_bare_insert(self):
        """route /api/wechat/pool/report (扫码报工) 不应有裸 INSERT."""
        src = _read(APP_PY)
        body = _extract_route_body(src, "def scanner_report_api():")
        assert body, '未找到 scanner_report_api 函数体'
        assert 'INSERT INTO process_sub_steps' not in body, \
            'scanner_report_api 路由块内仍存在裸 INSERT, 应改走 save_process_sub_step'

    def test_scanner_report_uses_save_method(self):
        """扫码报工路由也必须调用 save_process_sub_step."""
        src = _read(APP_PY)
        # 至少出现 2 次: process_sub_step + scanner_report_api
        n = src.count('save_process_sub_step')
        assert n >= 2, f'期望至少 2 处 save_process_sub_step 调用, 实际 {n}'


class TestF6ContainerStorageRemoved:
    """场景 2: _config_infra.py 已彻底删除 container_storage key (F6 T4)."""

    def test_config_infra_no_container_storage_key(self):
        src = _read(CONFIG_INFRA_PY)
        assert "'container_storage'" not in src, \
            '_config_infra.py 仍残留 container_storage 字典项'
        assert '"container_storage"' not in src, \
            '_config_infra.py 仍残留 container_storage 字典项'

    def test_config_infra_no_deprecated_env_var(self):
        """CONTAINER_STORAGE_DB_PATH 不应再被代码读取（仅注释说明除外）."""
        src = _read(CONFIG_INFRA_PY)
        # 排除注释行
        non_comment_lines = [
            l for l in src.splitlines()
            if 'CONTAINER_STORAGE_DB_PATH' in l and not l.strip().startswith('#')
        ]
        assert not non_comment_lines, \
            f'_config_infra.py 仍读取 CONTAINER_STORAGE_DB_PATH: {non_comment_lines}'

    def test_storage_layer_default_uses_container_center(self):
        """storage_layer.py SQLiteStorage 默认 db_path 不再引用 container_storage."""
        src = _read(STORAGE_LAYER_PY)
        assert "DB_PATHS['container_storage']" not in src, \
            'storage_layer.py 仍引用 DB_PATHS["container_storage"]'
        assert "DB_PATHS[\"container_storage\"]" not in src, \
            'storage_layer.py 仍引用 DB_PATHS["container_storage"]'

    def test_storage_layer_docstring_no_container_storage(self):
        """storage_layer.py 文档注释中也不应再提及 container_storage.db."""
        src = _read(STORAGE_LAYER_PY)
        # 只检测 'container_storage.db' 字符串 (注释/默认值)
        assert "'container_storage.db'" not in src, \
            'storage_layer.py 注释/示例中仍提及 container_storage.db'

    def test_check_scripts_dropped_container_storage(self):
        """4 个 check 脚本都不应再列出 container_storage.db."""
        for p in [
            os.path.join(ROOT, 'mobile_api_ai', 'scripts', 'check_all_db.py'),
            os.path.join(ROOT, 'mobile_api_ai', 'scripts', 'tools', 'check_008_data.py'),
            os.path.join(ROOT, 'mobile_api_ai', 'scripts', 'tools', 'check_write.py'),
            os.path.join(ROOT, 'mobile_api_ai', 'scripts', 'tools', 'check_dbs.py'),
        ]:
            src = _read(p)
            # 排除标注清理意图的注释行
            non_comment = [
                l for l in src.splitlines()
                if 'container_storage' in l and 'F6 T4' not in l
                and not l.strip().startswith('#')
            ]
            assert not non_comment, f'{p} 仍引用 container_storage: {non_comment}'

    def test_diagnose_and_merge_scripts_use_container_center(self):
        """diagnose/merge 脚本已改用 container_center.db."""
        diagnose = _read(os.path.join(ROOT, 'scripts', 'tools', '_diagnose_substeps.py'))
        merge = _read(os.path.join(ROOT, 'scripts', 'tools', '_merge_dbs.py'))
        assert 'container_storage.db' not in diagnose, '_diagnose_substeps.py 仍指向 container_storage.db'
        assert 'container_storage.db' not in merge, '_merge_dbs.py 仍指向 container_storage.db'
        assert 'container_center.db' in diagnose, '_diagnose_substeps.py 应指向 container_center.db'
        assert 'container_center.db' in merge, '_merge_dbs.py 应指向 container_center.db'


class TestF6EventStreamAnnotation:
    """场景 5: 事件流专用路径 (T3+T5) 应保留裸 SQL + 带 v4.0 标注."""

    def test_sync_bridge_has_v4_annotation(self):
        src = _read(SYNC_BRIDGE_PY)
        # 必须有 v4.0 标注注释
        assert 'F6 v4.0 标注' in src, 'sync_bridge.py 缺少 F6 v4.0 标注'
        # 必须保留事件流 INSERT (故意绕过 v4.0)
        assert 'INSERT INTO process_sub_steps' in src, \
            'sync_bridge.py 事件流 INSERT 被错误删除'

    def test_sub_step_handler_has_v4_annotation(self):
        src = _read(SUB_STEP_HANDLER_PY)
        assert 'F6 v4.0 标注' in src, 'sub_step_handler.py 缺少 F6 v4.0 标注'
        # 保留 legacy 同步 INSERT IGNORE
        assert 'INSERT IGNORE INTO process_sub_steps' in src, \
            'sub_step_handler.py legacy INSERT IGNORE 被错误删除'
