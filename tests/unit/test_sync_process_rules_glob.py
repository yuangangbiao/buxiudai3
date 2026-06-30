# -*- coding: utf-8 -*-
"""
K22 BUG8 守护测试：sync_process_rules.py 不再硬编码 JSON 文件名

验证：
- 不再硬编码 '工序规则模板.json' / '工序规则模板1.json' / '工序规则模板2.json'
- 使用 glob.glob 动态读取 data/工序规则模板*.json
"""
import os
import sys
import re

import pytest

PROJECT_DIR = r"d:\yuan\不锈钢网带跟单3.0"
SCRIPT_PATH = os.path.join(PROJECT_DIR, "scripts", "sync_process_rules.py")


class TestK22BUG8SyncProcessRulesGlob:
    """验证 sync_process_rules.py 使用 glob 动态读取 JSON 文件"""

    @pytest.fixture
    def source(self):
        with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
            return f.read()

    def test_no_hardcoded_json_filenames(self, source):
        """硬编码文件名不应出现在 __init__ 的 template_files 定义中"""
        # 提取 __init__ 方法内容
        init_match = re.search(r'def __init__\(self\):.*?(?=\n    def |\nclass |\Z)', source, re.DOTALL)
        assert init_match, "找不到 __init__ 方法"
        init_body = init_match.group(0)

        # 不应出现硬编码的 3 个文件名
        assert "工序规则模板.json" not in init_body, \
            "BUG8 未修复：__init__ 中仍硬编码 '工序规则模板.json'"
        assert "工序规则模板1.json" not in init_body, \
            "BUG8 未修复：__init__ 中仍硬编码 '工序规则模板1.json'"
        assert "工序规则模板2.json" not in init_body, \
            "BUG8 未修复：__init__ 中仍硬编码 '工序规则模板2.json'"

    def test_uses_glob_glob(self, source):
        """__init__ 应使用 glob.glob 动态读取"""
        init_match = re.search(r'def __init__\(self\):.*?(?=\n    def |\nclass |\Z)', source, re.DOTALL)
        assert init_match
        init_body = init_match.group(0)

        assert "glob.glob" in init_body, \
            "BUG8 未修复：__init__ 中未使用 glob.glob"
        assert "工序规则模板*.json" in init_body, \
            "BUG8 未修复：glob pattern 应为 '工序规则模板*.json'"

    def test_no_redundant_file_list(self, source):
        """不应再有 3 个文件名的列表字面量"""
        # 查找形如 ["data/工序规则模板.json", ...] 的列表字面量
        list_literal = re.search(
            r'\[\s*["\']data/工序规则模板.*?\.json.*?\]',
            source,
            re.DOTALL
        )
        assert not list_literal, \
            f"BUG8 未修复：仍存在硬编码文件列表 {list_literal.group(0) if list_literal else ''}"

    def test_load_source_data_uses_full_path(self, source):
        """load_source_data 应直接使用完整路径（不再 join source_dir）"""
        # 实际签名是 def load_source_data(self) -> List[Dict]:
        load_match = re.search(
            r'def load_source_data\(self\) -> List\[Dict\]:.*?(?=\n    def \w+|\nclass |\Z)',
            source,
            re.DOTALL
        )
        assert load_match, "找不到 load_source_data 方法"
        load_body = load_match.group(0)

        # 不应再 os.path.join(self.source_dir, template_file)
        bad_pattern = "os.path.join(self.source_dir, template_file)"
        assert bad_pattern not in load_body, \
            f"BUG8 未修复：load_source_data 仍在拼接 {bad_pattern}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
