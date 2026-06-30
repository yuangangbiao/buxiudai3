"""插件注册中心"""
import logging

logger = logging.getLogger(__name__)

class PluginRegistry:
    _plugins = {}

    @classmethod
    def register(cls, plugin_type, name, plugin_class):
        if plugin_type not in cls._plugins:
            cls._plugins[plugin_type] = {}
        cls._plugins[plugin_type][name] = plugin_class
        logger.info(f"插件注册: {plugin_type}/{name}")

    @classmethod
    def get(cls, plugin_type, name):
        return cls._plugins.get(plugin_type, {}).get(name)

    @classmethod
    def list(cls, plugin_type=None):
        if plugin_type:
            return dict(cls._plugins.get(plugin_type, {}))
        return {k: list(v.keys()) for k, v in cls._plugins.items()}

    @classmethod
    def create(cls, plugin_type, name, *args, **kwargs):
        plugin_class = cls.get(plugin_type, name)
        if plugin_class is None:
            raise ValueError(f"插件未注册: {plugin_type}/{name}")
        return plugin_class(*args, **kwargs)
