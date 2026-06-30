"""通用规则引擎——从JSON加载业务规则"""
import json
import os
import logging

logger = logging.getLogger(__name__)


class RuleEngine:
    """通用规则引擎，从 rules_dir 加载所有 JSON 规则文件并缓存。"""

    def __init__(self, rules_dir: str | None = None):
        self._rules_dir = rules_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'data', 'rules'
        )
        self._rules: dict[str, dict] = {}
        self._load_all()

    def _load_all(self) -> None:
        """加载 rules_dir 下所有 .json 文件到内存。"""
        if not os.path.isdir(self._rules_dir):
            logger.warning(f"规则目录不存在: {self._rules_dir}")
            return
        for fname in os.listdir(self._rules_dir):
            if fname.endswith('.json'):
                path = os.path.join(self._rules_dir, fname)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        self._rules[fname] = json.load(f)
                    logger.info(f"规则加载: {fname}")
                except Exception as e:
                    logger.error(f"规则加载失败 {fname}: {e}")

    def get_process_rules(self) -> dict:
        """返回 process_rules.json 中定义的 processes 字典。"""
        return self._rules.get('process_rules.json', {}).get('processes', {})

    def get_process(self, name: str, default=None) -> dict | None:
        """按工序名称查询单条规则，未命中返回 default。"""
        return self.get_process_rules().get(name, default)


# 模块级单例
_engine: RuleEngine | None = None


def get_rule_engine() -> RuleEngine:
    """获取 RuleEngine 单例，按需懒加载。"""
    global _engine
    if _engine is None:
        _engine = RuleEngine()
    return _engine
