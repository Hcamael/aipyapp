#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import importlib.util
from typing import Dict, Any

from loguru import logger

class PluginManager:
    def __init__(self, plugin_dir: str):
        # Get the system plugin directory
        # This is the directory where the `aio_api.py` file is located
        self.sys_plugin_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'plugins')
        self.plugin_dir = plugin_dir
        self.plugins: Dict[str, Any] = {}
        self.logger = logger.bind(src=self.__class__.__name__)

    def load_plugins(self):
        """Load plugins from the plugin directory."""
        for plugin_dir in [self.sys_plugin_dir, self.plugin_dir]:
            if not os.path.exists(plugin_dir):
                continue
            for fname in os.listdir(plugin_dir):
                if fname.endswith(".py") and not fname.startswith("_"):
                    self._load_plugin(os.path.join(plugin_dir, fname))


    def _load_plugin(self, filepath: str):
        name = os.path.basename(filepath)[:-3]

        spec = importlib.util.spec_from_file_location(name, filepath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        plugin_cls = getattr(module, "Plugin", None)
        if not plugin_cls or not callable(plugin_cls):
            self.logger.warning(f"Plugin {name} is not a callable class")
            return

        plugin_name = getattr(plugin_cls, "name", name)
        if plugin_name:
            name = plugin_name

        self.plugins[name] = plugin_cls
        self.logger.info(f"Loaded plugin {name}")

    def get_plugin(self, name: str, plugin_config: Dict[str, Any] = None):
        plugin_cls = self.plugins.get(name)
        if not plugin_cls:
            self.logger.warning(f"Plugin {name} not found")
            return

        return plugin_cls(plugin_config)