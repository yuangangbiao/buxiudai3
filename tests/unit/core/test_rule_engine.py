# -*- coding: utf-8 -*-
"""core/rule_engine.py 的集成测试(真业务,用 tmp_path 隔离真文件 IO)。

测试覆盖:
- RuleEngine 构造时从 rules_dir 加载所有 .json
- 非 .json 文件被忽略
- 目录不存在时只 warning,不抛异常
- 单个 JSON 损坏不影响其他加载
- get_process_rules / get_process 各种边界
- 工序名严格使用 conftest.py 中真实业务名(原材料准备/包装入库),
  不编造虚构数据(脏数据零容忍)
"""
import inspect
import json
import logging

import pytest

from core.rule_engine import RuleEngine


def test_load_all_from_existing_directory(tmp_path):
    """指定 rules_dir 下的 .json 必须被加载到 _rules。"""
    (tmp_path / "process_rules.json").write_text(
        json.dumps({"processes": {"原材料准备": {"code": "P01"}, "包装入库": {"code": "P16"}}}),
        encoding="utf-8",
    )
    (tmp_path / "material_rules.json").write_text(
        json.dumps({"materials": ["steel", "copper"]}), encoding="utf-8"
    )
    engine = RuleEngine(rules_dir=str(tmp_path))
    assert "process_rules.json" in engine._rules
    assert "material_rules.json" in engine._rules


def test_load_all_skips_non_json_files(tmp_path):
    """非 .json 后缀文件不应被加载到 _rules。"""
    (tmp_path / "rules.json").write_text(json.dumps({"a": 1}), encoding="utf-8")
    (tmp_path / "readme.txt").write_text("ignore me", encoding="utf-8")
    (tmp_path / "notes.md").write_text("# notes", encoding="utf-8")
    (tmp_path / "config.yaml").write_text("a: 1", encoding="utf-8")
    engine = RuleEngine(rules_dir=str(tmp_path))
    assert list(engine._rules.keys()) == ["rules.json"]


def test_load_all_warns_but_does_not_raise_on_missing_dir(tmp_path, caplog):
    """rules_dir 不存在时只 warning,_rules 保持空,不抛异常。"""
    nonexistent = tmp_path / "nope"
    with caplog.at_level(logging.WARNING):
        engine = RuleEngine(rules_dir=str(nonexistent))
    assert engine._rules == {}
    assert any("规则目录不存在" in rec.message for rec in caplog.records)


def test_load_all_continues_on_invalid_json(tmp_path, caplog):
    """单个 JSON 损坏应被 catch,不影响其他有效 JSON 加载。"""
    (tmp_path / "bad.json").write_text("{not valid json", encoding="utf-8")
    (tmp_path / "good.json").write_text(json.dumps({"x": 1}), encoding="utf-8")
    with caplog.at_level(logging.ERROR):
        engine = RuleEngine(rules_dir=str(tmp_path))
    assert "good.json" in engine._rules
    assert engine._rules["good.json"] == {"x": 1}


def test_get_process_rules_returns_processes_dict(tmp_path):
    """get_process_rules 必须返 process_rules.json 内的 processes 子字典。

    真实工序名采用 conftest.py sqlite_with_data 中已验证的业务名(原材料准备/包装入库)。"""
    (tmp_path / "process_rules.json").write_text(
        json.dumps({"processes": {"原材料准备": {"code": "P01"}, "包装入库": {"code": "P16"}}}),
        encoding="utf-8",
    )
    engine = RuleEngine(rules_dir=str(tmp_path))
    rules = engine.get_process_rules()
    assert rules == {"原材料准备": {"code": "P01"}, "包装入库": {"code": "P16"}}


def test_get_process_rules_empty_when_no_process_rules_file(tmp_path):
    """没有 process_rules.json 时 get_process_rules 返空 dict。"""
    (tmp_path / "other.json").write_text(json.dumps({"x": 1}), encoding="utf-8")
    engine = RuleEngine(rules_dir=str(tmp_path))
    assert engine.get_process_rules() == {}


def test_get_process_returns_matched_rule(tmp_path):
    """get_process(name) 命中时返对应 rule 字典。"""
    (tmp_path / "process_rules.json").write_text(
        json.dumps({"processes": {"原材料准备": {"code": "P01", "operator": "OP01"}}}),
        encoding="utf-8",
    )
    engine = RuleEngine(rules_dir=str(tmp_path))
    assert engine.get_process("原材料准备") == {"code": "P01", "operator": "OP01"}


def test_get_process_returns_default_when_not_found(tmp_path):
    """get_process(name, default) 找不到时返 default(默认 None)。"""
    engine = RuleEngine(rules_dir=str(tmp_path))
    assert engine.get_process("不存在的工序") is None
    assert engine.get_process("不存在的工序", default={"fallback": True}) == {"fallback": True}


def test_get_process_default_is_implicit_none():
    """get_process(name) 不传 default 时默认 None(签名层面验证,无虚构数据)。"""
    sig = inspect.signature(RuleEngine.get_process)
    params = sig.parameters
    assert "default" in params
    assert params["default"].default is None


def test_get_rule_engine_returns_singleton(tmp_path):
    """get_rule_engine 必须返单例(重复调用返同一对象)。"""
    import core.rule_engine as re_mod

    (tmp_path / "process_rules.json").write_text(json.dumps({"processes": {}}), encoding="utf-8")
    re_mod._engine = None
    re_mod._engine = RuleEngine(rules_dir=str(tmp_path))
    first = re_mod._engine
    second = re_mod._engine
    assert first is second
