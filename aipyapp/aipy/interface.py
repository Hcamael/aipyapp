#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
from abc import ABC, abstractmethod
from typing import Callable, Any, Dict, List

from loguru import logger

class Runtime(ABC):
    @abstractmethod
    def install_packages(self, packages):
        pass

    @abstractmethod
    def getenv(self, name, desc=None):
        pass

class ConsoleInterface(ABC):
    @abstractmethod
    def print(self, *args, sep=' ', end='\n', file=None, flush=False):
        pass

    @abstractmethod
    def input(self, prompt=''):
        pass

    @abstractmethod
    def status(self, msg):
        pass

class Stoppable():
    def __init__(self):
        super().__init__()
        self._stop_event = threading.Event()

    def on_stop(self):
        pass

    def stop(self):
        self._stop_event.set()
        self.on_stop()
        
    def is_stopped(self):
        return self._stop_event.is_set()
    
    def wait(self, timeout=None):
        return self._stop_event.wait(timeout)
    
    def reset(self):
        self._stop_event.clear()

class Event:
    def __init__(self, name: str, data: dict):
        self.name = name
        self.data = data

    def __str__(self):
        return f"{self.name}: {self.data}"

class EventBus:
    def __init__(self):
        super().__init__()
        self._listeners: Dict[str, List[Callable[..., Any]]] = {}
        self._eb_logger = logger.bind(src=self.__class__.__name__)
    
    def register_event(self, event_name: str, handler: Callable[..., Any]):
        self._listeners.setdefault(event_name, []).append(handler)

    def register_listener(self, obj: Any):
        for event_name in dir(obj):
            if event_name.startswith('on_'):
                handler = getattr(obj, event_name)
                if callable(handler):
                    event_name = event_name[3:]
                    self.register_event(event_name, handler)
                    self._eb_logger.info(f"Registered event {event_name} for {obj.__class__.__name__}")
                else:
                    self._eb_logger.warning(f"Event {event_name} is not callable for {obj.__class__.__name__}")

    def broadcast(self, event_name: str, **kwargs):
        event = Event(event_name, kwargs)
        for handler in self._listeners.get(event_name, []):
            try:
                handler(event)
            except Exception as e:
                self._eb_logger.exception(f"Error broadcasting event {event_name}")

    def pipeline(self, event_name: str, **kwargs):
        event = Event(event_name, kwargs)
        for handler in self._listeners.get(event_name, []):
            try:
                handler(event)
            except Exception as e:
                self._eb_logger.exception(f"Error pipeline event {event_name}")

    def collect(self, event_name: str, **kwargs):
        event = Event(event_name, kwargs)
        try:
            ret = [handler(event) for handler in self._listeners.get(event_name, [])]
        except Exception as e:
            ret = []
            self._eb_logger.exception(f"Error collecting event {event_name}")
        return ret