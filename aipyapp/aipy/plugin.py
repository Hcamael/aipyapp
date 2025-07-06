#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import threading
import traceback
import importlib.util
from pathlib import Path
from typing import Callable, Any, Dict, List

class EventBus:
    def __init__(self):
        self._listeners: Dict[str, List[Callable[..., Any]]] = {}
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def is_stopped(self):
        return self._stop_event.is_set()    

    def __repr__(self):
        return repr(self._listeners)
    
    def register(self, event_name: str, handler: Callable[..., Any]):
        self._listeners.setdefault(event_name, []).append(handler)

    def broadcast(self, event_name: str, *args, **kwargs):
        for handler in self._listeners.get(event_name, []):
            try:
                handler(*args, **kwargs)
            except Exception as e:
                traceback.print_exc()

    def pipeline(self, event_name: str, data, **kwargs):
        for handler in self._listeners.get(event_name, []):
            try:
                handler(data, **kwargs)
            except Exception as e:
                traceback.print_exc()

    def collect(self, event_name: str, *args, **kwargs):
        try:
            ret = [handler(*args, **kwargs) for handler in self._listeners.get(event_name, [])]
        except Exception as e:
            ret = []
            traceback.print_exc()
        return ret

    def __call__(self, event_name: str, *args, **kwargs):
        self.pipeline(event_name, *args, **kwargs)

event_bus = EventBus()

class PluginManager:
    def __init__(self, plugin_dir: str|Path):
        # Get the system plugin directory
        # This is the directory where the `aio_api.py` file is located
        self.sys_plugin_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'plugins')
        self.plugin_dir = plugin_dir
        self.plugins: Dict[str, Any] = {}

    def load_plugins(self):
        """Load plugins from the plugin directory."""
        for plugin_dir in [self.sys_plugin_dir, self.plugin_dir]:
            if not os.path.exists(plugin_dir):
                continue
            for fname in os.listdir(plugin_dir):
                if fname.endswith(".py") and not fname.startswith("_"):
                    self._load_plugin(os.path.join(plugin_dir, fname))


    def _load_plugin(self, filepath: str):
        plugin_id = os.path.basename(filepath)[:-3]

        spec = importlib.util.spec_from_file_location(plugin_id, filepath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        plugin_cls = getattr(module, "Plugin", None)
        if not plugin_cls or not callable(plugin_cls):
            return

        plugin = plugin_cls()

        for attr_name in dir(plugin):
            if attr_name.startswith("on_") and len(attr_name) > 3:
                handler = getattr(plugin, attr_name)
                if callable(handler):
                    event_bus.register(attr_name[3:], handler)

        self.plugins[plugin_id] = plugin
