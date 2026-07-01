# DatabaseRouter 已废弃 — 全部改用 MySQL (CONTAINER_MYSQL_CFG)
from .document_store import DocumentStore
from .index_store import IndexStore
from .config_store import ConfigStore
from .alert_store import AlertStore
from .redis_cache import RedisCache, cache as cache_instance

__all__ = [
    'DocumentStore',
    'IndexStore',
    'ConfigStore',
    'AlertStore',
    'RedisCache',
    'cache_instance',
]