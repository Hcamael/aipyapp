#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from collections import Counter
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Union, List, Dict, Any

from loguru import logger

from .. import T

@dataclass
class ChatMessage:
    role: str
    content: Union[str, List[Dict[str, Any]]]
    reason: str = None
    usage: Counter = field(default_factory=Counter)

class BaseClient(ABC):
    MODEL = None
    BASE_URL = None
    TEMPERATURE = 0.5

    def __init__(self, config):
        self.name = config['name']
        self.log = logger.bind(src='llm', name=self.name)
        self.console = None
        self.config = config
        self.kind = config.get("type", "openai")
        self.max_tokens = config.get("max_tokens")
        self._model = config.get("model") or self.MODEL
        self._timeout = config.get("timeout")
        self._api_key = config.get("api_key")
        self._base_url = self.get_base_url()
        self._stream = config.get("stream", True)
        self._tls_verify = bool(config.get("tls_verify", True))
        self._client = None
        params = self.get_params()
        params.update(config.get("params", {}))
        self._params = params
        self._temperature = params.get("temperature") or self.TEMPERATURE

    @property
    def model(self):
        return self._model
    
    @property
    def base_url(self):
        return self._base_url
    
    def __repr__(self):
        return f"{self.name}/{self.kind}:{self._model}"
    
    def get_params(self):
        return {}
    
    def get_base_url(self):
        return self.config.get("base_url") or self.BASE_URL
    
    def usable(self):
        return self._model
    
    def _get_client(self):
        return self._client
    
    @abstractmethod
    def get_completion(self, messages):
        pass
        
    def add_system_prompt(self, history, system_prompt):
        history.add("system", system_prompt)

    @abstractmethod
    def _parse_usage(self, response):
        pass

    @abstractmethod
    def _parse_stream_response(self, response, stream_processor):
        pass

    @abstractmethod
    def _parse_response(self, response):
        pass
    
    def __call__(self, history, prompt, system_prompt=None, stream_processor=None):
        # We shall only send system prompt once
        if not history and system_prompt:
            self.add_system_prompt(history, system_prompt)
        history.add("user", prompt)

        start = time.time()
        try:
            response = self.get_completion(history.get_messages())
        except Exception as e:
            self.log.error(f"❌ [bold red]{self.name} API {T('Call failed')}: [yellow]{str(e)}")
            return ChatMessage(role='error', content=str(e))

        if self._stream:
            msg = self._parse_stream_response(response, stream_processor)
        else:
            msg = self._parse_response(response)

        msg.usage['time'] = round(time.time() - start, 3)
        history.add_message(msg)
        return msg
    